"""
Candidate Floating Window for YanMo IME (言墨输入法).
Desktop floating bar with minimalist WeChat Keyboard aesthetic,
C++20 high-performance engine integration, 4-row matrix blind typing navigation,
and dynamic theme/color customization.
"""

import json
from pathlib import Path
from typing import Callable, Optional, List

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk

from core.cpp_engine import YanMoCppEngine
from .radical_picker import RadicalPickerPanel


THEME_PALETTES = {
    "dark": {
        "r": 18, "g": 22, "b": 28,
        "border": "rgba(255, 255, 255, 0.12)",
        "text": "#f0f6fc",
        "num": "#8b949e",
        "buffer": "#f8fafc",
        "accent": "#38bdf8",
        "item_bg": "rgba(255, 255, 255, 0.05)",
    },
    "light": {
        "r": 248, "g": 250, "b": 252,
        "border": "rgba(0, 0, 0, 0.12)",
        "text": "#0f172a",
        "num": "#64748b",
        "buffer": "#0f172a",
        "accent": "#2563eb",
        "item_bg": "rgba(0, 0, 0, 0.04)",
    },
    "cyber": {
        "r": 15, "g": 23, "b": 42,
        "border": "rgba(56, 189, 248, 0.35)",
        "text": "#f8fafc",
        "num": "#64748b",
        "buffer": "#38bdf8",
        "accent": "#38bdf8",
        "item_bg": "rgba(56, 189, 248, 0.06)",
    },
    "catppuccin": {
        "r": 30, "g": 30, "b": 46,
        "border": "rgba(203, 166, 247, 0.3)",
        "text": "#cdd6f4",
        "num": "#a6adc8",
        "buffer": "#cdd6f4",
        "accent": "#cba6f7",
        "item_bg": "rgba(203, 166, 247, 0.06)",
    },
    "dracula": {
        "r": 40, "g": 42, "b": 54,
        "border": "rgba(189, 147, 249, 0.35)",
        "text": "#f8f8f2",
        "num": "#6272a4",
        "buffer": "#f8f8f2",
        "accent": "#bd93f9",
        "item_bg": "rgba(189, 147, 249, 0.06)",
    },
    "gruvbox": {
        "r": 40, "g": 40, "b": 40,
        "border": "rgba(254, 128, 25, 0.35)",
        "text": "#ebdbb2",
        "num": "#a89984",
        "buffer": "#ebdbb2",
        "accent": "#fe8019",
        "item_bg": "rgba(254, 128, 25, 0.06)",
    },
}


