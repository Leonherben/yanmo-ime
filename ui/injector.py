"""
Text injector for Linux X11 desktop in YanMo IME.
Injects committed text to the active window via clipboard and XTEST key synthesis.
"""

import time
from typing import Optional
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
        self.primary_clipboard = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
        self.display = display.Display() if HAS_XLIB else None

    def _is_window_terminal(self, win_id: Optional[int] = None) -> bool:
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

    def inject_text(self, text: str, target_window_id: Optional[int] = None):
        """
        Put text on clipboard and synthesize paste key event to focused window.
        Handles key ungrab, GTK event queue processing, and focus restoration.
        """
        if not text:
            return

        # 1. Update both standard clipboard and primary selection
        try:
            self.clipboard.set_text(text, -1)
            self.clipboard.store()
            if self.primary_clipboard:
                self.primary_clipboard.set_text(text, -1)
        except Exception as e:
            print(f"[Injector] Clipboard error: {e}")

        # Pump GTK events so X11 SelectionOwner is registered immediately
        try:
            while Gtk.events_pending():
                Gtk.main_iteration()
        except Exception:
            pass

        if not HAS_XLIB or self.display is None:
            return

        try:
            # 2. Explicitly ungrab any active keyboard grab in X server
            self.display.ungrab_keyboard(X.CurrentTime)

            # 3. Release any keys that might still be held physically (Space, Enter, digits 1-9)
            release_syms = [XK.XK_space, XK.XK_Return, XK.XK_KP_Enter]
            for d in range(1, 10):
                sym = getattr(XK, f"XK_{d}", None)
                if sym:
                    release_syms.append(sym)

            for sym in release_syms:
                kc = self.display.keysym_to_keycode(sym)
                if kc:
                    xtest.fake_input(self.display, X.KeyRelease, kc)
            self.display.sync()

            # 4. Check and restore focus to target window if specified
            if target_window_id and target_window_id > 0:
                try:
                    win = self.display.create_resource_object("window", target_window_id)
                    win.set_input_focus(X.RevertToParent, X.CurrentTime)
                    self.display.sync()
                except Exception:
                    pass

            is_term = self._is_window_terminal(target_window_id)

            ctrl_key = self.display.keysym_to_keycode(XK.XK_Control_L)
            shift_key = self.display.keysym_to_keycode(XK.XK_Shift_L)
            v_key = self.display.keysym_to_keycode(XK.XK_v)

            time.sleep(0.02)

            # 5. Key press (Ctrl+V or Ctrl+Shift+V)
            xtest.fake_input(self.display, X.KeyPress, ctrl_key)
            if is_term:
                xtest.fake_input(self.display, X.KeyPress, shift_key)
            xtest.fake_input(self.display, X.KeyPress, v_key)
            self.display.sync()

            time.sleep(0.02)

            # 6. Key release
            xtest.fake_input(self.display, X.KeyRelease, v_key)
            if is_term:
                xtest.fake_input(self.display, X.KeyRelease, shift_key)
            xtest.fake_input(self.display, X.KeyRelease, ctrl_key)
            self.display.sync()

            # 7. Pump GTK events again so SelectionRequest from the pasting app is answered promptly
            time.sleep(0.01)
            while Gtk.events_pending():
                Gtk.main_iteration()

        except Exception as e:
            print(f"[Injector] Warning during text injection: {e}")
