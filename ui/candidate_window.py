"""
Candidate Floating Window for YanMo IME (言墨输入法).
Desktop floating bar with candidate list and corner radical picker toggle.
"""

from pathlib import Path
from typing import Callable, Optional

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from core.engine import YanMoEngine
from core.models import InputMode
from .radical_picker import RadicalPickerPanel


class CandidateWindow(Gtk.Window):
    def __init__(self, engine: YanMoEngine, on_commit: Optional[Callable[[str], None]] = None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.engine = engine
        self.on_commit = on_commit

        # Window properties
        self.set_title("言墨候选条")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_resizable(False)

        # Transparency support
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        self._load_css()
        self._build_ui()

    def _load_css(self):
        css_file = Path(__file__).resolve().parent / "styles.css"
        if css_file.exists():
            css_provider = Gtk.CssProvider()
            css_provider.load_from_path(str(css_file))
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def _build_ui(self):
        # Outer main container
        self.main_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.main_card.get_style_context().add_class("yanmo-candidate-window")
        self.add(self.main_card)

        # 1. Header Box
        self.header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.header_box.get_style_context().add_class("yanmo-header")

        # Mode Badge
        self.badge_label = Gtk.Label(label="拼音")
        self.badge_label.get_style_context().add_class("yanmo-badge-pinyin")
        self.header_box.pack_start(self.badge_label, False, False, 0)

        # Buffer Display
        self.buffer_label = Gtk.Label(label="")
        self.buffer_label.get_style_context().add_class("yanmo-buffer")
        self.header_box.pack_start(self.buffer_label, False, False, 0)

        # Filler
        filler = Gtk.Box()
        self.header_box.pack_start(filler, True, True, 0)

        # Right Corner Radical Picker Toggle Button
        self.btn_picker_toggle = Gtk.Button(label="部首 ▾")
        self.btn_picker_toggle.get_style_context().add_class("yanmo-btn-radical")
        self.btn_picker_toggle.connect("clicked", self._on_toggle_picker)
        self.header_box.pack_start(self.btn_picker_toggle, False, False, 0)

        self.main_card.pack_start(self.header_box, False, False, 0)

        # 2. Candidate List Container (Horizontal)
        self.candidates_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.main_card.pack_start(self.candidates_box, False, False, 0)

        # 3. Expandable Radical Picker Panel (hidden by default)
        self.picker_panel = RadicalPickerPanel(on_selected=self._on_radical_chosen)
        self.picker_panel.set_no_show_all(True)
        self.picker_panel.hide()
        self.main_card.pack_start(self.picker_panel, False, False, 0)

    def _on_toggle_picker(self, button):
        """Toggle visibility of the radical picker grid."""
        if self.picker_panel.get_visible():
            self.picker_panel.hide()
            self.btn_picker_toggle.set_label("部首 ▾")
        else:
            self.picker_panel.show_all()
            self.btn_picker_toggle.set_label("收起 ▴")
        self.resize(1, 1)  # Re-fit window dimensions

    def _on_radical_chosen(self, radical_glyph: str):
        """Called when user clicks a radical in the grid."""
        self.engine.apply_visual_radical_filter(radical_glyph)
        self.update_from_engine()

    def update_from_engine(self):
        """Update window contents from current engine state."""
        state = self.engine.state

        # If committed text just happened
        if state.committed_text and self.on_commit:
            self.on_commit(state.committed_text)

        # If idle and no candidates, hide window
        if state.mode == InputMode.IDLE and not state.pinyin_buffer:
            self.hide()
            return

        # 1. Update Mode Badge & Buffer
        if state.mode == InputMode.RADICAL_FILTER:
            self.badge_label.set_label("部首筛选")
            self.badge_label.get_style_context().remove_class("yanmo-badge-pinyin")
            self.badge_label.get_style_context().add_class("yanmo-badge-radical")

            rad_display = state.radical_buffer if state.radical_buffer else "_"
            self.buffer_label.set_markup(f"<b>{state.pinyin_buffer}</b> <span color='#f59e0b'>[{rad_display}]</span>")
        else:
            self.badge_label.set_label("拼音")
            self.badge_label.get_style_context().remove_class("yanmo-badge-radical")
            self.badge_label.get_style_context().add_class("yanmo-badge-pinyin")
            self.buffer_label.set_text(state.pinyin_buffer)

        # 2. Re-populate Candidate items
        for child in self.candidates_box.get_children():
            self.candidates_box.remove(child)

        for i, cand in enumerate(state.candidates[:9]):
            idx = i + 1
            btn = Gtk.Button()
            btn.get_style_context().add_class("yanmo-candidate-item")

            cand_item_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)

            lbl_idx = Gtk.Label(label=f"{idx}.")
            lbl_idx.get_style_context().add_class("yanmo-cand-index")
            cand_item_box.pack_start(lbl_idx, False, False, 0)

            lbl_text = Gtk.Label(label=cand.text)
            lbl_text.get_style_context().add_class("yanmo-cand-text")
            cand_item_box.pack_start(lbl_text, False, False, 0)

            if cand.comment:
                lbl_comment = Gtk.Label(label=f"({cand.comment})")
                if cand.comment == "自学词":
                    lbl_comment.get_style_context().add_class("yanmo-cand-user")
                else:
                    lbl_comment.get_style_context().add_class("yanmo-cand-comment")
                cand_item_box.pack_start(lbl_comment, False, False, 0)

            btn.add(cand_item_box)
            btn.connect("clicked", self._on_candidate_clicked, i)
            self.candidates_box.pack_start(btn, False, False, 0)

        self.show_all()
        # Keep picker visibility as explicitly toggled
        if not self.btn_picker_toggle.get_label().startswith("收起"):
            self.picker_panel.hide()

        self.resize(1, 1)

    def _on_candidate_clicked(self, button, index: int):
        committed = self.engine.select_candidate(index)
        self.update_from_engine()
        if committed and self.on_commit:
            self.on_commit(committed)