class CandidateWindow(Gtk.Window):
    def __init__(
        self,
        engine: YanMoCppEngine,
        on_commit: Optional[Callable[[str], None]] = None,
        on_open_settings: Optional[Callable[[str], None]] = None,
        config: Optional[dict] = None,
        on_user_dragged: Optional[Callable[[int, int], None]] = None
    ):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.engine = engine
        self.on_commit = on_commit
        self.on_open_settings = on_open_settings
        self.config = config or self._load_default_config()
        self.on_user_dragged = on_user_dragged

        self._target_pos: Optional[Tuple[int, int]] = None
        self.voice_recording = False
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON1_MOTION_MASK)
        self.connect("button-press-event", self._on_button_press)
        self.connect("motion-notify-event", self._on_motion_notify)

        # Window properties for focus-free desktop overlay (override-redirect)
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
        self.move(-2000, -2000)

        self.get_style_context().add_class("yanmo-window")

        # RGBA Transparency
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        self.css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

        self._build_ui()
        self.picker_panel = RadicalPickerPanel(on_selected=self._on_radical_chosen)
        self.btn_voice_toggle = Gtk.Button(label="语音")
        self.btn_voice_toggle.connect("clicked", lambda b: self.start_voice_recording() if not self.voice_recording else self.stop_voice_recording())
        self.apply_config(self.config)

    def _load_default_config(self) -> dict:
        cfg_path = Path.home() / ".config" / "yanmo" / "config.json"
        defaults = {
            "orientation": "horizontal",
            "cand_count": 5,
            "border_radius": "8px",
            "theme": "dark",
            "bg_color": "#12161c",
            "accent_color": "#38bdf8",
            "opacity": 0.94,
            "blur": True,
            "font_size": "16px",
            "font_family": "system",
        }
        if cfg_path.exists():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    defaults.update(json.load(f))
            except Exception:
                pass
        return defaults

    def apply_config(self, cfg: dict):
        """Apply user configuration styles dynamically."""
        self.config.update(cfg)
        cand_count = int(self.config.get("cand_count", 5))
        if hasattr(self.engine, "set_candidate_count"):
            self.engine.set_candidate_count(cand_count)
        radius = self.config.get("border_radius", "8px")
        opacity = float(self.config.get("opacity", 0.94))
        font_size = self.config.get("font_size", "16px")
        theme_key = self.config.get("theme", "dark")
        custom_bg = self.config.get("bg_color", "")

        palette = THEME_PALETTES.get(theme_key, THEME_PALETTES["dark"]).copy()

        # Handle custom background color override
        if custom_bg and custom_bg.startswith("#") and len(custom_bg) in (4, 7):
            if len(custom_bg) == 4:
                custom_bg = f"#{custom_bg[1]*2}{custom_bg[2]*2}{custom_bg[3]*2}"
            try:
                r = int(custom_bg[1:3], 16)
                g = int(custom_bg[3:5], 16)
                b = int(custom_bg[5:7], 16)
                palette["r"], palette["g"], palette["b"] = r, g, b
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
                if luminance > 0.55:
                    palette["text"] = "#0f172a"
                    palette["num"] = "#64748b"
                    palette["buffer"] = "#0f172a"
                    palette["border"] = "rgba(0, 0, 0, 0.15)"
                    palette["item_bg"] = "rgba(0, 0, 0, 0.05)"
                else:
                    palette["text"] = "#f0f6fc"
                    palette["num"] = "#8b949e"
                    palette["buffer"] = "#f8fafc"
                    palette["border"] = "rgba(255, 255, 255, 0.15)"
                    palette["item_bg"] = "rgba(255, 255, 255, 0.06)"
            except Exception:
                pass

        user_accent = self.config.get("accent_color")
        if user_accent:
            palette["accent"] = user_accent

        bg_r, bg_g, bg_b = palette["r"], palette["g"], palette["b"]
        border_col = palette["border"]
        text_col = palette["text"]
        num_col = palette["num"]
        buf_col = palette["buffer"]
        accent = palette["accent"]
        item_bg = palette["item_bg"]

        # Generate dynamic CSS targeting candidate window
        css_text = f"""
        window.yanmo-window {{
            background-color: transparent;
            background: transparent;
        }}
        .yanmo-candidate-window {{
            background-color: rgba({bg_r}, {bg_g}, {bg_b}, {opacity});
            border: 1px solid {border_col};
            border-radius: {radius};
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.55);
            padding: 6px 12px;
        }}
        .yanmo-header {{
            border-bottom: 1px solid {border_col};
            padding-bottom: 4px;
            margin-bottom: 4px;
        }}
        .yanmo-buffer {{
            font-size: {font_size};
            font-weight: 600;
            color: {buf_col};
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Noto Sans CJK SC", sans-serif;
        }}
        .yanmo-badge-pinyin {{
            background-color: {accent};
            color: #0b0f17;
            font-size: 11px;
            font-weight: bold;
            border-radius: 4px;
            padding: 1px 6px;
            margin-right: 6px;
        }}
        .yanmo-badge-radical {{
            background-color: #f59e0b;
            color: #1e293b;
            font-size: 11px;
            font-weight: bold;
            border-radius: 4px;
            padding: 1px 6px;
            margin-right: 6px;
        }}
        .yanmo-badge-voice {{
            background-color: #ef4444;
            color: #ffffff;
            font-size: 11px;
            font-weight: bold;
            border-radius: 4px;
            padding: 1px 6px;
            margin-right: 6px;
        }}
        .yanmo-badge-security {{
            background-color: #dc2626;
            color: #ffffff;
            font-size: 11px;
            font-weight: bold;
            border-radius: 4px;
            padding: 1px 6px;
            margin-right: 6px;
        }}
        .yanmo-page-hint {{
            font-size: 11px;
            color: {num_col};
            font-weight: 500;
            margin-left: 8px;
        }}
        .yanmo-cand-row {{
            padding: 2px 0;
            border-radius: 6px;
        }}
        .yanmo-cand-row.active-row {{
            background-color: rgba(56, 189, 248, 0.10);
            border: 1px solid rgba(56, 189, 248, 0.35);
        }}
        .yanmo-row-cursor {{
            font-size: 11px;
            color: {accent};
            font-weight: bold;
            min-width: 14px;
            margin-right: 2px;
        }}
        .yanmo-candidate-item {{
            background: {item_bg};
            border: 1px solid transparent;
            border-radius: 5px;
            padding: 3px 6px;
            margin: 1px 2px;
            min-height: 28px;
        }}
        .yanmo-candidate-item:hover {{
            background-color: rgba(255, 255, 255, 0.15);
            border-color: rgba(255, 255, 255, 0.25);
        }}
        .yanmo-candidate-item.highlighted {{
            background-color: rgba(56, 189, 248, 0.22);
            border-color: {accent};
        }}
        .yanmo-cand-index {{
            color: {num_col};
            font-size: 12px;
            font-weight: 600;
            margin-right: 3px;
        }}
        .yanmo-cand-text {{
            color: {text_col};
            font-size: {font_size};
            font-weight: 500;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Noto Sans CJK SC", sans-serif;
        }}
        """
        try:
            self.css_provider.load_from_data(css_text.encode("utf-8"))
        except Exception:
            pass
        self.queue_draw()
        if hasattr(self, "main_card"):
            self.main_card.queue_draw()
        if self.is_visible():
            self.update_from_engine()

    def _build_ui(self):
        self.main_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
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

        # Page Hint (e.g. 1/12)
        self.page_hint_label = Gtk.Label(label="")
        self.page_hint_label.get_style_context().add_class("yanmo-page-hint")
        self.header_box.pack_start(self.page_hint_label, False, False, 0)

        self.main_card.pack_start(self.header_box, False, False, 0)

        # Enable dragging floating bar by header
        self.header_box.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON1_MOTION_MASK)
        self.header_box.connect("button-press-event", self._on_header_press)
        self.header_box.connect("motion-notify-event", self._on_header_motion)

        # 2. Candidate Rows Container (Vertical stack of 1 to 4 rows)
        self.rows_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.rows_box.set_can_focus(False)
        self.main_card.pack_start(self.rows_box, False, False, 0)

    def set_voice_recording(self, recording: bool):
        """Update display for Push-To-Talk voice dictation."""
        self.voice_recording = recording
        if hasattr(self, "btn_voice_toggle"):
            self.btn_voice_toggle.set_label("倾听中" if recording else "语音")
        if recording:
            self.badge_label.set_label("语音")
            self.badge_label.get_style_context().remove_class("yanmo-badge-pinyin")
            self.badge_label.get_style_context().remove_class("yanmo-badge-radical")
            self.badge_label.get_style_context().add_class("yanmo-badge-voice")
            self.buffer_label.set_text("正在倾听中... (松开立即上屏)")
            self.page_hint_label.set_text("")
            for child in self.rows_box.get_children():
                self.rows_box.remove(child)
            self.show_all()
            self.resize(1, 1)
        else:
            self.update_from_engine()

    def _on_radical_chosen(self, radical: str):
        """Callback when a radical is selected from picker panel."""
        if hasattr(self.engine, "apply_visual_radical_filter"):
            self.engine.apply_visual_radical_filter(radical)
        self.update_from_engine()

    def start_voice_recording(self) -> bool:
        """Begin voice recording UI state and activate underlying voice engine."""
        self.set_voice_recording(True)
        if hasattr(self.engine, "start_voice_recording"):
            return self.engine.start_voice_recording()
        elif hasattr(self.engine, "voice_engine") and self.engine.voice_engine:
            return self.engine.voice_engine.start_recording()
        return True

    def stop_voice_recording(self, callback: Optional[Callable[[str], None]] = None) -> str:
        """Stop voice recording, transcribe and trigger commit callback."""
        self.set_voice_recording(False)
        text = ""
        if hasattr(self.engine, "stop_voice_recording"):
            text = self.engine.stop_voice_recording()
        elif hasattr(self.engine, "voice_engine") and self.engine.voice_engine:
            text = self.engine.voice_engine.stop_recording()

        if text and self.on_commit:
            self.on_commit(text)
        if callback:
            callback(text)
        return text

    def update_from_engine(self):
        """Synchronize window layout and content from C++ engine status."""
        status = self.engine.get_status()

        # Handle text commitment
        committed = status.get("committed_text", "")
        if committed:
            if hasattr(self.engine, "clear_committed_text"):
                self.engine.clear_committed_text()
            if self.on_commit:
                self.on_commit(committed)

        mode = status["mode"]
        buf = status["pinyin_buffer"]
        total_cands = status["total_candidates"]

        if (mode == "IDLE" and not buf) and not self.voice_recording:
            self.hide()
            return

        # 1. Update Header
        if mode == "RADICAL":
            self.badge_label.set_label("部首")
            self.badge_label.get_style_context().remove_class("yanmo-badge-pinyin")
            self.badge_label.get_style_context().remove_class("yanmo-badge-voice")
            self.badge_label.get_style_context().add_class("yanmo-badge-radical")
            hint = status["radical_hint"]
            disp = f"{buf} [{hint}]" if hint else f"{buf} (按部首拼音或H/S/P/D/Z)"
            self.buffer_label.set_text(disp)
        else:
            self.badge_label.set_label("拼音")
            self.badge_label.get_style_context().remove_class("yanmo-badge-radical")
            self.badge_label.get_style_context().remove_class("yanmo-badge-voice")
            self.badge_label.get_style_context().add_class("yanmo-badge-pinyin")
            self.buffer_label.set_text(buf if buf else "(待输入)")

        # Page hint
        page_offset = status["page_offset"]
        cand_count = self.config.get("cand_count", 5)
        if total_cands > cand_count:
            cur_page = page_offset + 1
            max_page = (total_cands + cand_count - 1) // cand_count
            self.page_hint_label.set_text(f"{cur_page}/{max_page} [-/=]")
        else:
            self.page_hint_label.set_text("")

        # 2. Render Candidate Rows
        for child in self.rows_box.get_children():
            self.rows_box.remove(child)

        is_expanded = status["is_expanded"]
        active_row = status["active_row"]

        # If expanded: show up to 4 rows
        # If not expanded: show single row (page_offset)
        rows_to_render = 4 if is_expanded else 1
        is_vertical = (self.config.get("orientation") == "vertical")

        for r_rel in range(rows_to_render):
            row_idx = page_offset + r_rel
            cands = self.engine.get_row_candidates(row_idx)
            if not cands and r_rel > 0:
                continue

            row_orientation = Gtk.Orientation.VERTICAL if (is_vertical and not is_expanded) else Gtk.Orientation.HORIZONTAL
            row_box = Gtk.Box(orientation=row_orientation, spacing=3)
            row_box.set_can_focus(False)
            row_box.get_style_context().add_class("yanmo-cand-row")

            if is_expanded and r_rel == active_row:
                row_box.get_style_context().add_class("active-row")
                cursor_lbl = Gtk.Label(label="▶")
                cursor_lbl.get_style_context().add_class("yanmo-row-cursor")
                row_box.pack_start(cursor_lbl, False, False, 2)
            elif is_expanded:
                spacer_lbl = Gtk.Label(label="  ")
                spacer_lbl.get_style_context().add_class("yanmo-row-cursor")
                row_box.pack_start(spacer_lbl, False, False, 2)

            for i, word in enumerate(cands):
                btn = Gtk.Button()
                btn.set_can_focus(False)
                btn.set_focus_on_click(False)
                btn.get_style_context().add_class("yanmo-candidate-item")

                # Highlight top candidate of active row
                if (not is_expanded and i == 0) or (is_expanded and r_rel == active_row and i == 0):
                    btn.get_style_context().add_class("highlighted")

                item_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
                item_box.set_can_focus(False)

                lbl_idx = Gtk.Label(label=f"{i+1}.")
                lbl_idx.get_style_context().add_class("yanmo-cand-index")
                item_box.pack_start(lbl_idx, False, False, 0)

                lbl_text = Gtk.Label(label=word)
                lbl_text.get_style_context().add_class("yanmo-cand-text")
                item_box.pack_start(lbl_text, False, False, 0)

                btn.add(item_box)
                btn.connect("clicked", self._on_candidate_clicked, i)
                row_box.pack_start(btn, False, False, 0)

            self.rows_box.pack_start(row_box, False, False, 0)

        if self._target_pos:
            super().move(self._target_pos[0], self._target_pos[1])
        self.main_card.show_all()
        self.resize(1, 1)
        self.show()

    def show_security_blocked(self, text: str):
        """
        Display security block notification and retain committed text for manual user handling.
        Triggered when target window is identified as password or authentication dialog.
        """
        self.badge_label.set_label("安全拦截")
        self.badge_label.get_style_context().remove_class("yanmo-badge-pinyin")
        self.badge_label.get_style_context().remove_class("yanmo-badge-radical")
        self.badge_label.get_style_context().remove_class("yanmo-badge-voice")
        self.badge_label.get_style_context().add_class("yanmo-badge-security")
        self.buffer_label.set_text("检测到密码/认证窗口，已阻断自动注入")
        self.page_hint_label.set_text("[安全保护]")

        for child in self.rows_box.get_children():
            self.rows_box.remove(child)

        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        row_box.set_can_focus(False)
        row_box.get_style_context().add_class("yanmo-cand-row")

        btn = Gtk.Button()
        btn.set_can_focus(False)
        btn.set_focus_on_click(False)
        btn.get_style_context().add_class("yanmo-candidate-item")
        btn.get_style_context().add_class("highlighted")

        item_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        item_box.set_can_focus(False)

        lbl_idx = Gtk.Label(label="保留文本:")
        lbl_idx.get_style_context().add_class("yanmo-cand-index")
        item_box.pack_start(lbl_idx, False, False, 0)

        lbl_text = Gtk.Label(label=text)
        lbl_text.get_style_context().add_class("yanmo-cand-text")
        item_box.pack_start(lbl_text, False, False, 0)

        btn.add(item_box)
        row_box.pack_start(btn, False, False, 0)

        lbl_hint = Gtk.Label(label="(可手动使用，按 ESC 关闭)")
        lbl_hint.get_style_context().add_class("yanmo-cand-index")
        row_box.pack_start(lbl_hint, False, False, 4)

        self.rows_box.pack_start(row_box, False, False, 0)

        if self._target_pos:
            super().move(self._target_pos[0], self._target_pos[1])
        self.main_card.show_all()
        self.resize(1, 1)
        self.show()

    def move(self, x: int, y: int):
        self._target_pos = (x, y)
        super().move(x, y)

    def _on_candidate_clicked(self, button, index: int):
        self.engine.select_candidate(index)
        self.update_from_engine()

    def _on_button_press(self, widget, event):
        if event.button == 1:
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root
            pos = self.get_position()
            self._win_start_x, self._win_start_y = pos[0], pos[1]
            return True
        elif event.button == 3:  # Right-click
            if self.on_open_settings:
                self.on_open_settings("appearance")
                return True
        return False

    def _on_motion_notify(self, widget, event):
        if hasattr(self, "_drag_start_x") and (event.state & Gdk.ModifierType.BUTTON1_MASK):
            dx = int(event.x_root - self._drag_start_x)
            dy = int(event.y_root - self._drag_start_y)
            new_x = self._win_start_x + dx
            new_y = self._win_start_y + dy
            self.move(new_x, new_y)
            if self.on_user_dragged:
                self.on_user_dragged(new_x, new_y)
            return True
        return False

    def _on_header_press(self, widget, event):
        return self._on_button_press(widget, event)

    def _on_header_motion(self, widget, event):
        return self._on_motion_notify(widget, event)
