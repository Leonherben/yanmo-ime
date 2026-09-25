"""
Radical and component matching engine for YanMo IME (言墨输入法).
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from .models import RadicalInfo


class RadicalMatcher:
    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path(__file__).resolve().parent.parent / "data" / "radicals"

        self.radicals_file = data_dir / "radicals.json"
        self.char_radicals_file = data_dir / "char_radicals.json"

        self.radicals: List[RadicalInfo] = []
        self.pinyin_to_radicals: Dict[str, List[RadicalInfo]] = {}
        self.variant_to_radical: Dict[str, RadicalInfo] = {}
        self.char_to_info: Dict[str, dict] = {}
        self.radical_to_chars: Dict[str, Set[str]] = {}
        self.components_to_char: Dict[tuple, str] = {}

        self.load_data()

    def load_data(self):
        # 1. Load radicals table
        if self.radicals_file.exists():
            with open(self.radicals_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    rad = RadicalInfo(**item)
                    self.radicals.append(rad)

                    # Map variant glyphs
                    for var in rad.variants:
                        self.variant_to_radical[var] = rad
                    self.variant_to_radical[rad.radical] = rad

                    # Map pinyin
                    for py in rad.pinyin:
                        if py not in self.pinyin_to_radicals:
                            self.pinyin_to_radicals[py] = []
                        self.pinyin_to_radicals[py].append(rad)

        # 2. Load character to radical & component mapping
        if self.char_radicals_file.exists():
            with open(self.char_radicals_file, "r", encoding="utf-8") as f:
                self.char_to_info = json.load(f)

                for char, meta in self.char_to_info.items():
                    rad_glyph = meta.get("radical")
                    if rad_glyph:
                        if rad_glyph not in self.radical_to_chars:
                            self.radical_to_chars[rad_glyph] = set()
                        self.radical_to_chars[rad_glyph].add(char)

                        # Also index under canonical radical
                        rad_info = self.variant_to_radical.get(rad_glyph)
                        if rad_info and rad_info.radical != rad_glyph:
                            if rad_info.radical not in self.radical_to_chars:
                                self.radical_to_chars[rad_info.radical] = set()
                            self.radical_to_chars[rad_info.radical].add(char)

                    # Map components for assembly (e.g. ('木', '木') -> '林')
                    components = tuple(sorted(meta.get("components", [])))
                    if len(components) >= 2:
                        self.components_to_char[components] = char

    def resolve_radical_query(self, query: str) -> List[RadicalInfo]:
        """
        Resolve user radical input (pinyin prefix or literal glyph) to matching radicals.
        e.g. 'shui' -> [水/氵], '氵' -> [水/氵], 'mu' -> [木]
        """
        query = query.strip().lower()
        if not query:
            return []

        # 1. Exact match by glyph (e.g. "氵", "水")
        if query in self.variant_to_radical:
            return [self.variant_to_radical[query]]

        # 2. Match by pinyin (exact or prefix)
        matches: List[RadicalInfo] = []
        seen = set()

        for py, rad_list in self.pinyin_to_radicals.items():
            if py.startswith(query):
                for rad in rad_list:
                    if rad.id not in seen:
                        seen.add(rad.id)
                        matches.append(rad)

        return matches

    def get_characters_by_radical_query(self, query: str) -> List[str]:
        """
        Get all characters matching a radical query directly.
        e.g. 'shui' or '氵' -> ['海', '河', '江', '湖', '波', ...]
        """
        query = query.strip().lower()
        if not query:
            return []

        rad_infos = self.resolve_radical_query(query)
        results = []
        seen = set()

        if rad_infos:
            for rad_info in rad_infos:
                all_glyphs = [rad_info.radical] + rad_info.variants
                for glyph in all_glyphs:
                    for ch in self.radical_to_chars.get(glyph, set()):
                        if ch not in seen:
                            seen.add(ch)
                            results.append(ch)
        else:
            # Fallback: check if query glyph appears in components directly
            for ch, meta in self.char_to_info.items():
                if query in meta.get("components", []):
                    if ch not in seen:
                        seen.add(ch)
                        results.append(ch)

        # Sort characters by frequency descending
        results.sort(key=lambda ch: self.char_to_info.get(ch, {}).get("freq", 1000), reverse=True)
        return results

    def match_character(self, char: str, query: str) -> bool:
        """
        Check if a single character matches the given radical query.
        """
        char_meta = self.char_to_info.get(char)
        if not char_meta:
            return False

        target_rads = self.resolve_radical_query(query)
        if not target_rads:
            # Fallback: check if query is in components directly
            return query in char_meta.get("components", [])

        char_rad_glyph = char_meta.get("radical")
        char_components = set(char_meta.get("components", []))

        for rad_info in target_rads:
            all_glyphs = set(rad_info.variants + [rad_info.radical])
            # Check primary radical
            if char_rad_glyph in all_glyphs:
                return True
            # Check components
            if all_glyphs & char_components:
                return True

        return False

    def get_radical_hint(self, char: str) -> Optional[str]:
        """
        Get display hint for a character's radical, e.g. '氵/水部'.
        """
        meta = self.char_to_info.get(char)
        if not meta:
            return None
        rad_glyph = meta.get("radical")
        if not rad_glyph:
            return None
        rad_info = self.variant_to_radical.get(rad_glyph)
        if rad_info:
            return f"{rad_glyph}/{rad_info.name}"
        return rad_glyph

    def assemble_components(self, components: List[str]) -> Optional[str]:
        """
        Assemble components into a character (e.g. ['木', '木'] -> '林').
        """
        key = tuple(sorted(components))
        return self.components_to_char.get(key)
