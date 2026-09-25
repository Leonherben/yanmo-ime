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


if __name__ == "__main__":
    unittest.main()
