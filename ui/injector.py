"""
Text injector for Linux X11 desktop in YanMo IME.
Injects committed text to the active window via clipboard and XTEST key synthesis.
"""

import re
import time
from typing import Optional, Sequence
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

try:
    from Xlib import X, display, XK
    from Xlib.ext import xtest
    HAS_XLIB = True
except ImportError:
    HAS_XLIB = False

# Known password managers, privilege escalation prompters, and secure keyring agents by WM_CLASS
PWD_WM_CLASSES = (
    "polkit",
    "gcr-prompter",
    "keepass",
    "1password",
    "bitwarden",
    "pinentry",
    "kwallet",
    "gnome-keyring",
    "ksshaskpass",
    "ssh-askpass",
)

# Regex matching window title (WM_NAME) with word boundaries or specific phrases.
# Excludes substrings like "pin" in "Pinned tabs" or "lock" in "#locksmith".
PWD_NAME_REGEX = re.compile(
    r'(?:\b(?:password|passwd|passphrase|authenticate|authentication|pinentry)\b|sudo:\s*password\s+for)',
    re.IGNORECASE
)


class TextInjector:
    def __init__(self, use_clipboard: bool = True):
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.primary_clipboard = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
        self.display = display.Display() if HAS_XLIB else None
        self.use_clipboard = use_clipboard

    def is_window_terminal(self, win_id: Optional[int] = None) -> bool:
        """Check if active or specified window is a terminal emulator."""
        if not HAS_XLIB or self.display is None:
            return False
        try:
            if not win_id:
                root = self.display.screen().root
                net_active_atom = self.display.intern_atom("_NET_ACTIVE_WINDOW")
                prop = root.get_full_property(net_active_atom, X.AnyPropertyType)
                if prop and prop.value:
                    win_id = prop.value[0]
            if win_id and win_id > 0:
                win = self.display.create_resource_object("window", win_id)
                wm_class = win.get_wm_class()
                if wm_class:
                    term_indicators = ("terminal", "konsole", "xterm", "rxvt", "kitty", "alacritty", "tilix", "terminator")
                    return any(any(ind in c.lower() for ind in term_indicators) for c in wm_class if c)
        except Exception:
            pass
        return False

    @staticmethod
    def is_password_window_meta(wm_class: Optional[Sequence[str]] = None, wm_name: Optional[str] = None) -> bool:
        """
        Evaluate whether a window is a password/auth dialog based on WM_CLASS and WM_NAME.
        NOTE: This is window-level identification only (基于窗口级 WM_CLASS / WM_NAME 识别).
        Due to X11 protocol boundaries, it CANNOT detect internal password input fields inside
        applications (例如浏览器内部网页的 password 表单或终端内部交互提示，受限于 X11 协议).
        """
        if wm_class:
            for cls_item in wm_class:
                if cls_item:
                    cls_lower = cls_item.lower()
                    if any(ident in cls_lower for ident in PWD_WM_CLASSES):
                        return True

        if wm_name and PWD_NAME_REGEX.search(wm_name):
            return True

        return False

    def is_window_password(
        self,
        win_id: Optional[int] = None,
        wm_class: Optional[Sequence[str]] = None,
        wm_name: Optional[str] = None
    ) -> bool:
        """Check if active or specified window is a password or authentication dialog."""
        if wm_class is not None or wm_name is not None:
            return self.is_password_window_meta(wm_class, wm_name)

        if not HAS_XLIB or self.display is None:
            return False
        try:
            if not win_id:
                root = self.display.screen().root
                net_active_atom = self.display.intern_atom("_NET_ACTIVE_WINDOW")
                prop = root.get_full_property(net_active_atom, X.AnyPropertyType)
                if prop and prop.value:
                    win_id = prop.value[0]
            if win_id and win_id > 0:
                win = self.display.create_resource_object("window", win_id)
                wm_cls = win.get_wm_class()
                wm_nm = win.get_wm_name()
                return self.is_password_window_meta(wm_cls, wm_nm)
        except Exception:
            pass
        return False

    def _is_window_terminal(self, win_id: Optional[int] = None) -> bool:
        return self.is_window_terminal(win_id)

    def inject_text(self, text: str, target_window_id: Optional[int] = None) -> bool:
        """
        Put text on clipboard and synthesize paste key event to focused window.
        Handles key ungrab, GTK event queue processing, and focus restoration.
        Preserves original clipboard contents and restores it after injection.

        Returns:
            bool: True if injection succeeded, False if aborted (e.g. password dialog) or failed.

        NOTE:
            剪贴板注入机制存在约 150ms 的暴露时间窗口。在此期间，上屏内容暂存于系统剪贴板中。
            若系统后台运行有第三方剪贴板历史记录工具（如 CopyQ、GPaste），可能在此窗口内捕获该内容。
        """
        if not text:
            return False

        if self.is_window_password(target_window_id):
            print(f"[Injector] Security warning: Target window {target_window_id} detected as password/auth dialog. Text injection ABORTED.")
            return False

        if self.is_window_terminal(target_window_id):
            print(f"[Injector] Info: Injecting text into terminal emulator window {target_window_id}.")

        if not self.use_clipboard:
            self._inject_text_direct_xtest(text, target_window_id)
            return True

        # 1. Preserve original clipboard content before touching it
        orig_clipboard = None
        try:
            orig_clipboard = self.clipboard.wait_for_text()
        except Exception:
            pass

        # 2. Update standard clipboard (DO NOT touch primary_clipboard so mouse selection is preserved)
        try:
            self.clipboard.set_text(text, -1)
            self.clipboard.store()
        except Exception as e:
            print(f"[Injector] Clipboard error: {e}")

        # Pump GTK events so X11 SelectionOwner is registered immediately
        try:
            while Gtk.events_pending():
                Gtk.main_iteration()
        except Exception:
            pass

        # Schedule restoration of original clipboard content
        def _restore_clipboard():
            try:
                if orig_clipboard is not None:
                    self.clipboard.set_text(orig_clipboard, -1)
                    self.clipboard.store()
                else:
                    print("[Injector] Warning: Original clipboard content was non-text (image/file or empty); skipping clear() to preserve data.")
                while Gtk.events_pending():
                    Gtk.main_iteration()
            except Exception as ex:
                print(f"[Injector] Error restoring clipboard: {ex}")
            return False

        GLib.timeout_add(150, _restore_clipboard)

        if not HAS_XLIB or self.display is None:
            return True

        try:
            # 3. Explicitly ungrab any active keyboard grab in X server
            self.display.ungrab_keyboard(X.CurrentTime)

            # 4. Only release keys if they are ACTUALLY physically pressed down
            release_syms = [XK.XK_space, XK.XK_Return, XK.XK_KP_Enter]
            for d in range(1, 10):
                sym = getattr(XK, f"XK_{d}", None)
                if sym:
                    release_syms.append(sym)

            try:
                keymap = self.display.query_keymap()
                for sym in release_syms:
                    kc = self.display.keysym_to_keycode(sym)
                    if kc and (keymap[kc // 8] & (1 << (kc % 8))):
                        xtest.fake_input(self.display, X.KeyRelease, kc)
                self.display.sync()
            except Exception:
                pass

            # 5. Check and restore focus to target window if specified and not already focused
            if target_window_id and target_window_id > 0:
                try:
                    current_focused_win = None
                    try:
                        focus_obj = self.display.get_input_focus()
                        current_focused_win = getattr(focus_obj.focus, "id", None) if focus_obj else None
                    except Exception:
                        pass

                    if current_focused_win != target_window_id:
                        win = self.display.create_resource_object("window", target_window_id)
                        win.set_input_focus(X.RevertToParent, X.CurrentTime)
                        self.display.sync()
                except Exception:
                    pass

            is_term = self.is_window_terminal(target_window_id)

            ctrl_key = self.display.keysym_to_keycode(XK.XK_Control_L)
            shift_key = self.display.keysym_to_keycode(XK.XK_Shift_L)
            v_key = self.display.keysym_to_keycode(XK.XK_v)

            time.sleep(0.02)

            # 6. Key press (Ctrl+V or Ctrl+Shift+V)
            xtest.fake_input(self.display, X.KeyPress, ctrl_key)
            if is_term:
                xtest.fake_input(self.display, X.KeyPress, shift_key)
            xtest.fake_input(self.display, X.KeyPress, v_key)
            self.display.sync()

            time.sleep(0.02)

            # 7. Key release
            xtest.fake_input(self.display, X.KeyRelease, v_key)
            if is_term:
                xtest.fake_input(self.display, X.KeyRelease, shift_key)
            xtest.fake_input(self.display, X.KeyRelease, ctrl_key)
            self.display.sync()

            # 8. Pump GTK events again so SelectionRequest from the pasting app is answered promptly
            time.sleep(0.01)
            while Gtk.events_pending():
                Gtk.main_iteration()

            return True

        except Exception as e:
            print(f"[Injector] Warning during text injection: {e}")
            return False

    def _inject_text_direct_xtest(self, text: str, target_window_id: Optional[int] = None):
        """
        Direct XTEST character injection fallback without clipboard.
        NOTE: 实验性特性 (Experimental feature)。动态借用并重映射 X11 键映射 (keycode 250)，
        单字处理延迟约 5ms (字符吞吐率 ~5ms/字)。在 finally 中确保恢复原始键映射。
        """
        if not HAS_XLIB or self.display is None:
            return
        orig_mapping = None
        kc = 250
        try:
            self.display.ungrab_keyboard(X.CurrentTime)
            try:
                orig_mapping = self.display.get_keyboard_mapping(kc, 1)
            except Exception:
                orig_mapping = None

            for ch in text:
                cp = ord(ch)
                sym = cp if cp < 128 else (0x01000000 | cp)
                self.display.change_keyboard_mapping(kc, [[sym, 0, 0, 0]])
                self.display.sync()
                xtest.fake_input(self.display, X.KeyPress, kc)
                xtest.fake_input(self.display, X.KeyRelease, kc)
                self.display.sync()
                time.sleep(0.005)
        except Exception as e:
            print(f"[Injector] Error in direct XTEST injection: {e}")
        finally:
            if orig_mapping is not None and self.display is not None:
                try:
                    self.display.change_keyboard_mapping(kc, orig_mapping)
                    self.display.sync()
                except Exception as ex:
                    print(f"[Injector] Warning restoring keycode {kc} mapping: {ex}")

    def inject_key(self, key_name: str, is_shift: bool = False, keycode: Optional[int] = None, target_window_id: Optional[int] = None):
        """
        Synthesize key press and release event via XTEST for unconsumed keys.
        """
        if not HAS_XLIB or self.display is None:
            return

        try:
            # 1. Determine keycode
            kc = keycode
            if not kc:
                key_map = {
                    "Escape": "Escape",
                    "Backspace": "BackSpace",
                    "Enter": "Return",
                    "Tab": "Tab",
                    " ": "space",
                    "ArrowDown": "Down",
                    "ArrowUp": "Up",
                    "PageDown": "Page_Down",
                    "PageUp": "Page_Up",
                    "-": "minus",
                    "=": "equal",
                    "[": "bracketleft",
                    "]": "bracketright",
                    "{": "braceleft",
                    "}": "braceright",
                    ",": "comma",
                    ".": "period",
                    "<": "less",
                    ">": "greater",
                    ";": "semicolon",
                    ":": "colon",
                    "/": "slash",
                    "?": "question",
                    "\\": "backslash",
                    "|": "bar",
                    "'": "apostrophe",
                    '"': "quotedbl",
                    "`": "grave",
                    "~": "asciitilde",
                }
                sym_name = key_map.get(key_name, key_name)
                sym = XK.string_to_keysym(sym_name)
                if not sym and len(key_name) == 1:
                    sym = ord(key_name)
                if sym:
                    kc = self.display.keysym_to_keycode(sym)

            if not kc or kc <= 0:
                return

            # 2. Check and restore focus to target window if specified
            if target_window_id and target_window_id > 0:
                try:
                    win = self.display.create_resource_object("window", target_window_id)
                    win.set_input_focus(X.RevertToParent, X.CurrentTime)
                    self.display.sync()
                except Exception:
                    pass

            # 3. Handle shift key modifier if needed
            shift_kc = self.display.keysym_to_keycode(XK.XK_Shift_L) if is_shift else None

            if shift_kc:
                xtest.fake_input(self.display, X.KeyPress, shift_kc)

            xtest.fake_input(self.display, X.KeyPress, kc)
            xtest.fake_input(self.display, X.KeyRelease, kc)

            if shift_kc:
                xtest.fake_input(self.display, X.KeyRelease, shift_kc)

            self.display.sync()

        except Exception as e:
            print(f"[Injector] Warning during key injection: {e}")

