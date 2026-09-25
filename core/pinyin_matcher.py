"""
Pinyin and lexicon matching engine for YanMo IME (言墨输入法).
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from .models import Candidate


class PinyinMatcher:
    def __init__(self, dict_dir: Optional[Path] = None):
        if dict_dir is None:
            dict_dir = Path(__file__).resolve().parent.parent / "data" / "dict"

        self.lexicon_file = dict_dir / "core_lexicon.json"
        self.exact_pinyin_map: Dict[str, List[Candidate]] = {}
        self.prefix_pinyin_map: Dict[str, List[Candidate]] = {}

        self.load_data()

    def load_data(self):
        if not self.lexicon_file.exists():
            return

        with open(self.lexicon_file, "r", encoding="utf-8") as f:
            entries = json.load(f)

        for item in entries:
            cand = Candidate(
                text=item["word"],
                pinyin=item["pinyin"],
                freq=item.get("freq", 1000),
                radical=item.get("radical")
            )
            py = cand.pinyin.lower()

            if py not in self.exact_pinyin_map:
                self.exact_pinyin_map[py] = []
            self.exact_pinyin_map[py].append(cand)

        # Sort all lists by frequency descending
        for py, cands in self.exact_pinyin_map.items():
            cands.sort(key=lambda c: c.freq, reverse=True)

    def match(self, pinyin: str, prefix_limit: int = 15) -> List[Candidate]:
        """
        Find candidates by pinyin: exact matches first, then prefix matches.
        """
        pinyin = pinyin.strip().lower()
        if not pinyin:
            return []

        results: List[Candidate] = []
        seen = set()

        # 1. Exact matches
        if pinyin in self.exact_pinyin_map:
            for c in self.exact_pinyin_map[pinyin]:
                if c.text not in seen:
                    seen.add(c.text)
                    results.append(c)

        # 2. Prefix matches (for fuzzy / incomplete pinyin)
        prefix_matches = []
        for py, cands in self.exact_pinyin_map.items():
            if py != pinyin and py.startswith(pinyin):
                for c in cands:
                    if c.text not in seen:
                        prefix_matches.append(c)

        prefix_matches.sort(key=lambda c: c.freq, reverse=True)
        results.extend(prefix_matches[:prefix_limit])

        return results
