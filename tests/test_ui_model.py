import unittest
import tempfile
from pathlib import Path
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from core.engine import YanMoEngine
from core.models import InputMode
from ui.candidate_window import CandidateWindow
from ui.radical_picker import RadicalPickerPanel


class TestUIModel(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.user_db = Path(self.temp_dir.name) / "ui_test_user.db"
        self.engine = YanMoEngine(user_db_path=self.user_db)
        self.committed_log = []
        self.window = CandidateWindow(
            engine=self.engine,
            on_commit=lambda text: self.committed_log.append(text)
        )

    def tearDown(self):
        self.window.destroy()
        self.temp_dir.cleanup()

    def test_window_initialization(self):
        self.assertIsNotNone(self.window)
        self.assertEqual(self.window.get_title(), "言墨候选条")
        self.assertIsNotNone(self.window.picker_panel)

    def test_radical_picker_callback(self):
        # Type 'h', 'e'
        self.engine.feed_key("h")
        self.engine.feed_key("e")
        self.window.update_from_engine()

        # Simulate clicking '氵' in the radical panel
        self.window._on_radical_chosen("氵")
        self.assertEqual(self.engine.state.mode, InputMode.RADICAL_FILTER)

        candidate_texts = [c.text for c in self.engine.state.candidates]
        self.assertIn("河", candidate_texts)
        self.assertNotIn("核", candidate_texts)

    def test_candidate_click_commits(self):
        self.engine.feed_key("h")
        self.engine.feed_key("e")
        self.window.update_from_engine()

        # Click candidate #0
        self.window._on_candidate_clicked(None, 0)
        self.assertTrue(len(self.committed_log) > 0)
        self.assertEqual(self.committed_log[-1], "和")


if __name__ == "__main__":
    unittest.main()
