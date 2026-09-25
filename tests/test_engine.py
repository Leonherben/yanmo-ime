import unittest
from core.engine import YanMoEngine
from core.models import InputMode


class TestYanMoEngine(unittest.TestCase):
    def setUp(self):
        self.engine = YanMoEngine()

    def test_pinyin_typing_and_selection(self):
        # Type 'h', 'e'
        self.engine.feed_key("h")
        self.engine.feed_key("e")

        self.assertEqual(self.engine.state.mode, InputMode.COMPOSING)
        self.assertEqual(self.engine.state.pinyin_buffer, "he")
        self.assertTrue(len(self.engine.state.candidates) > 0)

        # First candidates should include common 'he' words / chars like '和'
        candidate_texts = [c.text for c in self.engine.state.candidates]
        self.assertIn("和", candidate_texts)
        self.assertIn("河", candidate_texts)

        # Select first candidate via Space
        self.engine.feed_key(" ")
        self.assertEqual(self.engine.state.committed_text, "和")
        self.assertEqual(self.engine.state.mode, InputMode.IDLE)

    def test_tab_radical_filtering(self):
        # Type 'h', 'e'
        self.engine.feed_key("h")
        self.engine.feed_key("e")

        # Press Tab to enter radical filter mode
        consumed = self.engine.feed_key("Tab")
        self.assertTrue(consumed)
        self.assertEqual(self.engine.state.mode, InputMode.RADICAL_FILTER)

        # Type radical 's', 'h', 'u', 'i' (水/氵)
        for char in "shui":
            self.engine.feed_key(char)

        self.assertEqual(self.engine.state.radical_buffer, "shui")
        candidate_texts = [c.text for c in self.engine.state.candidates]

        # '河' must be present
        self.assertIn("河", candidate_texts)
        # Non-water characters like '核' (木部) and '荷' (艹部) MUST NOT be present
        self.assertNotIn("核", candidate_texts)
        self.assertNotIn("荷", candidate_texts)

        # Select '河' using number key '1'
        self.engine.feed_key("1")
        self.assertEqual(self.engine.state.committed_text, "河")
        self.assertEqual(self.engine.state.mode, InputMode.IDLE)

    def test_visual_radical_click(self):
        # Type 'h', 'e'
        self.engine.feed_key("h")
        self.engine.feed_key("e")

        # Simulate clicking the '木' radical button on the UI corner
        self.engine.apply_visual_radical_filter("木")
        self.assertEqual(self.engine.state.mode, InputMode.RADICAL_FILTER)

        candidate_texts = [c.text for c in self.engine.state.candidates]
        self.assertIn("核", candidate_texts)
        self.assertNotIn("河", candidate_texts)

    def test_backspace_navigation(self):
        self.engine.feed_key("h")
        self.engine.feed_key("e")
        self.engine.feed_key("Tab")
        self.engine.feed_key("s")

        self.assertEqual(self.engine.state.radical_buffer, "s")
        self.engine.feed_key("Backspace")
        self.assertEqual(self.engine.state.radical_buffer, "")

        # Second backspace exits radical mode back to composing
        self.engine.feed_key("Backspace")
        self.assertEqual(self.engine.state.mode, InputMode.COMPOSING)
        self.assertEqual(self.engine.state.pinyin_buffer, "he")


if __name__ == "__main__":
    unittest.main()
