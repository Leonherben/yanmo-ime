"""
Unit tests for Push-To-Talk voice dictation shortcut (v + Space hold to speak, release to end).
"""

import unittest
from unittest.mock import MagicMock
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from yanmo_gui import YanMoDesktopApp


class TestPushToTalk(unittest.TestCase):
    def setUp(self):
        self.app = YanMoDesktopApp()

    def tearDown(self):
        if self.app.voice_timer_id:
            GLib.source_remove(self.app.voice_timer_id)
            self.app.voice_timer_id = None
        if self.app.engine.voice_engine.is_recording:
            self.app.engine.voice_engine.stop_recording()
        self.app.candidate_window.hide()
        self.app.sandbox_window.hide()

    def _create_key_event(self, keyval: int, event_type: Gdk.EventType) -> Gdk.EventKey:
        event = Gdk.EventKey()
        event.type = event_type
        event.keyval = keyval
        return event

    def test_v_space_hold_and_release_lifecycle(self):
        # 1. Press 'v'
        ev_v_press = self._create_key_event(Gdk.KEY_v, Gdk.EventType.KEY_PRESS)
        consumed = self.app._on_key_press(None, ev_v_press)
        self.assertTrue(self.app.v_pressed)
        self.assertFalse(self.app.space_pressed)
        self.assertEqual(self.app.engine.state.pinyin_buffer, "v")

        # 2. Press 'Space' while 'v' is held
        ev_space_press = self._create_key_event(Gdk.KEY_space, Gdk.EventType.KEY_PRESS)
        consumed = self.app._on_key_press(None, ev_space_press)
        self.assertTrue(consumed)
        self.assertTrue(self.app.space_pressed)
        self.assertIsNotNone(self.app.voice_timer_id)

        # 3. Simulate timer trigger (hold threshold passed)
        self.app._on_voice_long_press_triggered()
        self.assertTrue(self.app.voice_recording_active)
        self.assertTrue(self.app.engine.voice_engine.is_recording)
        # Verify the stray 'v' was cleared
        self.assertEqual(self.app.engine.state.pinyin_buffer, "")

        # 4. Release 'Space' -> Push-To-Talk should end and transcribe
        ev_space_release = self._create_key_event(Gdk.KEY_space, Gdk.EventType.KEY_RELEASE)
        consumed = self.app._on_key_release(None, ev_space_release)
        self.assertTrue(consumed)
        self.assertFalse(self.app.space_pressed)
        self.assertFalse(self.app.voice_recording_active)
        self.assertFalse(self.app.engine.voice_engine.is_recording)

    def test_quick_tap_does_not_trigger_voice(self):
        # 1. Press 'v'
        ev_v_press = self._create_key_event(Gdk.KEY_v, Gdk.EventType.KEY_PRESS)
        self.app._on_key_press(None, ev_v_press)

        # 2. Press 'Space'
        ev_space_press = self._create_key_event(Gdk.KEY_space, Gdk.EventType.KEY_PRESS)
        self.app._on_key_press(None, ev_space_press)
        self.assertIsNotNone(self.app.voice_timer_id)

        # 3. Release 'Space' immediately before 150ms timer triggers
        ev_space_release = self._create_key_event(Gdk.KEY_space, Gdk.EventType.KEY_RELEASE)
        self.app._on_key_release(None, ev_space_release)

        # Timer should be cancelled and voice recording should NOT be active
        self.assertIsNone(self.app.voice_timer_id)
        self.assertFalse(self.app.voice_recording_active)
        self.assertFalse(self.app.engine.voice_engine.is_recording)


if __name__ == "__main__":
    unittest.main()
