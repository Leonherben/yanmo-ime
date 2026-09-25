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
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
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

    def record_selection(self, word: str, pinyin: str, initial_boost: int = 1):
        """
        Record a user-selected word. If it already exists, increment frequency and update timestamp.
        If it's new, insert with initial frequency.
        """
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
                    (word, pinyin.lower(), initial_boost, now, now)
                )
            conn.commit()

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

    def export_to_txt(self, file_path: Path) -> int:
        """Export user dictionary to a plain text file (word\\tpinyin\\tfreq)."""
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

    def import_from_txt(self, file_path: Path) -> int:
        """Import user dictionary from a plain text file."""
        if not file_path.exists():
            return 0

        now = time.time()
        count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for line in f:
                    parts = line.strip().split("\t")
                    if len(parts) >= 2:
                        word = parts[0].strip()
                        pinyin = parts[1].strip().lower()
                        freq = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 1
                        cursor.execute("""
                            INSERT INTO user_lexicon (word, pinyin, freq, last_used, created_at)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(word) DO UPDATE SET freq = freq + excluded.freq, last_used = excluded.last_used
                        """, (word, pinyin, freq, now, now))
                        count += 1
                conn.commit()
        return count

    def clear(self):
        """Clear all entries in user dictionary (for testing)."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM user_lexicon")
            conn.commit()

    def count(self) -> int:
        """Get total number of user words."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM user_lexicon")
            return cursor.fetchone()[0]
