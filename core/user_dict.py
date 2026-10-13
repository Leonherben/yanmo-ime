"""
SQLite-backed User Self-Learning Dictionary for YanMo IME (言墨输入法).
Handles dynamic frequency learning, user custom words, and text export/import.
"""

import sqlite3
import time
from pathlib import Path
from typing import List, Optional
from .models import Candidate


class UserDictionary:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            data_home = Path.home() / ".local" / "share" / "yanmo"
            data_home.mkdir(parents=True, exist_ok=True)
            db_path = data_home / "user.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_lexicon (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL UNIQUE,
                    pinyin TEXT NOT NULL,
                    freq INTEGER NOT NULL DEFAULT 1,
                    last_used REAL NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pinyin ON user_lexicon(pinyin)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_freq ON user_lexicon(freq DESC)")
            conn.commit()

    def apply_decay(self, decay_factor: float = 0.95, min_freq: int = 1):
        """
        Apply time decay to user word frequencies.
        Multiplies all frequencies by decay_factor and deletes words that fall below min_freq.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE user_lexicon SET freq = MAX(1, CAST(freq * ? AS INTEGER))", (decay_factor,))
            if min_freq > 1:
                cursor.execute("DELETE FROM user_lexicon WHERE freq < ?", (min_freq,))
            conn.commit()

    def cleanup_overflow(self, max_entries: int = 10000):
        """
        Enforce maximum dictionary size to avoid unbounded memory / DB growth.
        Removes lowest frequency and oldest words if count exceeds max_entries.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM user_lexicon")
            row = cursor.fetchone()
            if row and row["cnt"] > max_entries:
                overflow = row["cnt"] - max_entries
                cursor.execute(
                    """
                    DELETE FROM user_lexicon WHERE id IN (
                        SELECT id FROM user_lexicon ORDER BY freq ASC, last_used ASC LIMIT ?
                    )
                    """,
                    (overflow,)
                )
                conn.commit()

    def record_selection(self, word: str, pinyin: str, initial_boost: int = 1):
        """
        Record a user-selected word. If it already exists, increment frequency and update timestamp.
        If it's new, insert with initial frequency.
        """
        word = word.strip()
        pinyin = pinyin.strip().lower()
        if not word or not pinyin:
            return

        # Do NOT record if word contains no Chinese/CJK characters
        if not any('\u4e00' <= ch <= '\u9fff' for ch in word):
            return

        # Do NOT record if word is identical to pinyin
        if word.lower() == pinyin:
            return

        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, freq FROM user_lexicon WHERE word = ?", (word,))
            row = cursor.fetchone()
            if row:
                new_freq = row["freq"] + 1
                cursor.execute(
                    "UPDATE user_lexicon SET freq = ?, last_used = ? WHERE id = ?",
                    (new_freq, now, row["id"])
                )
            else:
                cursor.execute(
                    "INSERT INTO user_lexicon (word, pinyin, freq, last_used, created_at) VALUES (?, ?, ?, ?, ?)",
                    (word, pinyin, initial_boost, now, now)
                )
            conn.commit()
        self.cleanup_overflow()

    def get_candidates(self, pinyin: str, prefix: bool = False, limit: int = 15) -> List[Candidate]:
        """
        Query user words matching pinyin.
        User words get a high frequency boost (+50000) so they comfortably appear ahead of generic system words.
        """
        pinyin = pinyin.lower().strip()
        if not pinyin:
            return []

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if prefix:
                cursor.execute(
                    """
                    SELECT word, pinyin, freq FROM user_lexicon 
                    WHERE pinyin LIKE ? 
                    ORDER BY freq DESC, last_used DESC LIMIT ?
                    """,
                    (f"{pinyin}%", limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT word, pinyin, freq FROM user_lexicon 
                    WHERE pinyin = ? 
                    ORDER BY freq DESC, last_used DESC LIMIT ?
                    """,
                    (pinyin, limit)
                )

            rows = cursor.fetchall()

        candidates = []
        for r in rows:
            # Boost frequency so that user-learned words take priority
            effective_freq = 50000 + (r["freq"] * 100)
            candidates.append(Candidate(
                text=r["word"],
                pinyin=r["pinyin"],
                freq=effective_freq,
                comment="自学词"
            ))
        return candidates

    def delete_word(self, word: str) -> bool:
        """Delete a word from user dictionary (e.g. on Shift+Delete)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_lexicon WHERE word = ?", (word,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def sync_to_tsv(self, tsv_path: Optional[Path] = None) -> Path:
        """Sync SQLite user lexicon to user_dict.tsv for the C++ engine."""
        if tsv_path is None:
            tsv_path = Path.home() / ".local" / "share" / "yanmo" / "user_dict.tsv"
        tsv_path = Path(tsv_path)
        tsv_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT word, pinyin, freq FROM user_lexicon ORDER BY freq DESC")
            rows = cursor.fetchall()

        with open(tsv_path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(f"{r['word']}\t{r['pinyin']}\t\t{r['freq']}\n")
        return tsv_path

    def export_to_txt(self, file_path: Path) -> int:
        """Export user dictionary to a plain text TSV file (word\\tpinyin\\tfreq)."""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT word, pinyin, freq FROM user_lexicon ORDER BY freq DESC")
            rows = cursor.fetchall()

        count = 0
        with open(file_path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(f"{r['word']}\t{r['pinyin']}\t{r['freq']}\n")
                count += 1
        return count

    def import_from_file(self, file_path: Path) -> int:
        """
        Intelligently import words from TSV or TXT file.
        Supports:
          1. TSV with 2~4 columns: word\\tpinyin[\\tradical][\\tfreq]
          2. Plain TXT wordlist: one word per line (automatically converts to pinyin).
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return 0

        # Try pypinyin first, fallback to core_lexicon char map
        pypinyin_func = None
        try:
            from pypinyin import lazy_pinyin
            pypinyin_func = lambda w: "".join(lazy_pinyin(w))
        except Exception:
            pass

        if pypinyin_func is None:
            char_map = {
                "系": "xi", "地": "de", "着": "zhe", "得": "de",
                "长": "chang", "乐": "le", "重": "zhong", "行": "xing",
                "便": "bian", "强": "qiang", "发": "fa", "差": "cha",
                "入": "ru"
            }
            core_lex_path = Path(__file__).resolve().parent.parent / "data" / "dict" / "core_lexicon.tsv"
            if core_lex_path.exists():
                with open(core_lex_path, "r", encoding="utf-8", errors="ignore") as clf:
                    for cl in clf:
                        cp = cl.strip().split("\t")
                        if len(cp) >= 2 and len(cp[0]) == 1 and cp[0] not in char_map:
                            char_map[cp[0]] = cp[1]
            pypinyin_func = lambda w: "".join(char_map.get(ch, "") for ch in w)

        now = time.time()
        count = 0
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            for line in lines:
                parts = line.split("\t")
                if len(parts) >= 2:
                    word = parts[0].strip()
                    pinyin = parts[1].strip().lower()
                    freq = 5000
                    if len(parts) >= 4 and parts[3].strip().isdigit():
                        freq = int(parts[3].strip())
                    elif len(parts) >= 3 and parts[2].strip().isdigit():
                        freq = int(parts[2].strip())
                else:
                    word = parts[0].strip()
                    if not word:
                        continue
                    pinyin = pypinyin_func(word) if pypinyin_func else ""
                    if not pinyin:
                        continue
                    freq = 5000

                cursor.execute("""
                    INSERT INTO user_lexicon (word, pinyin, freq, last_used, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(word) DO UPDATE SET freq = freq + excluded.freq, last_used = excluded.last_used
                """, (word, pinyin, freq, now, now))
                count += 1
            conn.commit()

        self.sync_to_tsv()
        return count

    def import_from_txt(self, file_path: Path) -> int:
        return self.import_from_file(file_path)

    def export_full_lexicon(self, out_path: Path, core_lexicon_path: Optional[Path] = None) -> int:
        """Export merged full lexicon (core + user customized words)."""
        if core_lexicon_path is None:
            core_lexicon_path = Path(__file__).resolve().parent.parent / "data" / "dict" / "core_lexicon.tsv"
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        user_words = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT word, pinyin, freq FROM user_lexicon")
            for r in cursor.fetchall():
                user_words[r["word"]] = (r["pinyin"], r["freq"])

        written_words = set()
        count = 0
        with open(out_path, "w", encoding="utf-8") as out_f:
            if core_lexicon_path.exists():
                with open(core_lexicon_path, "r", encoding="utf-8", errors="ignore") as in_f:
                    for line in in_f:
                        parts = line.strip().split("\t")
                        if len(parts) >= 2:
                            w = parts[0].strip()
                            py = parts[1].strip()
                            rad = parts[2].strip() if len(parts) > 2 else ""
                            freq = parts[3].strip() if len(parts) > 3 else "5000"
                            if w in user_words:
                                freq = str(max(int(freq) if freq.isdigit() else 5000, user_words[w][1] + 20000))
                                written_words.add(w)
                            out_f.write(f"{w}\t{py}\t{rad}\t{freq}\n")
                            count += 1

            for w, (py, freq) in user_words.items():
                if w not in written_words:
                    out_f.write(f"{w}\t{py}\t\t{freq + 20000}\n")
                    count += 1

        return count

    def clear(self):
        """Clear all entries in user dictionary."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM user_lexicon")
            conn.commit()
        self.sync_to_tsv()

    def count(self) -> int:
        """Get total number of user words."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM user_lexicon")
            return cursor.fetchone()[0]
