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

    def test_character_matching(self):
        # '河' belongs to '氵' (水部)
        self.assertTrue(self.matcher.match_character("河", "shui"))
        self.assertTrue(self.matcher.match_character("河", "氵"))
        self.assertFalse(self.matcher.match_character("河", "mu"))

        # '核' belongs to '木' (木部)
        self.assertTrue(self.matcher.match_character("核", "mu"))
        self.assertFalse(self.matcher.match_character("核", "shui"))

        # '荷' belongs to '艹' (草部)
        self.assertTrue(self.matcher.match_character("荷", "cao"))

    def test_component_assembly(self):
        # ['木', '木'] -> '林'
        self.assertEqual(self.matcher.assemble_components(["木", "木"]), "林")
        # ['木', '木', '木'] -> '森'
        self.assertEqual(self.matcher.assemble_components(["木", "木", "木"]), "森")
        # ['口', '口', '口'] -> '品'
        self.assertEqual(self.matcher.assemble_components(["口", "口", "口"]), "品")
        # ['日', '月'] -> '明'
        self.assertEqual(self.matcher.assemble_components(["日", "月"]), "明")


if __name__ == "__main__":
    unittest.main()
