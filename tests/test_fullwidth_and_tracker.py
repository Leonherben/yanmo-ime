"""
Unit tests for full-width character/punctuation toggles and window tracker drag position memory.
"""

import unittest
from core.cpp_engine import YanMoCppEngine
from core.engine import YanMoEngine
from daemon.window_tracker import WindowTracker


class TestFullWidthAndTracker(unittest.TestCase):
    def setUp(self):
        self.cpp_engine = YanMoCppEngine()
        self.engine = YanMoEngine()
        self.tracker = WindowTracker()

    def tearDown(self):
        self.tracker.close()

    def test_full_width_punct_toggle(self):
        # 1. Default should be full_width_punct = True
        self.assertTrue(self.cpp_engine.is_full_width_punct())
        self.assertTrue(self.engine.is_full_width_punct())

        # Test comma mapping in idle
        self.cpp_engine.reset()
        consumed = self.cpp_engine.feed_key(",")
        self.assertTrue(consumed)
        status = self.cpp_engine.get_status()
        self.assertEqual(status["committed_text"], "，")

        # 2. Toggle full_width_punct to False (English punctuation mode)
        self.cpp_engine.set_full_width_punct(False)
        self.assertFalse(self.cpp_engine.is_full_width_punct())

        # In IDLE: should NOT consume punctuation so it passes through to OS natively
        self.cpp_engine.reset()
        consumed = self.cpp_engine.feed_key(",")
        self.assertFalse(consumed)

        # In COMPOSING: should commit candidate with half-width punctuation
        self.cpp_engine.reset()
        self.cpp_engine.feed_key("n")
        self.cpp_engine.feed_key("i")
        consumed = self.cpp_engine.feed_key(",")
        self.assertTrue(consumed)
        status = self.cpp_engine.get_status()
        self.assertTrue(status["committed_text"].endswith(","))

        # Reset back to True
        self.cpp_engine.set_full_width_punct(True)
        self.assertTrue(self.cpp_engine.is_full_width_punct())

    def test_full_width_char_toggle(self):
        # 1. Default should be full_width_char = False
        self.assertFalse(self.cpp_engine.is_full_width_char())
        self.assertFalse(self.engine.is_full_width_char())

        # 2. Toggle to True
        self.engine.set_full_width_char(True)
        self.assertTrue(self.engine.is_full_width_char())

        # Feed space in idle mode -> should output full-width space U+3000 (\u3000)
        self.engine.reset()
        consumed = self.engine.feed_key(" ")
        self.assertTrue(consumed)
        status = self.engine.get_status()
        self.assertEqual(status["committed_text"], "\u3000")

        # 3. Toggle back to False
        self.engine.set_full_width_char(False)
        self.assertFalse(self.engine.is_full_width_char())

    def test_clear_committed_text(self):
        self.cpp_engine.reset()
        self.cpp_engine.feed_key(",")
        status = self.cpp_engine.get_status()
        self.assertEqual(status["committed_text"], "，")

        self.cpp_engine.clear_committed_text()
        status_cleared = self.cpp_engine.get_status()
        self.assertEqual(status_cleared["committed_text"], "")

    def test_window_tracker_offset_memory(self):
        # Set user dragged position
        self.tracker.set_user_offset(250, 350, window_id=12345)
        self.assertEqual(self.tracker.custom_offset, (250, 350))
        self.assertIn(12345, self.tracker.window_offsets)

        # Clamping calculation should return a valid tuple of ints
        x, y = self.tracker.calculate_candidate_position()
        self.assertIsInstance(x, int)
        self.assertIsInstance(y, int)
        self.assertGreaterEqual(x, 12)
        self.assertGreaterEqual(y, 12)

    def test_find_caret_null_safe(self):
        # Should gracefully return None when given None
        res = self.tracker._find_caret_in_element(None)
        self.assertIsNone(res)

    def test_active_window_pid(self):
        pid = self.tracker.get_active_window_pid()
        if pid is not None:
            self.assertIsInstance(pid, int)
            self.assertGreater(pid, 0)

    def test_pointer_fallback_calculation(self):
        # Even without active caret, calculate_candidate_position returns valid on-screen coordinates
        pos = self.tracker.calculate_candidate_position(cand_w=380, cand_h=50)
        self.assertIsInstance(pos, tuple)
        self.assertEqual(len(pos), 2)
        self.assertGreaterEqual(pos[0], 12)
        self.assertGreaterEqual(pos[1], 12)


if __name__ == "__main__":
    unittest.main()
