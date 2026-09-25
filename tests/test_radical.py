import unittest
from core.radical_matcher import RadicalMatcher


class TestRadicalMatcher(unittest.TestCase):
    def setUp(self):
        self.matcher = RadicalMatcher()

    def test_radical_resolution(self):
        # By pinyin
        shui_rads = self.matcher.resolve_radical_query("shui")
        self.assertTrue(len(shui_rads) > 0)
        self.assertEqual(shui_rads[0].radical, "水")

        # By variant glyph
        sandian_rads = self.matcher.resolve_radical_query("氵")
        self.assertTrue(len(sandian_rads) > 0)
        self.assertEqual(sandian_rads[0].radical, "水")

        # By 5 basic strokes: 'd' (点) must resolve radicals starting with 点, including 水/氵
        d_rads = self.matcher.resolve_radical_query("d")
        d_glyphs = [r.radical for r in d_rads]
        self.assertIn("水", d_glyphs)
        self.assertIn("广", d_glyphs)

    def test_character_matching_by_pinyin_and_strokes(self):
        # '河' belongs to '氵' (水部), starts with 'd' (点)
        self.assertTrue(self.matcher.match_character("河", "shui"))
        self.assertTrue(self.matcher.match_character("河", "氵"))
        self.assertTrue(self.matcher.match_character("河", "d"))  # 'd' for 点
        self.assertFalse(self.matcher.match_character("河", "p"))  # Not 撇

        # '核' belongs to '木' (木部), starts with 'h' (横)
        self.assertTrue(self.matcher.match_character("核", "mu"))
        self.assertTrue(self.matcher.match_character("核", "h"))  # 'h' for 横
        self.assertFalse(self.matcher.match_character("核", "d"))

        # '何' belongs to '亻' (人部), starts with 'p' (撇)
        self.assertTrue(self.matcher.match_character("何", "ren"))
        self.assertTrue(self.matcher.match_character("何", "p"))  # 'p' for 撇

    def test_component_assembly(self):
        self.assertEqual(self.matcher.assemble_components(["木", "木"]), "林")
        self.assertEqual(self.matcher.assemble_components(["木", "木", "木"]), "森")
        self.assertEqual(self.matcher.assemble_components(["口", "口", "口"]), "品")
        self.assertEqual(self.matcher.assemble_components(["日", "月"]), "明")


if __name__ == "__main__":
    unittest.main()
