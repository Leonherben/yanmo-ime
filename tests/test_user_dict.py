import unittest
import tempfile
from pathlib import Path
from core.user_dict import UserDictionary


class TestUserDictionary(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_user.db"
        self.user_dict = UserDictionary(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_record_and_dynamic_frequency(self):
        # 1. Record selection once
        self.user_dict.record_selection("言墨", "yanmo")
        cands = self.user_dict.get_candidates("yanmo")
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0].text, "言墨")
        initial_freq = cands[0].freq

        # 2. Record again -> frequency must increase
        self.user_dict.record_selection("言墨", "yanmo")
        cands2 = self.user_dict.get_candidates("yanmo")
        self.assertGreater(cands2[0].freq, initial_freq)

    def test_delete_word(self):
        self.user_dict.record_selection("错词", "cuoci")
        self.assertEqual(len(self.user_dict.get_candidates("cuoci")), 1)

        # Delete it
        success = self.user_dict.delete_word("错词")
        self.assertTrue(success)
        self.assertEqual(len(self.user_dict.get_candidates("cuoci")), 0)

    def test_export_and_import(self):
        self.user_dict.record_selection("输入法", "shurufa")
        self.user_dict.record_selection("言墨", "yanmo")

        export_file = Path(self.temp_dir.name) / "export.txt"
        exported_count = self.user_dict.export_to_txt(export_file)
        self.assertEqual(exported_count, 2)

        # Create a new user dict and import
        new_db_path = Path(self.temp_dir.name) / "imported_user.db"
        new_user_dict = UserDictionary(db_path=new_db_path)
        imported_count = new_user_dict.import_from_txt(export_file)
        self.assertEqual(imported_count, 2)
        self.assertEqual(len(new_user_dict.get_candidates("shurufa")), 1)

    def test_import_plain_wordlist(self):
        plain_file = Path(self.temp_dir.name) / "words.txt"
        plain_file.write_text("言墨输入法\n人工智能\n", encoding="utf-8")
        imported = self.user_dict.import_from_file(plain_file)
        self.assertEqual(imported, 2)
        cands = self.user_dict.get_candidates("yanmoshurufa")
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0].text, "言墨输入法")

    def test_export_full_lexicon(self):
        self.user_dict.record_selection("言墨科技", "yanmokeji")
        out_file = Path(self.temp_dir.name) / "full_lexicon.tsv"
        total = self.user_dict.export_full_lexicon(out_file)
        self.assertGreater(total, 1000)
        self.assertTrue(out_file.exists())


    def test_ignore_non_chinese_or_raw_pinyin(self):
        # Raw pinyin or english should never be saved into user dict
        self.user_dict.record_selection("zenmeshuon", "zenmeshuon")
        self.user_dict.record_selection("hello", "hello")
        self.user_dict.record_selection("p", "p")
        self.assertEqual(len(self.user_dict.get_candidates("zenmeshuon")), 0)
        self.assertEqual(len(self.user_dict.get_candidates("hello")), 0)
    def test_decay_and_overflow(self):
        self.user_dict.record_selection("词条一", "citiaoyi", initial_boost=10)
        self.user_dict.record_selection("词条二", "citiaoer", initial_boost=2)
        # Apply decay
        self.user_dict.apply_decay(decay_factor=0.5, min_freq=2)
        cands1 = self.user_dict.get_candidates("citiaoyi")
        self.assertEqual(len(cands1), 1)
        self.assertEqual(cands1[0].freq, 5 * 100 + 50000)

        # Test overflow limit
        self.user_dict.cleanup_overflow(max_entries=1)
        self.assertEqual(self.user_dict.count(), 1)
        self.assertEqual(len(self.user_dict.get_candidates("citiaoyi")), 1)


if __name__ == "__main__":
    unittest.main()
