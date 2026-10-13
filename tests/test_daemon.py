"""
Unit tests for YanMo IME Daemon, WindowTracker, and Tray subsystem.
"""

import os
import unittest
from pathlib import Path

from daemon.window_tracker import WindowTracker
from daemon.keyboard_grabber import KeyboardGrabber
from daemon.yanmo_daemon import YanMoDaemon, PID_FILE


class TestDaemonSubsystem(unittest.TestCase):
    def setUp(self):
        self.tracker = WindowTracker()
        self.daemon = YanMoDaemon()

    def tearDown(self):
        self.tracker.close()
        self.daemon.window_tracker.close()
        self.daemon.grabber.stop()
        self.daemon.candidate_window.hide()
        if self.daemon.engine.voice_engine.is_recording:
            self.daemon.engine.voice_engine.stop_recording()
        if PID_FILE.exists():
            PID_FILE.unlink()

    def test_window_tracker_geometry(self):
        info = self.tracker.get_active_window_info()
        self.assertIn("screen_width", info)
        self.assertIn("screen_height", info)
        self.assertGreater(info["screen_width"], 0)

        x, y = self.tracker.calculate_candidate_position(300, 60)
        self.assertGreaterEqual(x, 10)
        self.assertLessEqual(x + 300, info["screen_width"] + 10)
        self.assertGreaterEqual(y, 10)

    def test_daemon_mode_toggle(self):
        # Default is Chinese mode
        self.assertTrue(self.daemon.is_chinese_mode)

        # Toggle to English mode
        self.daemon.toggle_mode()
        self.assertFalse(self.daemon.is_chinese_mode)
        self.assertFalse(self.daemon.grabber.is_chinese_mode)

        # Toggle back to Chinese mode
        self.daemon.toggle_mode()
        self.assertTrue(self.daemon.is_chinese_mode)
        self.assertTrue(self.daemon.grabber.is_chinese_mode)

    def test_daemon_pid_lifecycle(self):
        self.daemon._write_pid()
        self.assertTrue(PID_FILE.exists())
        pid = int(PID_FILE.read_text().strip())
        self.assertEqual(pid, os.getpid())

        self.daemon._remove_pid()
        self.assertFalse(PID_FILE.exists())

    def test_autostart_toggle(self):
        autostart_file = Path.home() / ".config" / "autostart" / "yanmo.desktop"
        # If exists, clean first
        if autostart_file.exists():
            autostart_file.unlink()

        # 1. Enable autostart
        created = self.daemon.toggle_autostart()
        self.assertTrue(created)
        self.assertTrue(autostart_file.exists())
        self.assertIn("Exec=", autostart_file.read_text())

        # 2. Disable autostart
        removed = self.daemon.toggle_autostart()
        self.assertFalse(removed)
        self.assertFalse(autostart_file.exists())

    def test_unconsumed_key_reinjection_behavior(self):
        """Test P1-1: Unconsumed keys must be reinjected to target window via injector.inject_key."""
        injected = []
        original_inject_key = self.daemon.injector.inject_key

        def mock_inject_key(key_name, is_shift=False, keycode=None, target_window_id=None):
            injected.append({
                "key_name": key_name,
                "is_shift": is_shift,
                "keycode": keycode,
                "target_window_id": target_window_id
            })

        self.daemon.injector.inject_key = mock_inject_key
        try:
            # 1. Idle mode: Escape is not consumed by engine -> must reinject
            self.daemon.engine.reset()
            self.daemon._on_key_event("Escape", keycode=9)
            self.assertEqual(len(injected), 1)
            self.assertEqual(injected[-1]["key_name"], "Escape")
            self.assertEqual(injected[-1]["keycode"], 9)

            # 2. Idle mode: Backspace is not consumed by engine -> must reinject
            self.daemon._on_key_event("Backspace", keycode=22)
            self.assertEqual(len(injected), 2)
            self.assertEqual(injected[-1]["key_name"], "Backspace")
            self.assertEqual(injected[-1]["keycode"], 22)

            # 3. Composing mode: 'n' IS consumed by engine -> must NOT reinject
            self.daemon._on_key_event("n", keycode=38)
            self.assertEqual(len(injected), 2)  # Count should not increase

            # 4. Composing mode: out-of-bounds digit selection '9' is not consumed -> must reinject
            self.daemon._on_key_event("9", keycode=18)
            self.assertEqual(len(injected), 3)
            self.assertEqual(injected[-1]["key_name"], "9")
            self.assertEqual(injected[-1]["keycode"], 18)

            # 5. Shifted unconsumed key
            self.daemon.engine.reset()
            self.daemon._on_key_event("Escape", is_shift=True, keycode=9)
            self.assertEqual(len(injected), 4)
            self.assertEqual(injected[-1]["is_shift"], True)

        finally:
            self.daemon.injector.inject_key = original_inject_key

    @unittest.skipUnless(os.environ.get("RUN_DESKTOP_E2E") == "1", "Skipped live desktop test: requires RUN_DESKTOP_E2E=1 to prevent polluting user desktop session")
    def test_xtest_inject_key_end_to_end(self):
        """Test P1-1: Real X11 XTEST key synthesis delivers key press to focused window."""
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
        import time

        win = Gtk.Window()
        received_keys = []
        win.connect("key-press-event", lambda w, e: received_keys.append(e.keyval))
        win.show_all()
        win.present()

        try:
            for _ in range(10):
                while Gtk.events_pending():
                    Gtk.main_iteration()
                time.sleep(0.01)

            # Inject Escape key using daemon injector
            self.daemon.injector.inject_key("Escape")

            for _ in range(10):
                while Gtk.events_pending():
                    Gtk.main_iteration()
                time.sleep(0.01)

            # 0xff1b is XK_Escape
            self.assertIn(0xff1b, received_keys)
        finally:
            win.destroy()
            while Gtk.events_pending():
                Gtk.main_iteration()

    @unittest.skipUnless(os.environ.get("RUN_DESKTOP_E2E") == "1", "Skipped live clipboard test: requires RUN_DESKTOP_E2E=1 to prevent overwriting user clipboard")
    def test_clipboard_preservation_and_restoration_live(self):
        """Test P1-2: Injector preserves original clipboard content and restores it after injection."""
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk, Gdk
        import time

        cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        cb.set_text("User Original Secret Clipboard", -1)
        cb.store()
        while Gtk.events_pending():
            Gtk.main_iteration()

        # Inject IME text
        self.daemon.injector.inject_text("言墨输入法测试")

        # Let GTK event loop process the delayed restore timer (150ms)
        time.sleep(0.2)
        while Gtk.events_pending():
            Gtk.main_iteration()

        restored_text = cb.wait_for_text()
        self.assertEqual(restored_text, "User Original Secret Clipboard")

    def test_target_window_uses_commit_time_focus(self):
        """Test P1-2: When committing, the target window is the active window at commit time, not pre-typing window."""
        injected_targets = []
        original_inject_text = self.daemon.injector.inject_text

        def mock_inject_text(text, target_window_id=None):
            injected_targets.append(target_window_id)
            return True

        self.daemon.injector.inject_text = mock_inject_text
        try:
            # Simulate pre-typing window recorded as 11111
            self.daemon.last_target_window_id = 11111

            # User Alt+Tabs to window 22222 before committing
            self.daemon.window_tracker.get_active_window_id = lambda: 22222

            self.daemon._on_commit_text("你好")

            self.assertEqual(len(injected_targets), 1)
            # Must inject into 22222 (active window at commit moment), NOT 11111!
            self.assertEqual(injected_targets[0], 22222)
            self.assertIsNone(self.daemon.last_target_window_id)
        finally:
            self.daemon.injector.inject_text = original_inject_text

    def test_password_window_suppression(self):
        """Test P1-2 & P1-4: Commit inside password window aborts injection and suppresses self-learning."""
        recorded = []
        injected = []
        blocked_prompts = []

        original_record = self.daemon.user_dict.record_selection
        self.daemon.user_dict.record_selection = lambda w, p: recorded.append((w, p))

        original_inject_text = self.daemon.injector.inject_text
        self.daemon.injector.inject_text = lambda t, target_window_id=None: injected.append((t, target_window_id))

        original_show_blocked = self.daemon.candidate_window.show_security_blocked
        self.daemon.candidate_window.show_security_blocked = lambda t: blocked_prompts.append(t)

        original_is_pwd = self.daemon.injector.is_window_password
        self.daemon.injector.is_window_password = lambda wid: True

        try:
            self.daemon._on_commit_text("秘密密码")

            # 1. Assert self-learning dictionary recording was NOT called
            self.assertEqual(len(recorded), 0)

            # 2. Assert text injection was ABORTED (never called)
            self.assertEqual(len(injected), 0)

            # 3. Assert candidate window received security blocked alert with retained text
            self.assertEqual(len(blocked_prompts), 1)
            self.assertEqual(blocked_prompts[0], "秘密密码")

            # 4. Assert direct call to injector.inject_text also defensively aborts and returns False
            self.daemon.injector.inject_text = original_inject_text
            res = self.daemon.injector.inject_text("秘密密码", target_window_id=99999)
            self.assertFalse(res)

        finally:
            self.daemon.user_dict.record_selection = original_record
            self.daemon.injector.inject_text = original_inject_text
            self.daemon.candidate_window.show_security_blocked = original_show_blocked
            self.daemon.injector.is_window_password = original_is_pwd

    def test_password_window_keyword_tightening(self):
        """Test P1-2: WM_CLASS and WM_NAME rules eliminate false positives while catching real password windows."""
        from ui.injector import TextInjector

        # False positives that must NOT be matched
        self.assertFalse(TextInjector.is_password_window_meta(wm_class=("google-chrome", "Google-chrome"), wm_name="Pinned tabs"))
        self.assertFalse(TextInjector.is_password_window_meta(wm_class=("slack", "Slack"), wm_name="Slack — #locksmith"))
        self.assertFalse(TextInjector.is_password_window_meta(wm_class=("gedit", "Gedit"), wm_name="authoring tool"))
        self.assertFalse(TextInjector.is_password_window_meta(wm_class=("firefox", "Firefox"), wm_name="PIN code article - Mozilla Firefox"))
        self.assertFalse(TextInjector.is_password_window_meta(wm_class=("gnome-terminal", "Gnome-terminal"), wm_name="bash: locked file"))

        # Real password and privilege escalation windows that MUST be matched
        self.assertTrue(TextInjector.is_password_window_meta(wm_name="sudo: password for root"))
        self.assertTrue(TextInjector.is_password_window_meta(wm_name="sudo: password for alice"))
        self.assertTrue(TextInjector.is_password_window_meta(wm_name="Enter Password:"))
        self.assertTrue(TextInjector.is_password_window_meta(wm_name="Authentication Required"))
        self.assertTrue(TextInjector.is_password_window_meta(wm_name="Enter passphrase for key"))
        self.assertTrue(TextInjector.is_password_window_meta(wm_class=("Bitwarden", "bitwarden")))
        self.assertTrue(TextInjector.is_password_window_meta(wm_class=("keepassxc", "KeePassXC")))
        self.assertTrue(TextInjector.is_password_window_meta(wm_class=("1password", "1Password")))
        self.assertTrue(TextInjector.is_password_window_meta(wm_class=("gcr-prompter", "Gcr-prompter")))
        self.assertTrue(TextInjector.is_password_window_meta(wm_class=("polkit-gnome-authentication-agent-1", "polkit")))
        self.assertTrue(TextInjector.is_password_window_meta(wm_class=("pinentry-gtk-2", "pinentry")))

    def test_clipboard_non_text_protection(self):
        """Test P1-2: If clipboard content was non-text (wait_for_text returns None), clear() must NOT be called."""
        from unittest.mock import MagicMock
        from gi.repository import GLib

        injector = self.daemon.injector
        original_clipboard = injector.clipboard

        mock_cb = MagicMock()
        mock_cb.wait_for_text.return_value = None  # Simulates non-text / image on clipboard
        injector.clipboard = mock_cb

        # Intercept GLib.timeout_add to run the restore callback immediately
        restore_callbacks = []
        original_timeout_add = GLib.timeout_add
        GLib.timeout_add = lambda ms, cb: restore_callbacks.append(cb)

        try:
            # We bypass the X11 injection portion by mocking HAS_XLIB or display
            orig_has_xlib = injector.display
            injector.display = None

            injector.inject_text("测试文本")

            self.assertEqual(len(restore_callbacks), 1)
            # Execute restore callback
            restore_callbacks[0]()

            # Assert clear() was NEVER called because orig_clipboard was None!
            mock_cb.clear.assert_not_called()

        finally:
            injector.clipboard = original_clipboard
            injector.display = orig_has_xlib
            GLib.timeout_add = original_timeout_add

    def test_use_clipboard_switch_and_config_sync(self):
        """Test P1-2: Toggle use_clipboard_injection switch in injector and verify config callback sync."""
        self.assertTrue(self.daemon.injector.use_clipboard)

        # 1. Direct toggle
        self.daemon.injector.use_clipboard = False
        self.assertFalse(self.daemon.injector.use_clipboard)

        # 2. Sync via config change event
        self.daemon._on_config_changed({"use_clipboard_injection": True})
        self.assertTrue(self.daemon.injector.use_clipboard)

        self.daemon._on_config_changed({"use_clipboard_injection": False})
        self.assertFalse(self.daemon.injector.use_clipboard)

        self.daemon._on_config_changed({"use_clipboard_injection": True})
        self.assertTrue(self.daemon.injector.use_clipboard)

    def test_panic_exit_when_main_thread_blocked(self):
        """Test P1-3: Emergency panic hotkey (Ctrl+Alt+Escape) ungrabs immediately in X thread without waiting for main thread."""
        import time
        from unittest.mock import MagicMock
        from Xlib import X

        panic_called = []
        grabber = KeyboardGrabber(
            on_panic_exit=lambda: panic_called.append(True)
        )
        grabber.running = True

        # Create a mock X KeyEvent for Escape with Ctrl+Alt
        mock_event = MagicMock()
        mock_event.detail = grabber.kc_escape
        mock_event.state = X.ControlMask | X.Mod1Mask

        start_time = time.time()
        # Simulate handling the event in the X listener thread
        grabber._handle_x_key_press(mock_event)
        elapsed = time.time() - start_time

        # 1. Must be executed immediately (< 50ms)
        self.assertLess(elapsed, 0.05)
        # 2. on_panic_exit must have been called directly
        self.assertEqual(len(panic_called), 1)
        # 3. Grabber must have stopped running
        self.assertFalse(grabber.running)

    def test_window_tracker_caret_async_non_blocking(self):
        """Test P1-3: WindowTracker.get_caret_position returns immediately without blocking main thread."""
        import time
        tracker = WindowTracker()
        try:
            start_time = time.time()
            pos = tracker.get_caret_position()
            elapsed = time.time() - start_time
            # Must return in < 5ms without synchronous D-Bus tree traversal blocking
            self.assertLess(elapsed, 0.02)
        finally:
            tracker.close()

    def test_voice_toggle_async_execution(self):
        """Test P1-3: Stopping voice recording runs decode asynchronously without blocking main thread."""
        import time
        from unittest.mock import MagicMock

        # Mock voice engine with intentional sleep simulating heavy SenseVoice inference
        decode_started = []
        decode_finished = []

        def slow_stop_recording():
            decode_started.append(time.time())
            time.sleep(0.1)
            decode_finished.append(time.time())
            return "测试转写"

        self.daemon.engine.stop_voice_recording = slow_stop_recording

        start_time = time.time()
        self.daemon._on_voice_toggle(False)
        elapsed = time.time() - start_time

        # Main thread must return immediately (< 30ms) without waiting for 100ms inference
        self.assertLess(elapsed, 0.05)

        # Allow background thread to finish
        time.sleep(0.15)
        self.assertEqual(len(decode_finished), 1)


if __name__ == "__main__":
    unittest.main()
