"""
X11 Global Keyboard Interceptor for YanMo IME Daemon.
Listens to global hotkeys (Ctrl+Space, v+Space) and intercepts typing keys
when Chinese input mode is active.
"""

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
        on_voice_toggle: Optional[Callable[[bool], None]] = None,
    ):
        self.on_key_event = on_key_event
        self.on_mode_toggle = on_mode_toggle
        self.on_voice_toggle = on_voice_toggle

        self.display = display.Display() if HAS_XLIB else None
        self.root = self.display.screen().root if self.display else None

        self.running = False
        self.thread: Optional[threading.Thread] = None

        self.is_chinese_mode = False
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
        self.kc_v = self.display.keysym_to_keycode(XK.XK_v)
        self.kc_tab = self.display.keysym_to_keycode(XK.XK_Tab)
        self.kc_backspace = self.display.keysym_to_keycode(XK.XK_BackSpace)
        self.kc_escape = self.display.keysym_to_keycode(XK.XK_Escape)
        self.kc_grave = self.display.keysym_to_keycode(XK.XK_grave)

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

        # 1. Global Activation Hotkeys (Always grabbed): Ctrl+Space
        self._grab(self.kc_space, X.ControlMask)

        # 2. In Chinese Mode: Grab letters a-z
        if self.is_chinese_mode:
            for kc in self.alpha_keycodes:
                self._grab(kc, 0)
        else:
            for kc in self.alpha_keycodes:
                self._ungrab(kc, 0)

        # 3. In Composing State: Grab Space, digits 1-9, Backspace, Tab, Escape
        if self.is_chinese_mode and self.is_composing:
            self._grab(self.kc_space, 0)
            self._grab(self.kc_tab, 0)
            self._grab(self.kc_backspace, 0)
            self._grab(self.kc_escape, 0)
            self._grab(self.kc_grave, 0)
            for kc in self.digit_keycodes:
                self._grab(kc, 0)
        else:
            self._ungrab(self.kc_space, 0)
            self._ungrab(self.kc_tab, 0)
            self._ungrab(self.kc_backspace, 0)
            self._ungrab(self.kc_escape, 0)
            self._ungrab(self.kc_grave, 0)
            for kc in self.digit_keycodes:
                self._ungrab(kc, 0)

        self.display.sync()

    def set_chinese_mode(self, enabled: bool):
        """Set Chinese typing mode state and refresh grabs."""
        self.is_chinese_mode = enabled
        self.update_grabs()

    def set_composing(self, composing: bool):
        """Update composing state and refresh grabs."""
        if self.is_composing != composing:
            self.is_composing = composing
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

    def _handle_x_key_press(self, ev):
        kc = ev.detail
        state = ev.state

        # Check Ctrl+Space toggle
        is_ctrl = bool(state & X.ControlMask)
        if kc == self.kc_space and is_ctrl:
            if self.on_mode_toggle:
                GLib.idle_add(self.on_mode_toggle)
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
        elif kc == self.kc_tab:
            key_name = "Tab"
        elif kc == self.kc_backspace:
            key_name = "Backspace"
        elif kc == self.kc_escape:
            key_name = "Escape"
        elif kc == self.kc_grave:
            key_name = "`"

        if key_name and self.on_key_event:
            GLib.idle_add(self.on_key_event, key_name, True)

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
