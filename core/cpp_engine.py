"""
Python ctypes wrapper for YanMo IME C++20 Core Engine.
Provides sub-millisecond candidate lookup and state management.
"""

import ctypes
import json
import logging
from pathlib import Path
from typing import List, Optional
from .voice_engine import VoiceEngine

logger = logging.getLogger(__name__)


class YanMoCppEngine:
    def __init__(self, lib_path: Optional[Path] = None, voice_model_dir: Optional[Path] = None):
        if lib_path is None:
            lib_path = Path(__file__).resolve().parent.parent / "cpp" / "lib" / "libyanmo_engine.so"

        if not lib_path.exists():
            raise FileNotFoundError(f"C++ shared library not found: {lib_path}. Please run 'make' in cpp/")

        self.lib = ctypes.CDLL(str(lib_path))
        self._bind_functions()

        self._handle = self.lib.yanmo_create()
        if not self._handle:
            raise RuntimeError("Failed to create C++ YanMoEngine instance")

        data_dir = Path(__file__).resolve().parent.parent / "data"
        lex_path = str(data_dir / "dict" / "core_lexicon.tsv").encode("utf-8")
        rad_path = str(data_dir / "radicals" / "radicals.tsv").encode("utf-8")

        ok = self.lib.yanmo_init(self._handle, lex_path, rad_path)
        if ok != 1:
            raise RuntimeError("Failed to initialize C++ YanMoEngine with TSV data")

        user_dict_file = Path.home() / ".local" / "share" / "yanmo" / "user_dict.tsv"
        if user_dict_file.exists():
            self.load_user_dict(str(user_dict_file))

        user_bigram_file = Path.home() / ".local" / "share" / "yanmo" / "user_bigram.tsv"
        if user_bigram_file.exists():
            self.load_bigram(str(user_bigram_file))

        self.voice_engine = VoiceEngine(model_dir=voice_model_dir)

    def _bind_functions(self):
        self.lib.yanmo_create.restype = ctypes.c_void_p
        self.lib.yanmo_destroy.argtypes = [ctypes.c_void_p]

        self.lib.yanmo_init.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
        self.lib.yanmo_init.restype = ctypes.c_int

        self.lib.yanmo_load_user_dict.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        self.lib.yanmo_load_user_dict.restype = ctypes.c_int

        self.lib.yanmo_load_bigram.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        self.lib.yanmo_load_bigram.restype = ctypes.c_int

        self.lib.yanmo_reset.argtypes = [ctypes.c_void_p]

        self.lib.yanmo_feed_key.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int
        ]
        self.lib.yanmo_feed_key.restype = ctypes.c_int

        self.lib.yanmo_get_buffer.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        self.lib.yanmo_get_buffer.restype = ctypes.c_int

        self.lib.yanmo_get_radical_hint.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        self.lib.yanmo_get_radical_hint.restype = ctypes.c_int

        self.lib.yanmo_get_radical_buffer.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        self.lib.yanmo_get_radical_buffer.restype = ctypes.c_int

        self.lib.yanmo_get_status.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
        ]
        self.lib.yanmo_get_status.restype = ctypes.c_int

        self.lib.yanmo_get_row_candidates_json.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int
        ]
        self.lib.yanmo_get_row_candidates_json.restype = ctypes.c_int

        self.lib.yanmo_get_candidates_json.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int
        ]
        self.lib.yanmo_get_candidates_json.restype = ctypes.c_int

        self.lib.yanmo_save_user_bigram.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        self.lib.yanmo_save_user_bigram.restype = ctypes.c_int

        self.lib.yanmo_select_candidate.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int
        ]
        self.lib.yanmo_select_candidate.restype = ctypes.c_int

        self.lib.yanmo_get_committed_text.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int
        ]
        self.lib.yanmo_get_committed_text.restype = ctypes.c_int

        self.lib.yanmo_clear_committed_text.argtypes = [ctypes.c_void_p]
        self.lib.yanmo_clear_committed_text.restype = None

        self.lib.yanmo_set_row_size.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.lib.yanmo_set_row_size.restype = ctypes.c_int

        self.lib.yanmo_set_full_width_punct.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.lib.yanmo_set_full_width_punct.restype = ctypes.c_int

        self.lib.yanmo_get_full_width_punct.argtypes = [ctypes.c_void_p]
        self.lib.yanmo_get_full_width_punct.restype = ctypes.c_int

        self.lib.yanmo_set_full_width_char.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.lib.yanmo_set_full_width_char.restype = ctypes.c_int

        self.lib.yanmo_get_full_width_char.argtypes = [ctypes.c_void_p]
        self.lib.yanmo_get_full_width_char.restype = ctypes.c_int

        self.lib.yanmo_enter_radical_mode.argtypes = [ctypes.c_void_p]
        self.lib.yanmo_enter_radical_mode.restype = ctypes.c_int

        self.lib.yanmo_set_radical_glyph.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        self.lib.yanmo_set_radical_glyph.restype = ctypes.c_int

        self.last_committed = ""

    def set_full_width_punct(self, enabled: bool) -> bool:
        if not self._handle:
            return False
        return self.lib.yanmo_set_full_width_punct(self._handle, 1 if enabled else 0) == 1

    def is_full_width_punct(self) -> bool:
        if not self._handle:
            return True
        return self.lib.yanmo_get_full_width_punct(self._handle) == 1

    def set_full_width_char(self, enabled: bool) -> bool:
        if not self._handle:
            return False
        return self.lib.yanmo_set_full_width_char(self._handle, 1 if enabled else 0) == 1

    def is_full_width_char(self) -> bool:
        if not self._handle:
            return False
        return self.lib.yanmo_get_full_width_char(self._handle) == 1

    def load_user_dict(self, path: str) -> bool:
        if not self._handle:
            return False
        return self.lib.yanmo_load_user_dict(self._handle, path.encode("utf-8")) == 1

    def load_bigram(self, path: str) -> bool:
        if not self._handle:
            return False
        return self.lib.yanmo_load_bigram(self._handle, path.encode("utf-8")) == 1

    def save_user_bigram(self, path: Optional[str] = None) -> bool:
        if not self._handle:
            return False
        if path is None:
            user_bigram_file = Path.home() / ".local" / "share" / "yanmo" / "user_bigram.tsv"
            user_bigram_file.parent.mkdir(parents=True, exist_ok=True)
            path = str(user_bigram_file)
        return self.lib.yanmo_save_user_bigram(self._handle, path.encode("utf-8")) == 1

    def set_candidate_count(self, count: int) -> bool:
        if count < 3 or count > 10:
            return False
        return self.lib.yanmo_set_row_size(self._handle, count) == 1

    def __del__(self):
        if hasattr(self, "_handle") and self._handle:
            self.lib.yanmo_destroy(self._handle)
            self._handle = None

    def reset(self):
        self.last_committed = ""
        self.lib.yanmo_reset(self._handle)

    def feed_key(self, key: str, is_shift: bool = False) -> bool:
        key_bytes = key.encode("utf-8")
        out_buf = ctypes.create_string_buffer(512)
        consumed = self.lib.yanmo_feed_key(self._handle, key_bytes, 1 if is_shift else 0, out_buf, 512)
        committed = out_buf.value.decode("utf-8")
        self.last_committed = committed
        return consumed == 1

    def select_candidate(self, index: int) -> str:
        out_buf = ctypes.create_string_buffer(512)
        ok = self.lib.yanmo_select_candidate(self._handle, index, out_buf, 512)
        committed = out_buf.value.decode("utf-8") if ok == 1 else ""
        self.last_committed = committed
        return committed

    def get_committed_text(self) -> str:
        committed = self.last_committed
        self.last_committed = ""
        return committed

    def clear_committed_text(self):
        self.last_committed = ""
        if self._handle:
            self.lib.yanmo_clear_committed_text(self._handle)

    def get_buffer(self) -> str:
        buf = ctypes.create_string_buffer(256)
        self.lib.yanmo_get_buffer(self._handle, buf, 256)
        return buf.value.decode("utf-8")

    def get_radical_hint(self) -> str:
        buf = ctypes.create_string_buffer(256)
        self.lib.yanmo_get_radical_hint(self._handle, buf, 256)
        return buf.value.decode("utf-8", errors="replace")

    def get_radical_buffer(self) -> str:
        buf = ctypes.create_string_buffer(256)
        self.lib.yanmo_get_radical_buffer(self._handle, buf, 256)
        return buf.value.decode("utf-8", errors="replace")

    def enter_radical_mode(self) -> bool:
        if not self._handle:
            return False
        return self.lib.yanmo_enter_radical_mode(self._handle) == 1

    def set_radical_glyph(self, glyph: str) -> bool:
        if not self._handle:
            return False
        return self.lib.yanmo_set_radical_glyph(self._handle, glyph.encode("utf-8")) == 1

    def apply_visual_radical_filter(self, radical_glyph: str):
        """Apply visual radical filter directly (e.g. '氵' or '木')."""
        self.set_radical_glyph(radical_glyph)

    def get_status(self) -> dict:
        mode = ctypes.c_int()
        total_cands = ctypes.c_int()
        page_offset = ctypes.c_int()
        active_row = ctypes.c_int()
        is_expanded = ctypes.c_int()

        self.lib.yanmo_get_status(
            self._handle,
            ctypes.byref(mode),
            ctypes.byref(total_cands),
            ctypes.byref(page_offset),
            ctypes.byref(active_row),
            ctypes.byref(is_expanded),
        )

        modes = ["IDLE", "COMPOSING", "RADICAL"]
        mode_idx = mode.value if 0 <= mode.value < len(modes) else 0

        return {
            "mode": modes[mode_idx],
            "total_candidates": total_cands.value,
            "page_offset": page_offset.value,
            "active_row": active_row.value,
            "is_expanded": bool(is_expanded.value),
            "pinyin_buffer": self.get_buffer(),
            "radical_buffer": self.get_radical_buffer(),
            "radical_hint": self.get_radical_hint(),
            "committed_text": self.last_committed,
        }

    def get_row_candidates(self, row_idx: int) -> List[str]:
        buf_size = 2048
        buf = ctypes.create_string_buffer(buf_size)
        res = self.lib.yanmo_get_row_candidates_json(self._handle, row_idx, buf, buf_size)
        if res < 0:
            buf_size = -res
            buf = ctypes.create_string_buffer(buf_size)
            res = self.lib.yanmo_get_row_candidates_json(self._handle, row_idx, buf, buf_size)
        if res <= 0:
            return []
        raw_json = buf.value.decode("utf-8")
        if not raw_json:
            return []
        try:
            return json.loads(raw_json)
        except Exception as e:
            logger.error(f"[YanMoCppEngine] Failed to parse row candidates JSON: {e}, raw: {raw_json!r}")
            return []

    def get_all_candidates(self, max_cands: int = 50) -> List[str]:
        buf_size = 4096
        buf = ctypes.create_string_buffer(buf_size)
        res = self.lib.yanmo_get_candidates_json(self._handle, max_cands, buf, buf_size)
        if res < 0:
            buf_size = -res
            buf = ctypes.create_string_buffer(buf_size)
            res = self.lib.yanmo_get_candidates_json(self._handle, max_cands, buf, buf_size)
        if res <= 0:
            return []
        raw_json = buf.value.decode("utf-8")
        if not raw_json:
            return []
        try:
            return json.loads(raw_json)
        except Exception as e:
            logger.error(f"[YanMoCppEngine] Failed to parse all candidates JSON: {e}, raw: {raw_json!r}")
            return []

    def start_voice_recording(self) -> bool:
        if self.voice_engine:
            return self.voice_engine.start_recording()
        return False

    def stop_voice_recording(self) -> str:
        if self.voice_engine:
            return self.voice_engine.stop_recording()
        return ""

