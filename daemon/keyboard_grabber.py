"""
X11 Global Keyboard Interceptor for YanMo IME Daemon.
Listens to global hotkeys (Ctrl+Space, v+Space) and intercepts typing keys
when Chinese input mode is active.
"""

import os
import threading
import time
from typing import Callable, Optional, Set

try:
    from Xlib import X, display, XK
    HAS_XLIB = True
except ImportError:
    HAS_XLIB = False

import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib


class KeyboardGrabber:
    def __init__(
        self,
        on_key_event: Optional[Callable[[str, bool], None]] = None,
        on_mode_toggle: Optional[Callable[[], None]] = None,
        on_punct_toggle: Optional[Callable[[], None]] = None,
        on_fullwidth_toggle: Optional[Callable[[], None]] = None,
        on_voice_toggle: Optional[Callable[[bool], None]] = None,
        on_panic_exit: Optional[Callable[[], None]] = None,
    ):
        self.on_key_event = on_key_event
        self.on_mode_toggle = on_mode_toggle
        self.on_punct_toggle = on_punct_toggle
        self.on_fullwidth_toggle = on_fullwidth_toggle
        self.on_voice_toggle = on_voice_toggle
        self.on_panic_exit = on_panic_exit

        self.display = display.Display() if HAS_XLIB else None
        if self.display:
            try:
                self.display.set_error_handler(lambda *args: None)
            except Exception:
                pass
        self.root = self.display.screen().root if self.display else None

        self.running = False
        self.thread: Optional[threading.Thread] = None

        self.is_chinese_mode = False
        self.is_chinese_punct = True
        self.is_full_width = False
        self.is_composing = False

        # Key state tracking for v + Space push-to-talk
        self.v_pressed = False
        self.space_pressed = False
        self.voice_recording = False
        self.voice_timer_id = None

        # Cache keycodes
        self._init_keycodes()

    def _init_keycodes(self):
        if not self.display:
            return

        self.kc_space = self.display.keysym_to_keycode(XK.XK_space)
        self.kc_return = self.display.keysym_to_keycode(XK.XK_Return)
        self.kc_v = self.display.keysym_to_keycode(XK.XK_v)
        self.kc_tab = self.display.keysym_to_keycode(XK.XK_Tab)
        self.kc_backspace = self.display.keysym_to_keycode(XK.XK_BackSpace)
        self.kc_escape = self.display.keysym_to_keycode(XK.XK_Escape)
        self.kc_grave = self.display.keysym_to_keycode(XK.XK_grave)
        self.kc_down = self.display.keysym_to_keycode(XK.XK_Down)
        self.kc_up = self.display.keysym_to_keycode(XK.XK_Up)
        self.kc_minus = self.display.keysym_to_keycode(XK.XK_minus)
        self.kc_equal = self.display.keysym_to_keycode(XK.XK_equal)
        self.kc_bracketleft = self.display.keysym_to_keycode(XK.XK_bracketleft)
        self.kc_bracketright = self.display.keysym_to_keycode(XK.XK_bracketright)
        self.kc_comma = self.display.keysym_to_keycode(XK.XK_comma)
        self.kc_period = self.display.keysym_to_keycode(XK.XK_period)
        self.kc_semicolon = self.display.keysym_to_keycode(XK.XK_semicolon)
        self.kc_slash = self.display.keysym_to_keycode(XK.XK_slash)
        self.kc_backslash = self.display.keysym_to_keycode(XK.XK_backslash)
        self.kc_apostrophe = self.display.keysym_to_keycode(XK.XK_apostrophe)

        # Alpha keys a-z
        self.alpha_keycodes = {}
        for c in range(ord('a'), ord('z') + 1):
            char = chr(c)
            sym = getattr(XK, f"XK_{char}", None)
            if sym:
                kc = self.display.keysym_to_keycode(sym)
                self.alpha_keycodes[kc] = char

        # Digit keys 1-9
        self.digit_keycodes = {}
        for d in range(1, 10):
            sym = getattr(XK, f"XK_{d}", None)
            if sym:
                kc = self.display.keysym_to_keycode(sym)
                self.digit_keycodes[kc] = str(d)

    def _grab(self, keycode: int, modifiers: int = 0):
        if not self.root:
            return
        # Mask variations (clean, +NumLock, +CapsLock, +NumLock+CapsLock)
        mod_masks = [0, X.Mod2Mask, X.LockMask, X.Mod2Mask | X.LockMask]
        for mask in mod_masks:
            try:
                self.root.grab_key(
                    keycode,
                    modifiers | mask,
                    True,
                    X.GrabModeAsync,
                    X.GrabModeAsync
                )
            except Exception:
                pass

    def _ungrab(self, keycode: int, modifiers: int = 0):
        if not self.root:
            return
        mod_masks = [0, X.Mod2Mask, X.LockMask, X.Mod2Mask | X.LockMask]
        for mask in mod_masks:
            try:
                self.root.ungrab_key(keycode, modifiers | mask)
            except Exception:
                pass

    def update_grabs(self):
        """Update key grabs based on current mode (Chinese vs English, Composing vs Idle)."""
        if not self.display or not self.root:
            return

        # 1. Global Activation Hotkeys (Always grabbed):
        # Ctrl+Space (IME toggle), Ctrl+. (Chinese/English Punctuation), Shift+Space (Full/Half width)
        # Ctrl+Alt+Escape (P1-3 Emergency Panic Exit)
        self._grab(self.kc_space, X.ControlMask)
        self._grab(self.kc_period, X.ControlMask)
        self._grab(self.kc_space, X.ShiftMask)
        self._grab(self.kc_escape, X.ControlMask | X.Mod1Mask)

        punct_keys = [
            self.kc_comma, self.kc_period, self.kc_semicolon,
            self.kc_bracketleft, self.kc_bracketright,
            self.kc_slash, self.kc_backslash, self.kc_apostrophe
        ]

        # 2. In Chinese Mode: Grab letters a-z and punctuation if in Chinese punctuation mode
        if self.is_chinese_mode:
            for kc in self.alpha_keycodes:
                self._grab(kc, 0)
            if self.is_chinese_punct:
                for kc in punct_keys:
                    if kc:
                        self._grab(kc, 0)
                        self._grab(kc, X.ShiftMask)
            else:
                for kc in punct_keys:
                    if kc:
                        self._ungrab(kc, 0)
                        self._ungrab(kc, X.ShiftMask)

            # In full-width mode, intercept space to output full-width space
            if self.is_full_width and not self.is_composing:
                self._grab(self.kc_space, 0)
        else:
            for kc in self.alpha_keycodes:
                self._ungrab(kc, 0)
            for kc in punct_keys:
                if kc:
                    self._ungrab(kc, 0)
                    self._ungrab(kc, X.ShiftMask)

        # 3. In Composing State: Grab Space, digits 1-9, Backspace, Tab, Escape, Arrows, Pagination
        composing_keys = [
            self.kc_space, self.kc_return, self.kc_tab, self.kc_backspace,
            self.kc_escape, self.kc_grave, self.kc_down, self.kc_up,
            self.kc_minus, self.kc_equal, self.kc_bracketleft, self.kc_bracketright,
            self.kc_comma, self.kc_period, self.kc_semicolon, self.kc_slash,
            self.kc_backslash, self.kc_apostrophe
        ]
        if self.is_chinese_mode and self.is_composing:
            for kc in composing_keys:
                if kc: self._grab(kc, 0)
            for kc in self.digit_keycodes:
                self._grab(kc, 0)
        else:
            for kc in composing_keys:
                if not (self.is_chinese_mode and self.is_chinese_punct and kc in punct_keys):
                    if not (self.is_chinese_mode and self.is_full_width and kc == self.kc_space):
                        if kc: self._ungrab(kc, 0)
            for kc in self.digit_keycodes:
                self._ungrab(kc, 0)

        self.display.sync()

    def set_chinese_mode(self, enabled: bool):
        """Set Chinese typing mode state and refresh grabs."""
        self.is_chinese_mode = enabled
        self.update_grabs()

    def set_chinese_punct(self, enabled: bool):
        """Set Chinese punctuation state and refresh grabs."""
        self.is_chinese_punct = enabled
        self.update_grabs()

    def set_full_width(self, enabled: bool):
        """Set Full-width character state."""
        self.is_full_width = enabled
        self.update_grabs()

    def set_composing(self, composing: bool):
        """Update composing state and refresh grabs."""
        if self.is_composing != composing:
            self.is_composing = composing
            self.update_grabs()
            if not composing and self.display:
                try:
                    self.display.ungrab_keyboard(X.CurrentTime)
                    self.display.sync()
                except Exception:
                    pass

    def suspend_grabs(self):
        """Temporarily ungrab all keys and release active keyboard grab."""
        if not self.display or not self.root:
            return
        try:
            self.display.ungrab_keyboard(X.CurrentTime)
            self.root.ungrab_key(X.AnyKey, X.AnyModifier)
            self.display.sync()
        except Exception:
            pass

    def resume_grabs(self):
        """Re-apply key grabs according to current mode and state."""
        self.update_grabs()

    def start(self):
        """Start X11 event interception loop in background thread."""
        if self.running or not self.display:
            return
        self.running = True
        self.update_grabs()

        def _loop():
            while self.running:
                try:
                    ev = self.display.next_event()
                    if not self.running:
                        break

                    if ev.type == X.KeyPress:
                        self._handle_x_key_press(ev)
                    elif ev.type == X.KeyRelease:
                        self._handle_x_key_release(ev)
                except Exception as e:
                    if self.running:
                        time.sleep(0.05)

        self.thread = threading.Thread(target=_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop grabber and release all keys."""
        self.running = False
        if self.root:
            try:
                self.root.ungrab_key(X.AnyKey, X.AnyModifier)
                self.display.sync()
            except Exception:
                pass
        if self.display:
            try:
                self.display.close()
            except Exception:
                pass
            self.display = None
            self.root = None

    def __del__(self):
        self.stop()

    def _handle_x_key_press(self, ev):
        kc = ev.detail
        state = ev.state

        # Check Ctrl+Alt+Escape emergency panic exit (P1-3: handled immediately in X thread, never queued to GLib)
        is_ctrl = bool(state & X.ControlMask)
        is_alt = bool(state & X.Mod1Mask)
        if kc == self.kc_escape and is_ctrl and is_alt:
            print("[KeyboardGrabber] Emergency panic hotkey (Ctrl+Alt+Escape) triggered in X listener thread!")
            try:
                self.stop()
            except Exception:
                pass
            if self.on_panic_exit:
                try:
                    self.on_panic_exit()
                except Exception as e:
                    print(f"[KeyboardGrabber] Panic callback error: {e}")
            else:
                os._exit(0)
            return

        # Check Ctrl+Space toggle
        if kc == self.kc_space and is_ctrl:
            if self.on_mode_toggle:
                GLib.idle_add(self.on_mode_toggle)
            return

        is_shift = bool(state & X.ShiftMask)

        # Check Ctrl+. toggle Chinese / English punctuation
        if kc == self.kc_period and is_ctrl:
            if self.on_punct_toggle:
                GLib.idle_add(self.on_punct_toggle)
            return

        # Check Shift+Space toggle Full-width / Half-width characters
        if kc == self.kc_space and is_shift:
            if self.on_fullwidth_toggle:
                GLib.idle_add(self.on_fullwidth_toggle)
            return

        # Track v and space keys for Push-To-Talk (v+Space hold)
        if kc == self.kc_v:
            self.v_pressed = True
        elif kc == self.kc_space:
            self.space_pressed = True

        # Check v + Space combination
        if self.v_pressed and self.space_pressed:
            if not self.voice_recording and not self.voice_timer_id:
                def _trigger_ptt():
                    self.voice_timer_id = None
                    if self.v_pressed and self.space_pressed:
                        self.voice_recording = True
                        if self.on_voice_toggle:
                            self.on_voice_toggle(True)
                    return False

                self.voice_timer_id = GLib.timeout_add(150, _trigger_ptt)
            return

        # If voice recording active, suppress repeat keys
        if self.voice_recording:
            return

        # Map to engine key name
        key_name = None
        if kc in self.alpha_keycodes:
            key_name = self.alpha_keycodes[kc]
        elif kc in self.digit_keycodes:
            key_name = self.digit_keycodes[kc]
        elif kc == self.kc_space:
            key_name = " "
        elif kc == self.kc_return:
            key_name = "Enter"
        elif kc == self.kc_tab:
            key_name = "Tab"
        elif kc == self.kc_backspace:
            key_name = "Backspace"
        elif kc == self.kc_escape:
            key_name = "Escape"
        elif kc == self.kc_grave:
            key_name = "`"
        elif kc == self.kc_down:
            key_name = "ArrowDown"
        elif kc == self.kc_up:
            key_name = "ArrowUp"
        elif kc == self.kc_minus:
            key_name = "-"
        elif kc == self.kc_equal:
            key_name = "="
        elif kc == self.kc_bracketleft:
            key_name = "{" if is_shift else "["
        elif kc == self.kc_bracketright:
            key_name = "}" if is_shift else "]"
        elif kc == self.kc_comma:
            key_name = "<" if is_shift else ","
        elif kc == self.kc_period:
            key_name = ">" if is_shift else "."
        elif kc == self.kc_semicolon:
            key_name = ":" if is_shift else ";"
        elif kc == self.kc_slash:
            key_name = "?" if is_shift else "/"
        elif kc == self.kc_backslash:
            key_name = "|" if is_shift else "\\"
        elif hasattr(self, "kc_apostrophe") and kc == self.kc_apostrophe:
            key_name = '"' if is_shift else "'"

        if key_name and self.on_key_event:
            GLib.idle_add(self.on_key_event, key_name, True, is_shift, kc)

    def _handle_x_key_release(self, ev):
        kc = ev.detail

        was_v = (kc == self.kc_v)
        was_space = (kc == self.kc_space)

        if was_v:
            self.v_pressed = False
        if was_space:
            self.space_pressed = False

        if was_v or was_space:
            # Cancel timer if released before 150ms
            if self.voice_timer_id:
                GLib.source_remove(self.voice_timer_id)
                self.voice_timer_id = None

            # Stop voice recording on release
            if self.voice_recording:
                self.voice_recording = False
                if self.on_voice_toggle:
                    GLib.idle_add(self.on_voice_toggle, False)
