"""
Unit and integration tests for Text Injection and Comprehensive Lexicon Coverage in YanMo IME.
"""

import unittest
from core.engine import YanMoEngine
from core.models import InputMode
from ui.injector import TextInjector


class TestLexiconAndInjection(unittest.TestCase):
    def setUp(self):
        self.engine = YanMoEngine()
        self.injector = TextInjector()

    def test_basic_vocabulary_coverage(self):
        """Ensure common Chinese characters and everyday phrases are all covered."""
        cases = {
            "wo": "我",
            "ni": "你",
            "ta": "他",
            "de": "的",
            "shi": "是",
            "zai": "在",
            "you": "有",
            "zhe": "这",
            "ge": "个",
            "ren": "人",
            "zhong": "中",
            "guo": "国",
            "shuo": "说",
            "men": "们",
            "nihao": "你好",
            "zhongguo": "中国",
            "shurufa": "输入法",
            "rengongzhineng": "人工智能",
        }

        for py, expected_char in cases.items():
            self.engine.reset()
            for ch in py:
                self.engine.feed_key(ch)
            cands = [c.text for c in self.engine.state.candidates]
            self.assertIn(
                expected_char,
                cands,
                f"Expected '{expected_char}' to be in candidates for '{py}', but got {cands[:5]}"
            )

    def test_number_key_commit(self):
        """Verify committing candidate at specified 1-based index."""
        self.engine.reset()
        for ch in "ni":
            self.engine.feed_key(ch)
        self.assertGreaterEqual(len(self.engine.state.candidates), 2)
        second_cand = self.engine.state.candidates[1].text

        # Press '2'
        consumed = self.engine.feed_key("2")
        self.assertTrue(consumed)
        self.assertEqual(self.engine.state.committed_text, second_cand)
        self.assertEqual(self.engine.state.mode, InputMode.IDLE)

    def test_space_key_commit(self):
        """Verify pressing space commits first candidate."""
        self.engine.reset()
        for ch in "wo":
            self.engine.feed_key(ch)
        first_cand = self.engine.state.candidates[0].text
        self.assertEqual(first_cand, "我")

        # Press ' '
        consumed = self.engine.feed_key(" ")
        self.assertTrue(consumed)
        self.assertEqual(self.engine.state.committed_text, "我")
        self.assertEqual(self.engine.state.mode, InputMode.IDLE)

    def test_injector_clipboard_update(self):
        """Verify TextInjector correctly loads text into clipboard."""
        test_text = "言墨输入法测试文本"
        self.injector.inject_text(test_text)
        read_back = self.injector.clipboard.wait_for_text()
        self.assertEqual(read_back, test_text)


if __name__ == "__main__":
    unittest.main()
