import unittest
import time
from core.ai_service import AIService


class TestAIService(unittest.TestCase):
    def setUp(self):
        self.ai = AIService()

    def test_predict_next_words_sync(self):
        # 1. Prediction for context ending in '今天'
        preds = self.ai.predict_next_words("我们今天")
        self.assertIsInstance(preds, list)
        self.assertGreater(len(preds), 0)
        self.assertIn("天气真好", preds)

        # 2. Prediction for '人工智能'
        preds_ai = self.ai.predict_next_words("探讨人工智能")
        self.assertIn("技术应用", preds_ai)

    def test_predict_next_words_async(self):
        result_box = []
        done_flag = [False]

        def _callback(items):
            result_box.extend(items)
            done_flag[0] = True

        self.ai.predict_next_words_async("今天", "", _callback)
        # Give worker thread up to 1 second
        for _ in range(20):
            if done_flag[0]:
                break
            time.sleep(0.05)

        self.assertTrue(done_flag[0])
        self.assertGreater(len(result_box), 0)
        self.assertIn("天气真好", result_box)

    def test_rewrite_oral_fillers(self):
        raw = "呃言墨输入法那个非常好用就是说"
        cleaned = self.ai.rewrite_text(raw)
        self.assertNotIn("呃", cleaned)
        self.assertNotIn("那个", cleaned)
        self.assertNotIn("就是说", cleaned)
        self.assertTrue(cleaned.endswith("。"))


if __name__ == "__main__":
    unittest.main()
