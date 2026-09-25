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


if __name__ == "__main__":
    unittest.main()
