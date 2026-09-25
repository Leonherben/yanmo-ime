"""
Active window and screen geometry tracker for YanMo IME.
Determines optimal placement for the floating candidate bar across X11 applications.
"""

from typing import Optional, Tuple, Dict, Any

try:
    from Xlib import X, display
    HAS_XLIB = True
except ImportError:
    HAS_XLIB = False


class WindowTracker:
    def __init__(self):
        self.display = display.Display() if HAS_XLIB else None
        if self.display:
            self.screen = self.display.screen()
            self.root = self.screen.root
            self.screen_width = self.screen.width_in_pixels
            self.screen_height = self.screen.height_in_pixels
        else:
            self.screen_width = 1920
            self.screen_height = 1080

    def get_active_window_id(self) -> Optional[int]:
        """Fetch the active window ID from X11 root property."""
        if not HAS_XLIB or not self.display:
            return None
        try:
            net_active_atom = self.display.intern_atom("_NET_ACTIVE_WINDOW")
            prop = self.root.get_full_property(net_active_atom, X.AnyPropertyType)
            if prop and prop.value:
                return prop.value[0]
        except Exception:
            pass
        return None

    def get_active_window_info(self) -> Dict[str, Any]:
        """Return geometry and metadata for currently active window."""
        info = {
            "window_id": None,
            "wm_class": None,
            "x": 100,
            "y": 100,
            "width": 800,
            "height": 600,
            "pointer_x": 400,
            "pointer_y": 300,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
        }

        if not HAS_XLIB or not self.display:
            return info

        try:
            ptr = self.root.query_pointer()
            info["pointer_x"] = ptr.root_x
            info["pointer_y"] = ptr.root_y

            win_id = self.get_active_window_id()
            if win_id and win_id > 0:
                info["window_id"] = win_id
                win = self.display.create_resource_object("window", win_id)
                info["wm_class"] = win.get_wm_class()
                geom = win.get_geometry()
                coords = win.translate_coords(self.root, 0, 0)
                info["x"] = abs(coords.x)
                info["y"] = abs(coords.y)
                info["width"] = geom.width
                info["height"] = geom.height
        except Exception:
            pass

        return info

    def calculate_candidate_position(self, cand_w: int = 340, cand_h: int = 70) -> Tuple[int, int]:
        """
        Calculate ideal floating coordinates near the active typing area.
        Ensures the candidate bar stays strictly on-screen.
        """
        info = self.get_active_window_info()
        px, py = info["pointer_x"], info["pointer_y"]
        wx, wy = info["x"], info["y"]
        ww, wh = info["width"], info["height"]

        # If pointer is within or near the active window, place below cursor
        if wx - 50 <= px <= wx + ww + 50 and wy - 50 <= py <= wy + wh + 50:
            target_x = px + 12
            target_y = py + 24
        else:
            # Fallback: place in lower quarter of active window
            target_x = wx + 40
            target_y = wy + wh - cand_h - 40

        # Boundary checks against screen edges
        margin = 16
        if target_x + cand_w > self.screen_width - margin:
            target_x = max(margin, self.screen_width - cand_w - margin)
        if target_x < margin:
            target_x = margin

        if target_y + cand_h > self.screen_height - margin:
            # Flip above cursor/window if overflowing bottom
            target_y = max(margin, py - cand_h - 24 if py > cand_h + 30 else wy + 40)
        if target_y < margin:
            target_y = margin

        return int(target_x), int(target_y)
