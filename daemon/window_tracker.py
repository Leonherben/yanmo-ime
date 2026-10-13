"""
Active window and screen geometry tracker for YanMo IME.
Determines optimal placement for the floating candidate bar across X11 applications,
fully accounting for Linux Mint HiDPI scaling (Surface Pro display) and AT-SPI caret detection.
"""

import json
import threading
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

try:
    import pyatspi
    HAS_ATSPI = True
except ImportError:
    HAS_ATSPI = False

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkX11", "3.0")
from gi.repository import Gtk, Gdk, GdkX11

try:
    from Xlib import X, display
    HAS_XLIB = True
except ImportError:
    HAS_XLIB = False


class WindowTracker:
    def __init__(self):
        self.gdk_display = Gdk.Display.get_default()
        self.x_display = display.Display() if HAS_XLIB else None
        self.x_root = self.x_display.screen().root if self.x_display else None
        self.window_offsets: Dict[int, Tuple[int, int]] = {}
        self.custom_offset: Optional[Tuple[int, int]] = None
        self.caret_offset: Optional[Tuple[int, int]] = None
        self._cached_caret_elem = None
        self._cached_caret_pos: Optional[Tuple[int, int]] = None
        self._caret_thread_running = True
        self._caret_request_event = threading.Event()
        self._caret_worker_thread = threading.Thread(target=self._caret_worker, daemon=True)
        self._caret_worker_thread.start()
        self._load_offsets()

    def _get_offsets_file(self) -> Path:
        return Path.home() / ".config" / "yanmo" / "window_offsets.json"

    def _load_offsets(self):
        """Load persisted user candidate window offsets."""
        try:
            p = self._get_offsets_file()
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "custom_offset" in data and data["custom_offset"]:
                        self.custom_offset = tuple(data["custom_offset"])
                    if "caret_offset" in data and data["caret_offset"]:
                        self.caret_offset = tuple(data["caret_offset"])
                    if "window_offsets" in data:
                        self.window_offsets = {
                            int(k): tuple(v) for k, v in data["window_offsets"].items()
                        }
        except Exception:
            pass

    def _save_offsets(self):
        """Persist user dragged candidate window offsets."""
        try:
            p = self._get_offsets_file()
            p.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "custom_offset": list(self.custom_offset) if self.custom_offset else None,
                "caret_offset": list(self.caret_offset) if self.caret_offset else None,
                "window_offsets": {str(k): list(v) for k, v in self.window_offsets.items()},
            }
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def set_user_offset(self, x: int, y: int, window_id: Optional[int] = None):
        """Save user dragged position as an offset relative to caret, window or screen."""
        caret = self.get_caret_position()
        if caret:
            self.caret_offset = (x - (caret[0] + 4), y - (caret[1] + 6))
        if window_id:
            info = self.get_active_window_info()
            wx, wy = info["x"], info["y"]
            self.window_offsets[window_id] = (x - wx, y - wy)
        self.custom_offset = (x, y)
        self._save_offsets()

    def close(self):
        """Close X11 display socket and release resources."""
        self._caret_thread_running = False
        if hasattr(self, "_caret_request_event"):
            self._caret_request_event.set()
        if self.x_display:
            try:
                self.x_display.close()
            except Exception:
                pass
            self.x_display = None
            self.x_root = None

    def __del__(self):
        self.close()

    def get_active_window_id(self) -> Optional[int]:
        """Fetch active top-level window XID from _NET_ACTIVE_WINDOW."""
        if not self.x_display or not self.x_root:
            return None
        try:
            net_active = self.x_display.intern_atom("_NET_ACTIVE_WINDOW")
            prop = self.x_root.get_full_property(net_active, X.AnyPropertyType)
            if prop and prop.value:
                return prop.value[0]
        except Exception:
            pass
        return None

    def get_active_window_pid(self) -> Optional[int]:
        """Fetch process ID (_NET_WM_PID) of the active window."""
        xid = self.get_active_window_id()
        if not xid or not self.x_display:
            return None
        try:
            win = self.x_display.create_resource_object("window", xid)
            pid_atom = self.x_display.intern_atom("_NET_WM_PID")
            prop = win.get_full_property(pid_atom, X.AnyPropertyType)
            if prop and prop.value:
                return prop.value[0]
        except Exception:
            pass
        return None

    def _caret_worker(self):
        """Background worker thread that runs AT-SPI queries without blocking main thread."""
        while self._caret_thread_running:
            self._caret_request_event.wait(timeout=0.25)
            self._caret_request_event.clear()
            if not self._caret_thread_running:
                break
            try:
                pos = self.query_caret_position_sync()
                self._cached_caret_pos = pos
            except Exception:
                pass

    def get_caret_position(self) -> Optional[Tuple[int, int]]:
        """
        Return latest caret position in logical pixels without blocking the main thread.
        Asynchronously triggers a fresh lookup in background worker thread.
        """
        self.trigger_caret_update()
        return self._cached_caret_pos

    def trigger_caret_update(self):
        """Signal background worker to perform fresh AT-SPI caret lookup."""
        if self._caret_thread_running:
            self._caret_request_event.set()

    def query_caret_position_sync(self) -> Optional[Tuple[int, int]]:
        """Synchronously query exact text caret position via AT-SPI in logical pixels."""
        if not HAS_ATSPI or not self.gdk_display:
            return None

        info = self.get_active_window_info()
        wx, wy = info["x"], info["y"]
        ww, wh = info["width"], info["height"]

        # 1. Fast path: check cached accessible element (<0.5ms)
        if self._cached_caret_elem is not None:
            try:
                st = self._cached_caret_elem.getState()
                if st.contains(pyatspi.STATE_FOCUSED):
                    t = self._cached_caret_elem.queryText()
                    offset = t.caretOffset
                    char_count = t.characterCount
                    if offset >= 0:
                        q_offset = offset if offset < char_count else (char_count - 1 if char_count > 0 else 0)
                        ext = t.getCharacterExtents(q_offset, pyatspi.XY_SCREEN)
                        if (ext[0] <= 0 or ext[1] <= 0) and offset > 0:
                            ext = t.getCharacterExtents(offset - 1, pyatspi.XY_SCREEN)
                            if ext[0] > 0 and ext[1] > 0:
                                ext = (ext[0] + ext[2], ext[1], ext[2], ext[3])
                        if ext[0] > 0 and ext[1] > 0:
                            cx = ext[0] + (ext[2] if offset >= char_count and char_count > 0 else 0)
                            cy = ext[1] + ext[3]
                            if (wx - 30 <= cx <= wx + ww + 30) and (wy - 30 <= cy <= wy + wh + 30):
                                return int(cx), int(cy)
            except Exception:
                self._cached_caret_elem = None

        # 2. General tree lookup
        try:
            desktop = pyatspi.Registry.getDesktop(0)
            if desktop is None:
                return None

            active_pid = self.get_active_window_pid()

            # Priority search in matching active application by PID
            if active_pid:
                for i in range(desktop.childCount):
                    try:
                        app = desktop.getChildAtIndex(i)
                        if app is not None and getattr(app, "get_process_id", lambda: None)() == active_pid:
                            caret = self._find_caret_in_element(app)
                            if caret and (wx - 30 <= caret[0] <= wx + ww + 30) and (wy - 30 <= caret[1] <= wy + wh + 30):
                                return caret
                    except Exception:
                        continue

            # Fallback search: any focused widget with caret inside active window rect
            for i in range(desktop.childCount):
                try:
                    app = desktop.getChildAtIndex(i)
                    if app is None:
                        continue
                    caret = self._find_caret_in_element(app)
                    if caret and (wx - 30 <= caret[0] <= wx + ww + 30) and (wy - 30 <= caret[1] <= wy + wh + 30):
                        return caret
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def _find_caret_in_element(self, obj, depth: int = 0, max_depth: int = 16) -> Optional[Tuple[int, int]]:
        if obj is None or depth > max_depth:
            return None
        try:
            st = obj.getState()
            if st.contains(pyatspi.STATE_FOCUSED):
                try:
                    text = obj.queryText()
                    offset = text.caretOffset
                    char_count = text.characterCount
                    if offset >= 0:
                        query_offset = offset
                        if query_offset >= char_count and char_count > 0:
                            query_offset = char_count - 1
                        ext = text.getCharacterExtents(query_offset, pyatspi.XY_SCREEN)
                        if (ext[0] <= 0 or ext[1] <= 0) and offset > 0:
                            ext = text.getCharacterExtents(offset - 1, pyatspi.XY_SCREEN)
                            if ext[0] > 0 and ext[1] > 0:
                                ext = (ext[0] + ext[2], ext[1], ext[2], ext[3])
                        if ext[0] > 0 and ext[1] > 0:
                            cx = ext[0] + (ext[2] if offset >= char_count and char_count > 0 else 0)
                            cy = ext[1] + ext[3]
                            self._cached_caret_elem = obj
                            return int(cx), int(cy)
                except Exception:
                    pass
            for i in range(obj.childCount):
                try:
                    child = obj.getChildAtIndex(i)
                    if child is not None:
                        res = self._find_caret_in_element(child, depth + 1, max_depth)
                        if res:
                            return res
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def get_active_window_info(self) -> Dict[str, Any]:
        """Fetch active window geometry and pointer in GDK logical coordinates."""
        info = {
            "window_id": None,
            "x": 100,
            "y": 100,
            "width": 800,
            "height": 600,
            "pointer_x": 400,
            "pointer_y": 300,
            "screen_width": 1920,
            "screen_height": 1080,
        }

        if self.gdk_display:
            monitor = self.gdk_display.get_primary_monitor() or self.gdk_display.get_monitor(0)
            if monitor:
                geom = monitor.get_geometry()
                info["screen_width"] = geom.width
                info["screen_height"] = geom.height

        # 1. Pointer position in GDK logical coordinates
        if self.gdk_display:
            seat = self.gdk_display.get_default_seat()
            if seat:
                pointer = seat.get_pointer()
                if pointer:
                    screen, px, py = pointer.get_position()
                    info["pointer_x"] = px
                    info["pointer_y"] = py

        # 2. Active Window coordinates in GDK logical coordinates
        xid = self.get_active_window_id()
        if xid and self.gdk_display:
            info["window_id"] = xid
            try:
                gdk_win = GdkX11.X11Window.foreign_new_for_display(self.gdk_display, xid)
                if gdk_win:
                    ox, oy = gdk_win.get_root_origin()
                    info["x"] = ox
                    info["y"] = oy
                    info["width"] = gdk_win.get_width()
                    info["height"] = gdk_win.get_height()
            except Exception:
                pass

        return info

    def calculate_candidate_position(self, cand_w: int = 380, cand_h: int = 50) -> Tuple[int, int]:
        """
        Calculate ideal floating coordinates near active typing caret or cursor in logical pixels.
        Ensures the candidate bar stays strictly on-screen across Surface HiDPI and multi-monitor setups.
        """
        # 1. Try AT-SPI caret position first
        caret = self.get_caret_position()

        info = self.get_active_window_info()
        px, py = info["pointer_x"], info["pointer_y"]
        wx, wy = info["x"], info["y"]
        ww, wh = info["width"], info["height"]

        xid = info.get("window_id")

        if caret:
            target_x = caret[0] + 4
            target_y = caret[1] + 6
            if self.caret_offset:
                target_x += self.caret_offset[0]
                target_y += self.caret_offset[1]
        elif xid and xid in self.window_offsets:
            off_x, off_y = self.window_offsets[xid]
            target_x = wx + off_x
            target_y = wy + off_y
        elif self.custom_offset:
            target_x, target_y = self.custom_offset
        elif (wx - 20 <= px <= wx + ww + 20) and (wy - 20 <= py <= wy + wh + 20):
            # Pointer is within or near the active window (where the user clicked to type!)
            target_x = px + 4
            target_y = py + 24
        else:
            # Predictable fallback inside the lower typing area of focused window
            target_x = wx + 36
            target_y = wy + max(40, wh - cand_h - 40)

        # 2. Monitor boundary clamping in logical pixels
        monitor = None
        if self.gdk_display:
            monitor = self.gdk_display.get_monitor_at_point(target_x, target_y)
            if not monitor:
                monitor = self.gdk_display.get_primary_monitor() or self.gdk_display.get_monitor(0)

        if monitor:
            geom = monitor.get_geometry()
            margin = 12

            # Clamp horizontal
            if target_x + cand_w > geom.x + geom.width - margin:
                target_x = max(geom.x + margin, geom.x + geom.width - cand_w - margin)
            if target_x < geom.x + margin:
                target_x = geom.x + margin

            # Clamp vertical (flip above if overflowing bottom)
            if target_y + cand_h > geom.y + geom.height - margin:
                target_y = max(geom.y + margin, target_y - cand_h - 32)
            if target_y < geom.y + margin:
                target_y = geom.y + margin
        else:
            target_x = max(12, min(target_x, 1400))
            target_y = max(12, min(target_y, 900))

        return int(target_x), int(target_y)
