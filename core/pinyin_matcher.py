"""
Pinyin and lexicon matching engine for YanMo IME (言墨输入法).
Integrates High-Performance Pinyin Trie and SQLite User Dynamic Dictionary.
"""

import json
from pathlib import Path
from typing import List, Optional
from .models import Candidate
from .trie import PinyinTrie
from .user_dict import UserDictionary


class PinyinMatcher:
    def __init__(self, dict_dir: Optional[Path] = None, user_db_path: Optional[Path] = None):
        if dict_dir is None:
            dict_dir = Path(__file__).resolve().parent.parent / "data" / "dict"

        self.dict_dir = Path(dict_dir)
        self.lexicon_file = self.dict_dir / "core_lexicon.json"

        self.trie = PinyinTrie()
        self.user_dict = UserDictionary(db_path=user_db_path)

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
            self.trie.insert(cand.pinyin, cand)

    def match(self, pinyin: str, prefix_limit: int = 20) -> List[Candidate]:
        """
        Two-tier matching:
        1. User self-learning words (top priority)
        2. System Trie exact matches + prefix matches
        """
        pinyin = pinyin.strip().lower()
        if not pinyin:
            return []

        results: List[Candidate] = []
        seen = set()

        # Tier 1: User dictionary (Exact matches first, then prefix)
        user_cands = self.user_dict.get_candidates(pinyin, prefix=False)
        for c in user_cands:
            if c.text not in seen:
                seen.add(c.text)
                results.append(c)

        # Tier 2: System Trie exact matches
        sys_exact = self.trie.search_exact(pinyin)
        sys_exact.sort(key=lambda c: c.freq, reverse=True)
        for c in sys_exact:
            if c.text not in seen:
                seen.add(c.text)
                results.append(c)

        # Tier 3: User prefix matches + System prefix matches
        user_prefix = self.user_dict.get_candidates(pinyin, prefix=True, limit=5)
        for c in user_prefix:
            if c.text not in seen:
                seen.add(c.text)
                results.append(c)

        sys_prefix = self.trie.search_prefix(pinyin, limit=prefix_limit)
        for c in sys_prefix:
            if c.text not in seen:
                seen.add(c.text)
                results.append(c)

        return results

    def record_selection(self, word: str, pinyin: str):
        """Record candidate selection into user dictionary."""
        self.user_dict.record_selection(word, pinyin)

    def delete_word(self, word: str) -> bool:
        """Delete word from user dictionary."""
        return self.user_dict.delete_word(word)
