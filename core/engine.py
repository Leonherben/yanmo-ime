"""
YanMo IME (言墨输入法) Core Engine.
Coordinates input state machine, pinyin matcher, and radical filtering.
"""

from pathlib import Path
from typing import List, Optional
from .models import Candidate, EngineState, InputMode
from .pinyin_matcher import PinyinMatcher
from .radical_matcher import RadicalMatcher


class YanMoEngine:
    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path(__file__).resolve().parent.parent / "data"

        self.pinyin_matcher = PinyinMatcher(dict_dir=data_dir / "dict")
        self.radical_matcher = RadicalMatcher(data_dir=data_dir / "radicals")
        self.state = EngineState()

    def reset(self):
        """Reset engine state to idle."""
        self.state.mode = InputMode.IDLE
        self.state.pinyin_buffer = ""
        self.state.radical_buffer = ""
        self.state.candidates = []
        self.state.selected_index = 0
        self.state.committed_text = ""

    def feed_key(self, key: str) -> bool:
        """
        Process a single key input event.
        Returns True if the key was consumed by the engine, False otherwise.
        """
        self.state.committed_text = ""

        # 1. ESC: Cancel everything
        if key == "Escape":
            if self.state.mode != InputMode.IDLE:
                self.reset()
                return True
            return False

        # 2. TAB or ~ (Backtick): Toggle Radical Filter Mode
        if key in ("Tab", "`", "~"):
            if self.state.mode == InputMode.COMPOSING:
                self.state.mode = InputMode.RADICAL_FILTER
                self._update_candidates()
                return True
            elif self.state.mode == InputMode.RADICAL_FILTER:
                # Cycle or toggle back if empty
                if not self.state.radical_buffer:
                    self.state.mode = InputMode.COMPOSING
                    self._update_candidates()
                return True
            return False

        # 3. BACKSPACE: Delete one character
        if key == "Backspace":
            if self.state.mode == InputMode.RADICAL_FILTER:
                if self.state.radical_buffer:
                    self.state.radical_buffer = self.state.radical_buffer[:-1]
                else:
                    # Radical buffer empty, switch back to pinyin
                    self.state.mode = InputMode.COMPOSING
                self._update_candidates()
                return True
            elif self.state.mode == InputMode.COMPOSING:
                if self.state.pinyin_buffer:
                    self.state.pinyin_buffer = self.state.pinyin_buffer[:-1]
                    if not self.state.pinyin_buffer:
                        self.state.mode = InputMode.IDLE
                        self.state.candidates = []
                    else:
                        self._update_candidates()
                    return True
            return False

        # 4. SPACE or ENTER: Commit candidate
        if key in (" ", "Space"):
            if self.state.candidates:
                # Select first candidate
                self.select_candidate(0)
                return True
            elif self.state.pinyin_buffer:
                # Direct commit raw pinyin
                self.state.committed_text = self.state.pinyin_buffer
                self.reset()
                return True
            return False

        # 5. NUMBER KEYS (1-9): Select candidate
        if key.isdigit() and key != "0":
            idx = int(key) - 1
            if idx < len(self.state.candidates):
                self.select_candidate(idx)
                return True
            return False

        # 6. REGULAR ALPHABET (a-z)
        if len(key) == 1 and key.isalpha():
            char = key.lower()
            if self.state.mode == InputMode.IDLE:
                self.state.mode = InputMode.COMPOSING
                self.state.pinyin_buffer = char
            elif self.state.mode == InputMode.COMPOSING:
                self.state.pinyin_buffer += char
            elif self.state.mode == InputMode.RADICAL_FILTER:
                self.state.radical_buffer += char

            self._update_candidates()
            return True

        return False

    def select_candidate(self, index: int) -> Optional[str]:
        """Commit selected candidate at index."""
        if 0 <= index < len(self.state.candidates):
            selected = self.state.candidates[index]
            committed = selected.text
            self.reset()
            self.state.committed_text = committed
            return committed
        return None

    def apply_visual_radical_filter(self, radical_glyph: str):
        """
        Used by UI corner button: User directly clicks or touches a radical (e.g. '氵' or '木').
        """
        if self.state.mode in (InputMode.COMPOSING, InputMode.RADICAL_FILTER):
            self.state.mode = InputMode.RADICAL_FILTER
            self.state.radical_buffer = radical_glyph
            self._update_candidates()

    def _update_candidates(self):
        """Re-compute candidate list based on current pinyin and radical filters."""
        if not self.state.pinyin_buffer:
            self.state.candidates = []
            return

        base_candidates = self.pinyin_matcher.match(self.state.pinyin_buffer)

        # Populate radical display hints for all single characters
        enriched_candidates = []
        for c in base_candidates:
            cand_copy = Candidate(
                text=c.text,
                pinyin=c.pinyin,
                freq=c.freq,
                radical=c.radical,
                comment=self.radical_matcher.get_radical_hint(c.text) if len(c.text) == 1 else None
            )
            enriched_candidates.append(cand_copy)

        # If in radical filter mode and user typed a radical query
        if self.state.mode == InputMode.RADICAL_FILTER and self.state.radical_buffer:
            query = self.state.radical_buffer
            filtered = []
            for c in enriched_candidates:
                # Multi-character words: check if any character in the word matches
                if len(c.text) > 1:
                    matched = any(self.radical_matcher.match_character(ch, query) for ch in c.text)
                else:
                    matched = self.radical_matcher.match_character(c.text, query)

                if matched:
                    c.is_radical_matched = True
                    filtered.append(c)

            self.state.candidates = filtered
        else:
            self.state.candidates = enriched_candidates
