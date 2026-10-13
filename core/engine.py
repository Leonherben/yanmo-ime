"""
YanMo IME (言墨输入法) Core Engine.
Unified Python interface backed by the C++20 Core Engine (YanMoCppEngine).
Acts as the single source of truth complying with AI Development Guidelines.
"""

from pathlib import Path
from typing import List, Optional, Set
from .models import Candidate, EngineState, InputMode
from .cpp_engine import YanMoCppEngine
from .user_dict import UserDictionary
from .voice_engine import VoiceEngine


class _PinyinMatcherCompat:
    """Compatibility adapter for legacy pinyin_matcher property."""

    def __init__(self, cpp_engine: YanMoCppEngine, user_db_path: Optional[Path] = None):
        self._cpp = cpp_engine
        self.user_dict = UserDictionary(db_path=user_db_path)

    def record_selection(self, word: str, pinyin: str):
        self.user_dict.record_selection(word, pinyin)

    def delete_word(self, word: str) -> bool:
        return self.user_dict.delete_word(word)

    def count(self) -> int:
        return self.user_dict.count()


class YanMoEngine:
    """
    YanMo IME Core Engine.
    Powered by YanMoCppEngine (C++20 shared library).
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        user_db_path: Optional[Path] = None,
        voice_model_dir: Optional[Path] = None,
    ):
        self._cpp = YanMoCppEngine(voice_model_dir=voice_model_dir)
        self.pinyin_matcher = _PinyinMatcherCompat(self._cpp, user_db_path=user_db_path)
        self.voice_engine = self._cpp.voice_engine
        self._user_learned: Set[str] = set()
        self.state = EngineState()
        self._sync_state()

    def reset(self):
        """Reset engine state to idle."""
        self._cpp.reset()
        self._sync_state()

    def feed_key(self, key: str) -> bool:
        """Process key input event."""
        # Convert ~ and ` to Tab for radical toggle
        if key in ("`", "~"):
            key = "Tab"

        consumed = self._cpp.feed_key(key)
        self._sync_state()
        return consumed

    def select_candidate(self, index: int) -> Optional[str]:
        """Commit selected candidate at index and learn into user dictionary."""
        status = self._cpp.get_status()
        py = status.get("pinyin_buffer", "")
        committed = self._cpp.select_candidate(index)
        if committed:
            if py:
                self._user_learned.add(committed)
                self.pinyin_matcher.record_selection(committed, py)
            self._sync_state()
            self.state.committed_text = committed
            return committed
        self._sync_state()
        return None

    def delete_candidate(self, index: int) -> bool:
        """Delete candidate from user dictionary."""
        if 0 <= index < len(self.state.candidates):
            target = self.state.candidates[index].text
            self._user_learned.discard(target)
            deleted = self.pinyin_matcher.delete_word(target)
            self._sync_state()
            return deleted
        return False

    def apply_visual_radical_filter(self, radical_glyph: str):
        """Used by UI corner button: User directly clicks or touches a radical."""
        self._cpp.apply_visual_radical_filter(radical_glyph)
        self._sync_state()

    def set_full_width_punct(self, enabled: bool) -> bool:
        return self._cpp.set_full_width_punct(enabled)

    def is_full_width_punct(self) -> bool:
        return self._cpp.is_full_width_punct()

    def set_full_width_char(self, enabled: bool) -> bool:
        return self._cpp.set_full_width_char(enabled)

    def is_full_width_char(self) -> bool:
        return self._cpp.is_full_width_char()

    def clear_committed_text(self):
        self._cpp.clear_committed_text()
        self.state.committed_text = ""

    def start_voice_recording(self) -> bool:
        """Start microphone recording for offline voice recognition."""
        return self._cpp.start_voice_recording()

    def stop_voice_recording(self) -> str:
        """Stop microphone recording, run SenseVoice inference, and return text."""
        text = self._cpp.stop_voice_recording()
        if text:
            self.state.committed_text = text
        return text

    def _sync_state(self):
        """Synchronize Python EngineState from C++ engine status."""
        status = self._cpp.get_status()
        raw_mode = status.get("mode", "IDLE")
        if raw_mode == "COMPOSING":
            self.state.mode = InputMode.COMPOSING
        elif raw_mode == "RADICAL":
            self.state.mode = InputMode.RADICAL_FILTER
        else:
            self.state.mode = InputMode.IDLE

        self.state.pinyin_buffer = status.get("pinyin_buffer", "")
        self.state.radical_buffer = self._cpp.get_radical_buffer()
        committed = status.get("committed_text", "")
        if committed:
            self.state.committed_text = committed
            self._user_learned.add(committed)

        total = status.get("total_candidates", 0)
        cands: List[Candidate] = []
        if total > 0:
            words = self._cpp.get_all_candidates(max_cands=100)
            hint = status.get("radical_hint", "")
            for i, w in enumerate(words):
                comment = None
                if w in self._user_learned:
                    comment = "自学词"
                elif hint and self.state.mode == InputMode.RADICAL_FILTER:
                    comment = hint

                cands.append(
                    Candidate(
                        text=w,
                        pinyin=self.state.pinyin_buffer,
                        freq=1000 - i * 10,
                        comment=comment,
                        is_radical_matched=(self.state.mode == InputMode.RADICAL_FILTER),
                    )
                )
        self.state.candidates = cands

    def get_status(self) -> dict:
        status = self._cpp.get_status()
        if self.state.committed_text:
            status["committed_text"] = self.state.committed_text
        return status

    def get_buffer(self) -> str:
        return self._cpp.get_buffer()

    def get_row_candidates(self, row_idx: int) -> List[str]:
        return self._cpp.get_row_candidates(row_idx)
