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

    def inject_text(self, text: str):
        """Put text on clipboard and synthesize Ctrl+V key event to focused window."""
        if not text:
            return

        # 1. Update clipboard
        self.clipboard.set_text(text, -1)
        self.clipboard.store()

        if not HAS_XLIB or self.display is None:
            return

        # 2. Synthesize Ctrl+V on the active X11 window
        try:
            ctrl_key = self.display.keysym_to_keycode(XK.XK_Control_L)
            v_key = self.display.keysym_to_keycode(XK.XK_v)

            # Key press: Ctrl + V
            xtest.fake_input(self.display, X.KeyPress, ctrl_key)
            xtest.fake_input(self.display, X.KeyPress, v_key)
            self.display.sync()

            time.sleep(0.02)

            # Key release: V + Ctrl
            xtest.fake_input(self.display, X.KeyRelease, v_key)
            xtest.fake_input(self.display, X.KeyRelease, ctrl_key)
            self.display.sync()
        except Exception as e:
            print(f"[Injector] Warning during text injection: {e}")
