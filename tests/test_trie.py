import unittest
from core.trie import PinyinTrie
from core.models import Candidate


class TestPinyinTrie(unittest.TestCase):
    def setUp(self):
        self.trie = PinyinTrie()
        self.trie.insert("he", Candidate("和", "he", 9999))
        self.trie.insert("he", Candidate("合", "he", 9800))
        self.trie.insert("he", Candidate("河", "he", 9500))
        self.trie.insert("heshui", Candidate("喝水", "heshui", 8500))
        self.trie.insert("heping", Candidate("和平", "heping", 9200))
        self.trie.insert("zhongwen", Candidate("中文", "zhongwen", 9900))

    def test_search_exact(self):
        cands = self.trie.search_exact("he")
        self.assertEqual(len(cands), 3)
        texts = [c.text for c in cands]
        self.assertIn("和", texts)
        self.assertIn("合", texts)
        self.assertIn("河", texts)

    def test_search_prefix(self):
        # Prefix "he" should match "he", "heshui", "heping"
        cands = self.trie.search_prefix("he", limit=10)
        self.assertTrue(len(cands) >= 5)
        texts = [c.text for c in cands]
        self.assertIn("和", texts)
        self.assertIn("和平", texts)
        self.assertIn("喝水", texts)
        # Should NOT match "zhongwen"
        self.assertNotIn("中文", texts)

    def test_empty_search(self):
        self.assertEqual(self.trie.search_exact("xyz"), [])
        self.assertEqual(self.trie.search_prefix("xyz"), [])


if __name__ == "__main__":
    unittest.main()
