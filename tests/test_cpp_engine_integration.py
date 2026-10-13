import unittest
import tempfile
from pathlib import Path
from core.cpp_engine import YanMoCppEngine
from core.user_dict import UserDictionary


class TestCppEngineIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = YanMoCppEngine()

    def setUp(self):
        self.engine.reset()

    def _query(self, pinyin_str):
        self.engine.reset()
        for ch in pinyin_str:
            self.engine.feed_key(ch)
        cands = []
        for r in range(100):
            row_cands = self.engine.get_row_candidates(r)
            if row_cands:
                cands.extend(row_cands)
            else:
                break
        return cands

    def test_single_character_reachability(self):
        """Test previously missing characters are now reachable and well-ranked."""
        # Test 'shi'
        shi_cands = self._query("shi")
        for expected in ["是", "时", "事", "十", "石", "世", "实", "视", "识", "失", "湿", "始"]:
            self.assertIn(expected, shi_cands, f"Character {expected} should be in shi candidates")

        # Test 'zhong'
        zhong_cands = self._query("zhong")
        for expected in ["中", "种", "重", "众", "钟", "忠", "终"]:
            self.assertIn(expected, zhong_cands, f"Character {expected} should be in zhong candidates")

        # Test 'di'
        di_cands = self._query("di")
        for expected in ["地", "第", "弟", "帝", "敌", "递", "抵"]:
            self.assertIn(expected, di_cands, f"Character {expected} should be in di candidates")

    def test_pinyin_normalization(self):
        """Test typing lue/nue matches lve/nve."""
        lue_cands = self._query("lue")
        self.assertIn("略", lue_cands)

        nue_cands = self._query("nue")
        self.assertIn("虐", nue_cands)

    def test_user_lexicon_dynamic_import_and_query(self):
        """Test importing custom words and hot-reloading into C++ engine."""
        temp_dir = tempfile.TemporaryDirectory()
        user_db = Path(temp_dir.name) / "user.db"
        user_dict = UserDictionary(db_path=user_db)

        custom_file = Path(temp_dir.name) / "my_dict.tsv"
        custom_file.write_text("言墨前沿科技\tyanmoqianqiankeji\t9999\n国产自研系统\n", encoding="utf-8")

        imported = user_dict.import_from_file(custom_file)
        self.assertEqual(imported, 2)

        user_tsv = Path(temp_dir.name) / "user_dict.tsv"
        user_dict.sync_to_tsv(user_tsv)
        ok = self.engine.load_user_dict(str(user_tsv))
        self.assertTrue(ok)

        q1 = self._query("yanmoqianqiankeji")
        self.assertIn("言墨前沿科技", q1)

        q2 = self._query("guochanziyanxitong")
        self.assertIn("国产自研系统", q2)

        temp_dir.cleanup()

    def test_single_letter_initials_strictly_only_single_characters(self):
        """Single letter initial consonants (z, d, b, s...) must strictly only return single characters."""
        for init in ["z", "d", "b", "s", "m", "l"]:
            all_cands = self._query(init)
            self.assertTrue(bool(all_cands), f"{init} should have candidates")
            self.assertTrue(all(len(c) == 1 for c in all_cands), f"{init} must strictly only contain single characters")

    def test_dual_letter_initial_zh_prioritizes_single_characters(self):
        """zh prioritizes single characters, followed by multi-character words."""
        zh_cands = self._query("zh")
        # First 10 candidates should be single characters
        self.assertTrue(all(len(c) == 1 for c in zh_cands[:10]))
        # Followed by multi-character words
        self.assertTrue(any(len(c) > 1 for c in zh_cands))

    def test_tiered_consonant_abbreviation_hierarchy(self):
        """Abbreviation wzx hierarchy: 3-char words first (max 3 chars), then 2-char words, then 1-char words."""
        wzx_cands = self._query("wzx")
        three_chars = [c for c in wzx_cands if len(c) == 3]
        two_chars = [c for c in wzx_cands if len(c) == 2]
        single_chars = [c for c in wzx_cands if len(c) == 1]

        self.assertTrue(len(three_chars) > 0, "wzx should have 3-char words")
        self.assertTrue(len(two_chars) > 0, "wzx should fall back to 2-char words")
        self.assertTrue(len(single_chars) > 0, "wzx should fall back to single chars")

        first_3_idx = wzx_cands.index(three_chars[0])
        first_2_idx = wzx_cands.index(two_chars[0])
        first_1_idx = wzx_cands.index(single_chars[0])
        self.assertLess(first_3_idx, first_2_idx)
        self.assertLess(first_2_idx, first_1_idx)

        self.assertIn("我只想", three_chars)
        self.assertIn("文章", two_chars)
        self.assertIn("我", single_chars)

        # For 2-consonant abbreviation zg
        zg_cands = self._query("zg")
        zg_2 = [c for c in zg_cands if len(c) == 2]
        zg_1 = [c for c in zg_cands if len(c) == 1]
        self.assertTrue(len(zg_2) > 0)
        self.assertTrue(len(zg_1) > 0)
        self.assertLess(zg_cands.index(zg_2[0]), zg_cands.index(zg_1[0]))
        self.assertIn("中国", zg_2)
        self.assertIn("在", zg_1)

    def test_continuous_long_sentence_input(self):
        """Long continuous sentence input directly composes full sentence as Candidate #1."""
        test_sentences = [
            ("birushuozhejuhuakeyizhijieshuru", "比如说这句话可以直接输入"),
            ("wolaidaobeijingxuexi", "我来到北京学习"),
            ("zhongguorenmindaxue", "中国人民大学"),
            ("zenmeshuone", "怎么说呢"),
            ("zenmeshuon", "怎么说呢"),
        ]
        for pystr, expected in test_sentences:
            cands = self._query(pystr)
            self.assertTrue(bool(cands))
            self.assertEqual(cands[0], expected)

    def test_auxiliary_filtering_he_er_and_he_p(self):
        """Test auxiliary filtering with Tab for radical (er) and stroke (p) pinpointing 郃."""
        # 1. he + Tab + er -> radical 阝 -> 郃
        self.engine.reset()
        for ch in "he": self.engine.feed_key(ch)
        self.engine.feed_key("Tab")
        for ch in "er": self.engine.feed_key(ch)
        status = self.engine.get_status()
        self.assertEqual(status["mode"], "RADICAL")
        self.assertIn("阝部", status["radical_hint"])
        cands = self.engine.get_row_candidates(0)
        self.assertIn("郃", cands)

        # 2. he + Tab + p -> stroke order 撇 -> 郃, 和, 合 (not 河, 荷)
        self.engine.reset()
        for ch in "he": self.engine.feed_key(ch)
        self.engine.feed_key("Tab")
        self.engine.feed_key("p")
        status = self.engine.get_status()
        self.assertEqual(status["mode"], "RADICAL")
        self.assertIn("撇", status["radical_hint"])
        all_cands_p = []
        for r in range(4):
            all_cands_p.extend(self.engine.get_row_candidates(r))
        self.assertIn("郃", all_cands_p)
        self.assertNotIn("河", all_cands_p) # 河 starts with 点 d
        self.assertNotIn("荷", all_cands_p) # 荷 starts with 横 h

    def test_page_flip_with_square_brackets(self):
        """Square brackets [ and ] flip candidate pages up and down."""
        self.engine.reset()
        for ch in "ni": self.engine.feed_key(ch)
        self.assertEqual(self.engine.get_status()["page_offset"], 0)
        self.engine.feed_key("]")
        self.assertEqual(self.engine.get_status()["page_offset"], 1)
        self.engine.feed_key("]")
        self.assertEqual(self.engine.get_status()["page_offset"], 2)
        self.engine.feed_key("[")
        self.assertEqual(self.engine.get_status()["page_offset"], 1)
        self.engine.feed_key("[")
        self.assertEqual(self.engine.get_status()["page_offset"], 0)


    def test_full_abbrev_hybrid_input(self):
        """Test seamless full-abbrev hybrid input at arbitrary positions."""
        test_cases = [
            ("shuosmn", "说什么呢"),
            ("zgguoji", "中国国际"),
            ("nshuosm", "你说什么"),
            ("beijingdx", "北京大学"),
        ]
        for pystr, expected in test_cases:
            cands = self._query(pystr)
            self.assertTrue(bool(cands), f"Input '{pystr}' should yield candidates")
            self.assertIn(expected, cands[:3], f"'{expected}' should be in top candidates for '{pystr}'")

    def test_keyboard_typo_correction(self):
        """Test physical keyboard typo correction and stutter deduplication."""
        # 1. Transposition / adjacent typo: tain -> 天
        tain_cands = self._query("tain")
        self.assertTrue(bool(tain_cands))
        self.assertTrue(any(c in ["天", "田", "填"] for c in tain_cands[:5]),
                        f"Candidates for 'tain' should contain '天'/'田'/'填', got {tain_cands[:5]}")

        # 2. Stutter deduplication: nnihao -> 你好
        nnihao_cands = self._query("nnihao")
        self.assertTrue(bool(nnihao_cands))
        self.assertIn("你好", nnihao_cands[:5],
                      f"Candidates for 'nnihao' should contain '你好', got {nnihao_cands[:5]}")

    def test_p0_1_mang_syllable_and_ranking(self):
        """P0-1: mang syllable ranking and abbrev indexing."""
        for query, expected in [('manglu', '忙碌'), ('bangmang', '帮忙'), ('mangzhe', '忙着'), ('womang', '我忙')]:
            cands = self._query(query)
            self.assertIn(expected, cands[:2], f"{expected} should be in top 2 for {query}")

        ml_cands = self.engine.get_all_candidates(50)
        ml_cands = self._query("ml")
        self.assertIn("忙碌", ml_cands, "忙碌 should be reachable via 'ml'")

        lm_cands = self._query("lm")
        self.assertIn("流氓", lm_cands, "流氓 should be reachable via 'lm'")

    def test_p0_3_corrupted_tsv_tolerance(self):
        """P0-3: Corrupted TSV with half-line does not crash engine."""
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as f:
            f.write("你好\t世界\t1000\n今天\t\n测试\t数据\tinvalid\n")
            temp_tsv = f.name
        try:
            ok = self.engine.lib.yanmo_load_bigram(self.engine._handle, temp_tsv.encode("utf-8"))
            self.assertEqual(ok, 1)
        finally:
            Path(temp_tsv).unlink(missing_ok=True)

    def test_p0_4_radical_multibyte_utf8_backspace(self):
        """P0-4: Backspace on multi-byte radical glyphs preserves valid UTF-8."""
        self.engine.reset()
        self.engine.feed_key("Tab")
        self.engine.apply_visual_radical_filter("氵")
        self.assertEqual(self.engine.get_radical_buffer(), "氵")
        self.engine.feed_key("Backspace")
        self.assertEqual(self.engine.get_radical_buffer(), "")

    def test_p0_5_json_escaping_and_buffer_expansion(self):
        """P0-5: Candidate word with quotes, backslashes, emoji escapes correctly."""
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as f:
            f.write('特殊"词\\条🎉\tteshucitiao\t\t50000\n')
            temp_dict = f.name
        try:
            self.engine.load_user_dict(temp_dict)
            cands = self._query("teshucitiao")
            self.assertIn('特殊"词\\条🎉', cands)
            de_cands = self._query("de")
            self.assertGreater(len(de_cands), 10)
        finally:
            Path(temp_dict).unlink(missing_ok=True)

    def test_p0_6_out_of_bounds_digit_key_not_committed(self):
        """P0-6: Pressing digit beyond row candidate count does not commit raw pinyin."""
        self.engine.reset()
        for ch in "bangmang":
            self.engine.feed_key(ch)
        row_cands = self.engine.get_row_candidates(0)
        self.assertLess(len(row_cands), 5)

        consumed = self.engine.feed_key("5")
        status = self.engine.get_status()
        self.assertFalse(consumed)
        self.assertEqual(status["committed_text"], "")
        self.assertEqual(status["pinyin_buffer"], "bangmang")

    def test_p0_7_idle_radical_filter_click(self):
        """P0-7: Direct click on radical filter in IDLE converges candidates."""
        self.engine.reset()
        self.assertEqual(self.engine.get_status()["mode"], "IDLE")
        self.engine.apply_visual_radical_filter("氵")
        status = self.engine.get_status()
        self.assertEqual(status["mode"], "RADICAL")
        self.assertEqual(status["radical_buffer"], "氵")
        cands = self.engine.get_all_candidates(100)
        for expected in ["河", "海", "湖", "江", "汉"]:
            self.assertIn(expected, cands)


if __name__ == "__main__":
    unittest.main()



