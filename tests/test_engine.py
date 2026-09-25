import unittest
import tempfile
from pathlib import Path
from core.engine import YanMoEngine
from core.models import InputMode


class TestYanMoEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.user_db = Path(self.temp_dir.name) / "test_user.db"
        self.engine = YanMoEngine(user_db_path=self.user_db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pinyin_typing_and_selection(self):
        self.engine.feed_key("h")
        self.engine.feed_key("e")

        self.assertEqual(self.engine.state.mode, InputMode.COMPOSING)
        self.assertEqual(self.engine.state.pinyin_buffer, "he")
        self.assertTrue(len(self.engine.state.candidates) > 0)

        # Select first candidate via Space
        self.engine.feed_key(" ")
        self.assertEqual(self.engine.state.committed_text, "和")
        self.assertEqual(self.engine.state.mode, InputMode.IDLE)

    def test_tab_pinyin_radical_filtering(self):
        # Type 'h', 'e'
        self.engine.feed_key("h")
        self.engine.feed_key("e")

        # Press Tab
        self.engine.feed_key("Tab")
        self.assertEqual(self.engine.state.mode, InputMode.RADICAL_FILTER)

        # Type 's', 'h', 'u', 'i'
        for char in "shui":
            self.engine.feed_key(char)

        candidate_texts = [c.text for c in self.engine.state.candidates]
        self.assertIn("河", candidate_texts)
        self.assertNotIn("核", candidate_texts)

    def test_tab_stroke_filtering_hspdz(self):
        # Type 'h', 'e'
        self.engine.feed_key("h")
        self.engine.feed_key("e")

        # Press Tab
        self.engine.feed_key("Tab")

        # Type 'd' (点/捺) -> should match '河' (氵水部首笔为点)
        self.engine.feed_key("d")
        candidate_texts = [c.text for c in self.engine.state.candidates]
        self.assertIn("河", candidate_texts)

        # Backspace, then type 'h' (横) -> should match '核' (木部首笔为横)
        self.engine.feed_key("Backspace")
        self.engine.feed_key("h")
        h_candidates = [c.text for c in self.engine.state.candidates]
        self.assertIn("核", h_candidates)
        self.assertNotIn("河", h_candidates)

    def test_visual_radical_click(self):
        self.engine.feed_key("h")
        self.engine.feed_key("e")

        self.engine.apply_visual_radical_filter("木")
        self.assertEqual(self.engine.state.mode, InputMode.RADICAL_FILTER)

        candidate_texts = [c.text for c in self.engine.state.candidates]
        self.assertIn("核", candidate_texts)
        self.assertNotIn("河", candidate_texts)

    def test_standalone_radical_lookup(self):
        self.engine.apply_visual_radical_filter("氵")
        candidate_texts = [c.text for c in self.engine.state.candidates]
        self.assertTrue(len(candidate_texts) > 0)
        self.assertIn("河", candidate_texts)
        self.assertIn("海", candidate_texts)

    def test_backspace_navigation(self):
        self.engine.feed_key("h")
        self.engine.feed_key("e")
        self.engine.feed_key("Tab")
        self.engine.feed_key("s")

        self.assertEqual(self.engine.state.radical_buffer, "s")
        self.engine.feed_key("Backspace")
        self.assertEqual(self.engine.state.radical_buffer, "")

        self.engine.feed_key("Backspace")
        self.assertEqual(self.engine.state.mode, InputMode.COMPOSING)
        self.assertEqual(self.engine.state.pinyin_buffer, "he")

    def test_dynamic_learning_and_promotion(self):
        self.engine.feed_key("h")
        self.engine.feed_key("e")

        initial_candidates = [c.text for c in self.engine.state.candidates]
        target_idx = initial_candidates.index("何")
        self.assertGreater(target_idx, 0)

        self.engine.feed_key(str(target_idx + 1))
        self.assertEqual(self.engine.state.committed_text, "何")

        # Type again -> promoted
        self.engine.feed_key("h")
        self.engine.feed_key("e")
        new_candidates = [c.text for c in self.engine.state.candidates]
        self.assertEqual(new_candidates[0], "何")
        self.assertEqual(self.engine.state.candidates[0].comment, "自学词")


if __name__ == "__main__":
    unittest.main()
