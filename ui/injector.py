"""
Text injector for Linux X11 desktop in YanMo IME.
Injects committed text to the active window via clipboard and XTEST key synthesis.
"""

import time
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

try:
    from Xlib import X, display, XK
    from Xlib.ext import xtest
    HAS_XLIB = True
except ImportError:
    HAS_XLIB = False


class TextInjector:
    def __init__(self):
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.display = display.Display() if HAS_XLIB else None

    def _is_active_window_terminal(self) -> bool:
        """Check if currently focused window is a terminal emulator."""
        if not HAS_XLIB or self.display is None:
            return False
        try:
            root = self.display.screen().root
            net_active_atom = self.display.intern_atom("_NET_ACTIVE_WINDOW")
            prop = root.get_full_property(net_active_atom, X.AnyPropertyType)
            if prop and prop.value:
                win_id = prop.value[0]
                win = self.display.create_resource_object("window", win_id)
                wm_class = win.get_wm_class()
                if wm_class:
                    term_indicators = ("terminal", "konsole", "xterm", "rxvt", "kitty", "alacritty", "tilix", "terminator")
                    return any(any(ind in c.lower() for ind in term_indicators) for c in wm_class if c)
        except Exception:
            pass
        return False

    def inject_text(self, text: str):
        """Put text on clipboard and synthesize paste key event to focused window."""
        if not text:
            return

        # 1. Update clipboard
        self.clipboard.set_text(text, -1)
        self.clipboard.store()

        if not HAS_XLIB or self.display is None:
            return

        # 2. Check window type
        is_term = self._is_active_window_terminal()

        # 3. Synthesize Ctrl+V (or Ctrl+Shift+V for terminals) on active X11 window
        try:
            ctrl_key = self.display.keysym_to_keycode(XK.XK_Control_L)
            shift_key = self.display.keysym_to_keycode(XK.XK_Shift_L)
            v_key = self.display.keysym_to_keycode(XK.XK_v)

            time.sleep(0.01)

            # Key press
            xtest.fake_input(self.display, X.KeyPress, ctrl_key)
            if is_term:
                xtest.fake_input(self.display, X.KeyPress, shift_key)
            xtest.fake_input(self.display, X.KeyPress, v_key)
            self.display.sync()

            time.sleep(0.02)

            # Key release
            xtest.fake_input(self.display, X.KeyRelease, v_key)
            if is_term:
                xtest.fake_input(self.display, X.KeyRelease, shift_key)
            xtest.fake_input(self.display, X.KeyRelease, ctrl_key)
            self.display.sync()
        except Exception as e:
            print(f"[Injector] Warning during text injection: {e}")
