"""
YanMo IME (言墨输入法) Core Engine.
Coordinates input state machine, pinyin matcher, and radical filtering.
Integrates user dictionary self-learning and standalone radical lookup.
"""

from pathlib import Path
from typing import List, Optional
from .models import Candidate, EngineState, InputMode
from .pinyin_matcher import PinyinMatcher
from .radical_matcher import RadicalMatcher
from .voice_engine import VoiceEngine


class YanMoEngine:
    def __init__(self, data_dir: Optional[Path] = None, user_db_path: Optional[Path] = None, voice_model_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path(__file__).resolve().parent.parent / "data"

        self.pinyin_matcher = PinyinMatcher(dict_dir=data_dir / "dict", user_db_path=user_db_path)
        self.radical_matcher = RadicalMatcher(data_dir=data_dir / "radicals")
        self.voice_engine = VoiceEngine(model_dir=voice_model_dir)
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
            if self.state.mode != InputMode.IDLE or self.state.radical_buffer or self.state.pinyin_buffer:
                self.reset()
                return True
            return False

        # 2. TAB or ~ (Backtick): Toggle Radical Filter Mode
        if key in ("Tab", "`", "~"):
            if self.state.mode in (InputMode.COMPOSING, InputMode.IDLE):
                self.state.mode = InputMode.RADICAL_FILTER
                self._update_candidates()
                return True
            elif self.state.mode == InputMode.RADICAL_FILTER:
                if not self.state.radical_buffer:
                    self.state.mode = InputMode.COMPOSING if self.state.pinyin_buffer else InputMode.IDLE
                    self._update_candidates()
                return True
            return False

        # 3. BACKSPACE: Delete one character
        if key == "Backspace":
            if self.state.mode == InputMode.RADICAL_FILTER:
                if self.state.radical_buffer:
                    self.state.radical_buffer = self.state.radical_buffer[:-1]
                else:
                    self.state.mode = InputMode.COMPOSING if self.state.pinyin_buffer else InputMode.IDLE
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
                self.select_candidate(0)
                return True
            elif self.state.pinyin_buffer:
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
        """Commit selected candidate at index and learn into user dictionary."""
        if 0 <= index < len(self.state.candidates):
            selected = self.state.candidates[index]
            committed = selected.text
            current_pinyin = self.state.pinyin_buffer or selected.pinyin

            # Learn into user dictionary
            if current_pinyin:
                self.pinyin_matcher.record_selection(committed, current_pinyin)

            self.reset()
            self.state.committed_text = committed
            return committed
        return None

    def delete_candidate(self, index: int) -> bool:
        """Delete candidate from user self-learning dictionary."""
        if 0 <= index < len(self.state.candidates):
            target = self.state.candidates[index]
            deleted = self.pinyin_matcher.delete_word(target.text)
            self._update_candidates()
            return deleted
        return False

    def apply_visual_radical_filter(self, radical_glyph: str):
        """
        Used by UI corner button: User directly clicks or touches a radical (e.g. '氵' or '木').
        Works both with existing pinyin and standalone pure radical lookup.
        """
        self.state.mode = InputMode.RADICAL_FILTER
        self.state.radical_buffer = radical_glyph
        self._update_candidates()

    def start_voice_recording(self) -> bool:
        """Start microphone recording for offline voice recognition."""
        return self.voice_engine.start_recording()

    def stop_voice_recording(self) -> str:
        """Stop microphone recording, run SenseVoice inference, and return text."""
        text = self.voice_engine.stop_recording()
        if text:
            self.state.committed_text = text
        return text

    def _update_candidates(self):
        """Re-compute candidate list based on current pinyin and radical filters."""
        # Case 1: Standalone radical lookup (no pinyin entered)
        if not self.state.pinyin_buffer:
            if self.state.mode == InputMode.RADICAL_FILTER and self.state.radical_buffer:
                matched_chars = self.radical_matcher.get_characters_by_radical_query(self.state.radical_buffer)
                cands = []
                for ch in matched_chars:
                    meta = self.radical_matcher.char_to_info.get(ch, {})
                    cands.append(Candidate(
                        text=ch,
                        pinyin=meta.get("pinyin", ""),
                        freq=meta.get("freq", 1000),
                        radical=meta.get("radical"),
                        comment=self.radical_matcher.get_radical_hint(ch),
                        is_radical_matched=True
                    ))
                self.state.candidates = cands
            else:
                self.state.candidates = []
            return

        # Case 2: Pinyin entered (+ optional radical filter)
        base_candidates = self.pinyin_matcher.match(self.state.pinyin_buffer)

        enriched_candidates = []
        for c in base_candidates:
            comment = c.comment
            if not comment and len(c.text) == 1:
                comment = self.radical_matcher.get_radical_hint(c.text)

            cand_copy = Candidate(
                text=c.text,
                pinyin=c.pinyin,
                freq=c.freq,
                radical=c.radical,
                comment=comment
            )
            enriched_candidates.append(cand_copy)

        # If in radical filter mode and user typed a radical query
        if self.state.mode == InputMode.RADICAL_FILTER and self.state.radical_buffer:
            query = self.state.radical_buffer
            filtered = []
            for c in enriched_candidates:
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
