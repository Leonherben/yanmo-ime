"""
Candidate Floating Window for YanMo IME (言墨输入法).
Desktop floating bar with candidate list and corner radical picker toggle.
Displays all 5 basic stroke categories directly with dynamic spotlighting.
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
        self.picker_visible = False

        # Focus immunity
        self.set_title("言墨候选条")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_resizable(False)
        self.set_accept_focus(False)
        self.set_focus_on_map(False)
        self.set_can_focus(False)
        self.set_app_paintable(True)
        self.set_type_hint(Gdk.WindowTypeHint.POPUP_MENU)

        self.get_style_context().add_class("yanmo-window")

        # RGBA Transparency
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
                Gtk.STYLE_PROVIDER_PRIORITY_USER
            )

    def _build_ui(self):
        self.main_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.main_card.get_style_context().add_class("yanmo-candidate-window")
        self.main_card.set_can_focus(False)
        self.add(self.main_card)

        # 1. Header Box
        self.header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.header_box.get_style_context().add_class("yanmo-header")
        self.header_box.set_can_focus(False)

        # Mode Badge
        self.badge_label = Gtk.Label(label="拼音")
        self.badge_label.get_style_context().add_class("yanmo-badge-pinyin")
        self.header_box.pack_start(self.badge_label, False, False, 0)

        # Buffer Display
        self.buffer_label = Gtk.Label(label="")
        self.buffer_label.get_style_context().add_class("yanmo-buffer")
        self.header_box.pack_start(self.buffer_label, False, False, 0)

        filler = Gtk.Box()
        filler.set_can_focus(False)
        self.header_box.pack_start(filler, True, True, 0)

        # Right Corner Radical Picker Toggle Button
        self.btn_picker_toggle = Gtk.Button(label="部首全景 ▾")
        self.btn_picker_toggle.set_can_focus(False)
        self.btn_picker_toggle.set_focus_on_click(False)
        self.btn_picker_toggle.get_style_context().add_class("yanmo-btn-radical")
        self.btn_picker_toggle.connect("clicked", self._on_toggle_picker)
        self.header_box.pack_start(self.btn_picker_toggle, False, False, 0)

        self.main_card.pack_start(self.header_box, False, False, 0)

        # 2. Candidate List Container (Horizontal)
        self.candidates_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.candidates_box.set_can_focus(False)
        self.main_card.pack_start(self.candidates_box, False, False, 0)

        # 3. Expandable Radical Picker Panel (All 5 Categories in view)
        self.picker_panel = RadicalPickerPanel(
            on_selected=self._on_radical_chosen,
            on_stroke_category=self._on_stroke_category_chosen
        )
        self.picker_panel.hide()
        self.main_card.pack_start(self.picker_panel, False, False, 0)

    def _on_toggle_picker(self, button=None):
        """Toggle visibility of the radical picker grid."""
        if self.picker_visible:
            self.picker_visible = False
            self.picker_panel.hide()
            self.btn_picker_toggle.set_label("部首全景 ▾")
        else:
            self.picker_visible = True
            self.picker_panel.show_all()
            self.btn_picker_toggle.set_label("收起 ▴")
            self.show()
        self.resize(1, 1)

    def show_radical_picker(self):
        """Programmatically expand radical picker panel."""
        self.picker_visible = True
        self.picker_panel.show_all()
        self.btn_picker_toggle.set_label("收起 ▴")
        self.show()
        self.resize(1, 1)

    def _on_stroke_category_chosen(self, stroke_key: str):
        """Called when user clicks a category badge like [丶 点 (D)]."""
        self.engine.apply_visual_radical_filter(stroke_key)
        self.update_from_engine()

    def _on_radical_chosen(self, radical_glyph: str):
        """Called when user clicks an individual radical chip."""
        self.engine.apply_visual_radical_filter(radical_glyph)
        self.update_from_engine()

    def update_from_engine(self):
        """Update window contents from current engine state."""
        state = self.engine.state

        # If committed text just happened
        if state.committed_text and self.on_commit:
            self.on_commit(state.committed_text)

        has_content = bool(
            state.pinyin_buffer or 
            state.radical_buffer or 
            state.candidates or 
            self.picker_visible
        )

        if not has_content:
            self.hide()
            return

        # 1. Update Mode Badge & Buffer
        if state.mode == InputMode.RADICAL_FILTER:
            self.badge_label.set_label("部首/笔画")
            self.badge_label.get_style_context().remove_class("yanmo-badge-pinyin")
            self.badge_label.get_style_context().add_class("yanmo-badge-radical")

            rad_display = state.radical_buffer if state.radical_buffer else "_"

            # If user typed a single stroke key (h, s, p, d, z), auto-highlight that category row!
            if state.radical_buffer and state.radical_buffer[0].lower() in ("h", "s", "p", "d", "z"):
                stroke_key = state.radical_buffer[0].lower()
                stroke_names = {"h": "横(H)", "s": "竖(S)", "p": "撇(P)", "d": "点(D)", "z": "折(Z)"}
                stroke_label = stroke_names[stroke_key]
                self.picker_panel.highlight_stroke(stroke_key)

                if state.pinyin_buffer:
                    self.buffer_label.set_markup(f"<b>{state.pinyin_buffer}</b> <span color='#f59e0b'>[首笔: {stroke_label}]</span>")
                else:
                    self.buffer_label.set_markup(f"<span color='#f59e0b'>[首笔查字: {stroke_label}]</span>")
            else:
                self.picker_panel.highlight_stroke(None)
                if state.pinyin_buffer:
                    self.buffer_label.set_markup(f"<b>{state.pinyin_buffer}</b> <span color='#f59e0b'>[部首: {rad_display}]</span>")
                else:
                    self.buffer_label.set_markup(f"<span color='#f59e0b'>[部首查字: {rad_display}]</span>")
        else:
            self.badge_label.set_label("拼音")
            self.badge_label.get_style_context().remove_class("yanmo-badge-radical")
            self.badge_label.get_style_context().add_class("yanmo-badge-pinyin")
            self.buffer_label.set_text(state.pinyin_buffer if state.pinyin_buffer else "(待输入)")
            self.picker_panel.highlight_stroke(None)

        # 2. Re-populate Candidate items
        for child in self.candidates_box.get_children():
            self.candidates_box.remove(child)

        if state.candidates:
            for i, cand in enumerate(state.candidates[:9]):
                idx = i + 1
                btn = Gtk.Button()
                btn.set_can_focus(False)
                btn.set_focus_on_click(False)
                btn.get_style_context().add_class("yanmo-candidate-item")

                cand_item_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
                cand_item_box.set_can_focus(False)

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
        else:
            if state.mode == InputMode.RADICAL_FILTER:
                lbl_empty = Gtk.Label(label=" (按 H/S/P/D/Z 或直接在下方点选部首) ")
                lbl_empty.get_style_context().add_class("yanmo-cand-index")
                self.candidates_box.pack_start(lbl_empty, False, False, 0)

        # 3. Show card
        self.main_card.show_all()
        if not self.picker_visible:
            self.picker_panel.hide()

        self.show()
        self.resize(1, 1)

    def _on_candidate_clicked(self, button, index: int):
        committed = self.engine.select_candidate(index)
        self.update_from_engine()
        if committed and self.on_commit:
            self.on_commit(committed)
