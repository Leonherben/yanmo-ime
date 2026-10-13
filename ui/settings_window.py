"""
Settings Window for YanMo IME (言墨输入法).
Pure text navigation (no icons), modern GTK 3 desktop GUI with live appearance preview
and full background / accent color / opacity / theme customization.
"""

import json
from pathlib import Path
from typing import Optional, Callable

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from core.user_dict import UserDictionary


THEME_DEFAULTS = {
    "dark": {
        "name": "墨夜深黑 (Dark Obsidian)",
        "bg": "#12161c",
        "accent": "#38bdf8",
    },
    "light": {
        "name": "素纸浅白 (Paper Light)",
        "bg": "#f8fafc",
        "accent": "#2563eb",
    },
    "cyber": {
        "name": "极客幽蓝 (Cyber Slate)",
        "bg": "#0f172a",
        "accent": "#38bdf8",
    },
    "catppuccin": {
        "name": "猫咪暖咖 (Catppuccin Mocha)",
        "bg": "#1e1e2e",
        "accent": "#cba6f7",
    },
    "dracula": {
        "name": "德古拉之夜 (Dracula Dark)",
        "bg": "#282a36",
        "accent": "#bd93f9",
    },
    "gruvbox": {
        "name": "复古绿林 (Gruvbox Dark)",
        "bg": "#282828",
        "accent": "#fe8019",
    },
}


class SettingsWindow(Gtk.Window):
    def __init__(
        self,
        on_config_changed: Optional[Callable[[dict], None]] = None,
        on_lexicon_updated: Optional[Callable[[], None]] = None,
    ):
        super().__init__(title="设置")
        self.set_default_size(780, 560)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.on_config_changed = on_config_changed
        self.on_lexicon_updated = on_lexicon_updated
        self.user_dict = UserDictionary()

        self.config_path = Path.home() / ".config" / "yanmo" / "config.json"
        self.config = self._load_config()

        self._build_ui()
        self._load_css()
        self._update_preview()

    def _load_config(self) -> dict:
        default_cfg = {
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
            "num_style": "arabic",
            "show_voice": True,
            "auto_punct_commit": True,
            "matrix_expand": True,
            "self_learning": True,
            "use_clipboard_injection": True,
        }
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_cfg.update(data)
            except Exception:
                pass
        return default_cfg

    def save_config(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        if self.on_config_changed:
            self.on_config_changed(self.config)

    def _load_css(self):
        css_data = b"""
        window.settings-window {
            background-color: #0b0f17;
            color: #f0f6fc;
        }
        .settings-sidebar {
            background-color: #11151c;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
            padding: 12px;
        }
        .sidebar-title {
            font-size: 15px;
            font-weight: bold;
            color: #f0f6fc;
            padding: 10px 14px 16px 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            margin-bottom: 8px;
        }
        .sidebar-btn {
            background: transparent;
            border: none;
            border-radius: 6px;
            color: #8b949e;
            font-size: 13px;
            font-weight: 500;
            padding: 9px 14px;
        }
        .sidebar-btn:hover {
            background-color: rgba(255, 255, 255, 0.05);
            color: #f0f6fc;
        }
        .sidebar-btn.active {
            background-color: rgba(56, 189, 248, 0.12);
            color: #38bdf8;
            font-weight: bold;
        }
        .content-pane {
            padding: 20px 28px;
            background-color: #161b22;
        }
        .pane-title {
            font-size: 18px;
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 3px;
        }
        .pane-desc {
            font-size: 12px;
            color: #8b949e;
            margin-bottom: 14px;
        }
        .section-header {
            font-size: 13px;
            font-weight: bold;
            color: #38bdf8;
            margin-top: 10px;
            margin-bottom: 6px;
        }
        .setting-row {
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .setting-name {
            font-size: 14px;
            color: #f0f6fc;
            font-weight: 500;
        }
        .setting-hint {
            font-size: 12px;
            color: #8b949e;
        }
        .rad-chip {
            padding: 3px 8px;
            background: rgba(255, 255, 255, 0.06);
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            color: #f0f6fc;
            font-size: 13px;
        }
        .rad-chip:hover {
            background: #f59e0b;
            color: #0b0f17;
            font-weight: bold;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css_data)
        self.get_style_context().add_class("settings-window")
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Dynamic CSS Provider for Live Preview
        self.preview_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), self.preview_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

    def _build_ui(self):
        root_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add(root_box)

        # 1. Left Sidebar (Pure text, NO icons)
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        sidebar_box.get_style_context().add_class("settings-sidebar")
        sidebar_box.set_size_request(210, -1)

        title_lbl = Gtk.Label(label="设置", xalign=0)
        title_lbl.get_style_context().add_class("sidebar-title")
        sidebar_box.pack_start(title_lbl, False, False, 0)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)

        nav_items = [
            ("general", "常规与按键"),
            ("appearance", "外观与悬浮条"),
            ("lexicon", "词库与自学习"),
            ("voice", "离线语音输入"),
            ("radical", "生僻字字典工具"),
            ("about", "关于"),
        ]

        self.nav_buttons = {}
        for tag, label in nav_items:
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("sidebar-btn")
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.set_alignment(0.05, 0.5)
            btn.connect("clicked", self._on_nav_clicked, tag)
            sidebar_box.pack_start(btn, False, False, 0)
            self.nav_buttons[tag] = btn

        root_box.pack_start(sidebar_box, False, False, 0)

        # 2. Right Content Panes
        self._build_general_pane()
        self._build_appearance_pane()
        self._build_lexicon_pane()
        self._build_voice_pane()
        self._build_radical_pane()
        self._build_about_pane()

        root_box.pack_start(self.stack, True, True, 0)
        root_box.show_all()

        # Default to appearance tab
        self.switch_to_tab("appearance")

    def _on_nav_clicked(self, btn, tag):
        self.switch_to_tab(tag)

    def switch_to_tab(self, tag: str):
        for t, b in self.nav_buttons.items():
            if t == tag:
                b.get_style_context().add_class("active")
            else:
                b.get_style_context().remove_class("active")
        self.stack.set_visible_child_name(tag)

    def _create_header(self, title: str, desc: str) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_title = Gtk.Label(label=title, xalign=0)
        lbl_title.get_style_context().add_class("pane-title")
        lbl_desc = Gtk.Label(label=desc, xalign=0)
        lbl_desc.get_style_context().add_class("pane-desc")
        box.pack_start(lbl_title, False, False, 0)
        box.pack_start(lbl_desc, False, False, 0)
        return box

    def _create_row(self, name: str, hint: str, widget: Gtk.Widget) -> Gtk.Box:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        row.get_style_context().add_class("setting-row")

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_n = Gtk.Label(label=name, xalign=0)
        lbl_n.get_style_context().add_class("setting-name")
        lbl_h = Gtk.Label(label=hint, xalign=0)
        lbl_h.get_style_context().add_class("setting-hint")
        info.pack_start(lbl_n, False, False, 0)
        info.pack_start(lbl_h, False, False, 0)

        row.pack_start(info, True, True, 0)
        row.pack_end(widget, False, False, 0)
        return row

    def _build_general_pane(self):
        pane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        pane.get_style_context().add_class("content-pane")
        pane.pack_start(self._create_header("常规与按键习惯", "配置输入法按键映射与中英文切换"), False, False, 0)

        # Switch Shift
        combo_shift = Gtk.ComboBoxText()
        combo_shift.append_text("左 Shift (推荐)")
        combo_shift.append_text("右 Shift")
        combo_shift.append_text("Caps Lock")
        combo_shift.set_active(0)
        pane.pack_start(self._create_row("中/英文切换按键", "按下该按键在中文输入与英文上屏之间切换", combo_shift), False, False, 0)

        # Punctuation Auto-commit
        sw_punct = Gtk.Switch()
        sw_punct.set_active(self.config.get("auto_punct_commit", True))
        sw_punct.connect("state-set", lambda s, state: self._update_cfg("auto_punct_commit", state))
        pane.pack_start(self._create_row("标点自动顶字上屏", "打拼音时输入标点，自动提交首选词并输出中文标点", sw_punct), False, False, 0)

        # Matrix Navigation
        sw_matrix = Gtk.Switch()
        sw_matrix.set_active(self.config.get("matrix_expand", True))
        sw_matrix.connect("state-set", lambda s, state: self._update_cfg("matrix_expand", state))
        pane.pack_start(self._create_row("按 ↓ 展开多行矩阵漫游", "单行候选时按向下箭头展开候选词矩阵并用数字直选", sw_matrix), False, False, 0)

        # Clipboard Injection Toggle
        sw_clip = Gtk.Switch()
        sw_clip.set_active(self.config.get("use_clipboard_injection", True))
        sw_clip.connect("state-set", lambda s, state: self._update_cfg("use_clipboard_injection", state))
        pane.pack_start(
            self._create_row(
                "剪贴板模拟注入",
                "开启后通过剪贴板与模拟按键上屏（注：上屏存在约 150ms 剪贴板暴露期）；关闭则降级为纯 XTEST 逐字映射（单字约 5ms 延迟）",
                sw_clip
            ),
            False, False, 0
        )

        self.stack.add_named(pane, "general")

    def _build_appearance_pane(self):
        pane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        pane.get_style_context().add_class("content-pane")
        pane.pack_start(self._create_header("外观与悬浮条", "自定义候选悬浮窗主题底色、首选强调色、圆角与透明度"), False, False, 0)

        # 1. Theme Preset
        self.combo_theme = Gtk.ComboBoxText()
        themes = [
            ("dark", "墨夜深黑 (Dark Obsidian)"),
            ("light", "素纸浅白 (Paper Light)"),
            ("cyber", "极客幽蓝 (Cyber Slate)"),
            ("catppuccin", "猫咪暖咖 (Catppuccin Mocha)"),
            ("dracula", "德古拉之夜 (Dracula Dark)"),
            ("gruvbox", "复古绿林 (Gruvbox Dark)"),
            ("custom", "自定义调色 (Custom)"),
        ]
        for tid, tname in themes:
            self.combo_theme.append(tid, tname)
        self.combo_theme.set_active_id(self.config.get("theme", "dark"))
        self.combo_theme.connect("changed", self._on_theme_changed)
        pane.pack_start(self._create_row("主题预设方案", "内置主流极客与明暗桌面配色方案", self.combo_theme), False, False, 0)

        # 2. Custom Background Color
        self.bg_color_btn = Gtk.ColorButton()
        bg_col = Gdk.RGBA()
        bg_col.parse(self.config.get("bg_color", "#12161c"))
        self.bg_color_btn.set_rgba(bg_col)
        self.bg_color_btn.connect("color-set", self._on_bg_color_set)
        pane.pack_start(self._create_row("悬浮窗背景颜色 (调色盘)", "自定义悬浮条底色，系统将自动计算最适文字对比度", self.bg_color_btn), False, False, 0)

        # 3. Accent Color
        self.accent_color_btn = Gtk.ColorButton()
        accent_col = Gdk.RGBA()
        accent_col.parse(self.config.get("accent_color", "#38bdf8"))
        self.accent_color_btn.set_rgba(accent_col)
        self.accent_color_btn.connect("color-set", self._on_color_set)
        pane.pack_start(self._create_row("首选词强调色 (调色盘)", "高亮首选词与部首辅码色彩", self.accent_color_btn), False, False, 0)

        # 4. Opacity
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 50, 100, 1)
        scale.set_value(float(self.config.get("opacity", 0.94)) * 100)
        scale.set_size_request(140, -1)
        scale.connect("value-changed", self._on_opacity_changed)
        pane.pack_start(self._create_row("背景不透明度 (50% ~ 100%)", "半透明悬浮条既可隐约透出底层文字，又保证辨识度", scale), False, False, 0)

        # 5. Border Radius
        combo_radius = Gtk.ComboBoxText()
        for r in ["4px", "8px", "12px", "16px"]:
            combo_radius.append(r, f"圆角 {r}")
        combo_radius.set_active_id(self.config.get("border_radius", "8px"))
        combo_radius.connect("changed", lambda c: self._update_cfg("border_radius", c.get_active_id()))
        pane.pack_start(self._create_row("悬浮条圆角弧度", "调节悬浮窗外边框圆角风格", combo_radius), False, False, 0)

        # 6. Candidate Count
        self.combo_count = Gtk.ComboBoxText()
        for c in ["5", "7", "9"]:
            self.combo_count.append(c, f"{c} 个")
        self.combo_count.set_active_id(str(self.config.get("cand_count", 5)))
        self.combo_count.connect("changed", lambda c: self._update_cfg("cand_count", int(c.get_active_id())))
        pane.pack_start(self._create_row("单页候选词数量", "候选条默认展示的候选字词数", self.combo_count), False, False, 0)

        # 7. Live Preview Card
        lbl_preview_title = Gtk.Label(label="效果实时预览", xalign=0)
        lbl_preview_title.get_style_context().add_class("section-header")
        pane.pack_start(lbl_preview_title, False, False, 4)

        self.preview_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.preview_box.get_style_context().add_class("preview-card")
        self.preview_box.set_size_request(-1, 46)

        self.preview_badge = Gtk.Label(label="拼音")
        self.preview_badge.get_style_context().add_class("preview-badge")
        self.preview_box.pack_start(self.preview_badge, False, False, 0)

        self.preview_buf = Gtk.Label(label="yanmo")
        self.preview_buf.get_style_context().add_class("preview-buf")
        self.preview_box.pack_start(self.preview_buf, False, False, 4)

        self.preview_cands_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.preview_box.pack_start(self.preview_cands_box, False, False, 0)

        pane.pack_start(self.preview_box, False, False, 4)

        self.stack.add_named(pane, "appearance")

    def _update_preview(self):
        """Update live preview box CSS dynamically."""
        if not hasattr(self, "preview_provider"):
            return
        theme = self.config.get("theme", "dark")
        bg_hex = self.config.get("bg_color", THEME_DEFAULTS.get(theme, {}).get("bg", "#12161c"))
        accent = self.config.get("accent_color", "#38bdf8")
        opacity = float(self.config.get("opacity", 0.94))
        radius = self.config.get("border_radius", "8px")

        r, g, b = 18, 22, 28
        if bg_hex and bg_hex.startswith("#") and len(bg_hex) in (4, 7):
            if len(bg_hex) == 4:
                bg_hex = f"#{bg_hex[1]*2}{bg_hex[2]*2}{bg_hex[3]*2}"
            try:
                r = int(bg_hex[1:3], 16)
                g = int(bg_hex[3:5], 16)
                b = int(bg_hex[5:7], 16)
            except Exception:
                pass

        lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
        text_col = "#0f172a" if lum > 0.55 else "#f0f6fc"
        border_col = "rgba(0,0,0,0.15)" if lum > 0.55 else "rgba(255,255,255,0.15)"

        css = f"""
        .preview-card {{
            background-color: rgba({r}, {g}, {b}, {opacity});
            border: 1px solid {border_col};
            border-radius: {radius};
            padding: 8px 14px;
        }}
        .preview-badge {{
            background-color: {accent};
            color: #0b0f17;
            font-size: 11px;
            font-weight: bold;
            border-radius: 4px;
            padding: 1px 6px;
        }}
        .preview-buf {{
            color: {text_col};
            font-size: 15px;
            font-weight: bold;
        }}
        .preview-cand {{
            color: {text_col};
            font-size: 15px;
            padding: 2px 6px;
        }}
        .preview-cand.preview-first {{
            background-color: rgba(56, 189, 248, 0.2);
            border: 1px solid {accent};
            border-radius: 4px;
        }}
        """
        try:
            self.preview_provider.load_from_data(css.encode("utf-8"))
            if hasattr(self, "preview_box"):
                self.preview_box.queue_draw()
        except Exception:
            pass

        # Re-populate preview candidates based on cand_count
        if hasattr(self, "preview_cands_box"):
            for child in self.preview_cands_box.get_children():
                self.preview_cands_box.remove(child)
            cand_count = int(self.config.get("cand_count", 5))
            sample_words = ["言墨", "研磨", "颜色", "严密", "掩面", "眼眸", "焰火", "演变", "延期"][:cand_count]
            for idx, word in enumerate(sample_words):
                c_lbl = Gtk.Label(label=f"{idx+1}.{word}")
                c_lbl.get_style_context().add_class("preview-cand")
                if idx == 0:
                    c_lbl.get_style_context().add_class("preview-first")
                self.preview_cands_box.pack_start(c_lbl, False, False, 2)
            self.preview_cands_box.show_all()

    def _on_theme_changed(self, combo):
        tid = combo.get_active_id()
        if not tid or tid == "custom":
            return
        if tid in THEME_DEFAULTS:
            preset = THEME_DEFAULTS[tid]
            self.config["theme"] = tid
            self.config["bg_color"] = preset["bg"]
            self.config["accent_color"] = preset["accent"]

            # Update color pickers visually
            bg_rgba = Gdk.RGBA()
            bg_rgba.parse(preset["bg"])
            self.bg_color_btn.set_rgba(bg_rgba)

            acc_rgba = Gdk.RGBA()
            acc_rgba.parse(preset["accent"])
            self.accent_color_btn.set_rgba(acc_rgba)

            self.save_config()
            self._update_preview()

    def _on_bg_color_set(self, btn):
        rgba = btn.get_rgba()
        hex_color = f"#{int(rgba.red*255):02x}{int(rgba.green*255):02x}{int(rgba.blue*255):02x}"
        self.config["bg_color"] = hex_color
        self.config["theme"] = "custom"
        self.combo_theme.set_active_id("custom")
        self.save_config()
        self._update_preview()

    def _on_color_set(self, btn):
        rgba = btn.get_rgba()
        hex_color = f"#{int(rgba.red*255):02x}{int(rgba.green*255):02x}{int(rgba.blue*255):02x}"
        self.config["accent_color"] = hex_color
        self.save_config()
        self._update_preview()

    def _on_opacity_changed(self, scale):
        self.config["opacity"] = scale.get_value() / 100.0
        self.save_config()
        self._update_preview()

    def _build_lexicon_pane(self):
        pane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        pane.get_style_context().add_class("content-pane")
        pane.pack_start(self._create_header("词库与自学习", "管理核心词库、自学习词频、导入外部词库及全量导出"), False, False, 0)

        # 1. Statistics
        lbl_core = Gtk.Label(label="137,374 词 / 20,898 汉字 (通用规范全覆盖)")
        lbl_core.get_style_context().add_class("setting-hint")
        pane.pack_start(self._create_row("系统核心词库", "内置国家规范汉字全量单字及高频现代汉语词库", lbl_core), False, False, 0)

        self.lbl_user_count = Gtk.Label()
        self.lbl_user_count.get_style_context().add_class("setting-hint")
        self._refresh_user_dict_count()
        pane.pack_start(self._create_row("用户自学与导入词库", "日常输入自学习词汇与外部导入的自定义词条", self.lbl_user_count), False, False, 0)

        # 2. Local self-learning toggle
        sw_learn = Gtk.Switch()
        sw_learn.set_active(self.config.get("self_learning", True))
        sw_learn.connect("notify::active", self._on_self_learning_toggled)
        pane.pack_start(self._create_row("本地词频自学习", "根据日常输入自动提升高频词优先级（数据纯本地保存）", sw_learn), False, False, 0)

        # 3. Import Button
        btn_import = Gtk.Button(label="导入外部词库...")
        btn_import.connect("clicked", self._on_import_lexicon_clicked)
        pane.pack_start(self._create_row("导入词库文件 (TSV / TXT)", "支持标准 TSV (词 拼音 词频) 或纯词表 TXT (智能自动注音)", btn_import), False, False, 0)

        # 4. Export User Lexicon Button
        btn_export_user = Gtk.Button(label="导出用户词库...")
        btn_export_user.connect("clicked", self._on_export_user_lexicon_clicked)
        pane.pack_start(self._create_row("导出自学与导入词库", "将用户本地积累的词条导出为 TSV 文件备份", btn_export_user), False, False, 0)

        # 5. Export Full Lexicon Button
        btn_export_full = Gtk.Button(label="导出全量词库...")
        btn_export_full.connect("clicked", self._on_export_full_lexicon_clicked)
        pane.pack_start(self._create_row("导出全量合并词库", "合并系统核心词库与用户词库并导出为完整 TSV", btn_export_full), False, False, 0)

        # 6. Clear User Lexicon Button
        btn_clear = Gtk.Button(label="清空用户词库")
        btn_clear.connect("clicked", self._on_clear_user_lexicon_clicked)
        pane.pack_start(self._create_row("清空自学词库", "重置所有自学习词频与导入词条（核心词库不受影响）", btn_clear), False, False, 0)

        self.stack.add_named(pane, "lexicon")

    def _refresh_user_dict_count(self):
        count = self.user_dict.count()
        self.lbl_user_count.set_text(f"{count} 条用户词条")

    def _on_self_learning_toggled(self, sw, gparam):
        self.config["self_learning"] = sw.get_active()
        self.save_config()

    def _on_import_lexicon_clicked(self, btn):
        dialog = Gtk.FileChooserDialog(
            title="选择要导入的词库文件 (TSV / TXT)",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            "取消", Gtk.ResponseType.CANCEL,
            "导入", Gtk.ResponseType.OK
        )
        filter_tsv = Gtk.FileFilter()
        filter_tsv.set_name("词库文件 (*.tsv, *.txt)")
        filter_tsv.add_pattern("*.tsv")
        filter_tsv.add_pattern("*.txt")
        dialog.add_filter(filter_tsv)

        filter_all = Gtk.FileFilter()
        filter_all.set_name("所有文件 (*.*)")
        filter_all.add_pattern("*")
        dialog.add_filter(filter_all)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            selected_path = dialog.get_filename()
            dialog.destroy()
            try:
                count = self.user_dict.import_from_file(Path(selected_path))
                self._refresh_user_dict_count()
                if self.on_lexicon_updated:
                    self.on_lexicon_updated()
                msg = Gtk.MessageDialog(
                    parent=self,
                    flags=Gtk.DialogFlags.MODAL,
                    type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    message_format=f"词库导入成功！\n共导入 {count} 条词条，已同步至 C++ 核心引擎并立即生效。"
                )
                msg.run()
                msg.destroy()
            except Exception as e:
                err_msg = Gtk.MessageDialog(
                    parent=self,
                    flags=Gtk.DialogFlags.MODAL,
                    type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    message_format=f"导入词库时发生错误：\n{e}"
                )
                err_msg.run()
                err_msg.destroy()
        else:
            dialog.destroy()

    def _on_export_user_lexicon_clicked(self, btn):
        dialog = Gtk.FileChooserDialog(
            title="导出用户自学与导入词库",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            "取消", Gtk.ResponseType.CANCEL,
            "保存", Gtk.ResponseType.OK
        )
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_name("yanmo_user_dict.tsv")

        filter_tsv = Gtk.FileFilter()
        filter_tsv.set_name("TSV 词库文件 (*.tsv)")
        filter_tsv.add_pattern("*.tsv")
        dialog.add_filter(filter_tsv)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            out_path = dialog.get_filename()
            dialog.destroy()
            try:
                count = self.user_dict.export_to_txt(Path(out_path))
                msg = Gtk.MessageDialog(
                    parent=self,
                    flags=Gtk.DialogFlags.MODAL,
                    type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    message_format=f"用户词库导出成功！\n共导出 {count} 条词条至：\n{out_path}"
                )
                msg.run()
                msg.destroy()
            except Exception as e:
                err_msg = Gtk.MessageDialog(
                    parent=self,
                    flags=Gtk.DialogFlags.MODAL,
                    type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    message_format=f"导出用户词库失败：\n{e}"
                )
                err_msg.run()
                err_msg.destroy()
        else:
            dialog.destroy()

    def _on_export_full_lexicon_clicked(self, btn):
        dialog = Gtk.FileChooserDialog(
            title="导出全量合并词库",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            "取消", Gtk.ResponseType.CANCEL,
            "保存", Gtk.ResponseType.OK
        )
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_name("yanmo_full_lexicon.tsv")

        filter_tsv = Gtk.FileFilter()
        filter_tsv.set_name("TSV 词库文件 (*.tsv)")
        filter_tsv.add_pattern("*.tsv")
        dialog.add_filter(filter_tsv)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            out_path = dialog.get_filename()
            dialog.destroy()
            try:
                count = self.user_dict.export_full_lexicon(Path(out_path))
                msg = Gtk.MessageDialog(
                    parent=self,
                    flags=Gtk.DialogFlags.MODAL,
                    type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    message_format=f"全量词库导出成功！\n共合并导出 {count} 条词条至：\n{out_path}"
                )
                msg.run()
                msg.destroy()
            except Exception as e:
                err_msg = Gtk.MessageDialog(
                    parent=self,
                    flags=Gtk.DialogFlags.MODAL,
                    type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    message_format=f"导出全量词库失败：\n{e}"
                )
                err_msg.run()
                err_msg.destroy()
        else:
            dialog.destroy()

    def _on_clear_user_lexicon_clicked(self, btn):
        confirm = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            message_format="确定要清空所有用户自学与导入的词库吗？\n\n此操作将清除本地记录的自学习词频与导入词条，系统核心词库不受影响。"
        )
        res = confirm.run()
        confirm.destroy()
        if res == Gtk.ResponseType.OK:
            self.user_dict.clear()
            self._refresh_user_dict_count()
            if self.on_lexicon_updated:
                self.on_lexicon_updated()
            msg = Gtk.MessageDialog(
                parent=self,
                flags=Gtk.DialogFlags.MODAL,
                type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                message_format="用户词库已成功清空。"
            )
            msg.run()
            msg.destroy()

    def _build_voice_pane(self):
        pane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        pane.get_style_context().add_class("content-pane")
        pane.pack_start(self._create_header("离线语音输入", "基于 sherpa-onnx / SenseVoice 的本地语音识别"), False, False, 0)

        lbl_status = Gtk.Label(label="● 已就绪 (sherpa-onnx INT8 CPU量化)")
        lbl_status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.25, 0.72, 0.31, 1))
        pane.pack_start(self._create_row("离线语音引擎状态", "纯本地离线计算，无网络音频传输", lbl_status), False, False, 0)

        self.stack.add_named(pane, "voice")

    def _build_radical_pane(self):
        pane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        pane.get_style_context().add_class("content-pane")
        pane.pack_start(self._create_header("生僻字字典工具", "点击任意部首查看读音与笔画，直接复制或用于辅助打字"), False, False, 0)

        rad_categories = [
            ("一 横", ["一", "十", "厂", "匚", "卜", "刂", "冂", "亻", "八", "勹"]),
            ("丨 竖", ["丨", "卜", "刂", "冂", "日", "目", "口", "田", "山", "巾"]),
            ("丿 撇", ["丿", "亻", "彳", "月", "钅", "禾", "白", "鸟", "爪", "父"]),
            ("丶 点", ["丶", "冫", "氵", "灬", "广", "门", "宀", "冖", "礻", "衤"]),
            ("乙 折", ["乙", "又", "廴", "辶", "阝", "女", "弓", "马", "子", "纟"]),
        ]

        for cat_name, rad_list in rad_categories:
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            lbl_cat = Gtk.Label(label=cat_name, xalign=0)
            lbl_cat.set_size_request(60, -1)
            lbl_cat.get_style_context().add_class("setting-hint")
            row_box.pack_start(lbl_cat, False, False, 0)

            flow = Gtk.FlowBox()
            flow.set_max_children_per_line(15)
            flow.set_selection_mode(Gtk.SelectionMode.NONE)

            for rad in rad_list:
                btn = Gtk.Button(label=rad)
                btn.get_style_context().add_class("rad-chip")
                btn.connect("clicked", self._on_radical_btn_clicked, rad)
                flow.add(btn)

            row_box.pack_start(flow, True, True, 0)
            pane.pack_start(row_box, False, False, 0)

        self.rad_result_label = Gtk.Label(label="请点击上方任意部首查看说明或检索", xalign=0)
        self.rad_result_label.get_style_context().add_class("setting-hint")
        pane.pack_start(self.rad_result_label, False, False, 10)

        self.stack.add_named(pane, "radical")

    def _on_radical_btn_clicked(self, btn, rad):
        self.rad_result_label.set_text(f"已选中【{rad}部】。可在打字时按 Tab 输入该部首拼音直接检索对应汉字。")

    def _build_about_pane(self):
        pane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        pane.get_style_context().add_class("content-pane")
        pane.pack_start(self._create_header("关于言墨输入法", "轻量、现代、优雅的 Linux 桌面中文输入法"), False, False, 0)

        info_lbl = Gtk.Label(
            label="言墨 (YanMo IME) v0.1.0\n\n"
                  "• C++20 高性能内核（Trie 树毫秒级检索，内存占用低至 1%）\n"
                  "• 极简悬浮窗设计（支持矩阵漫游与 Tab 辅码检索）\n"
                  "• 针对微软 Surface 与 Linux Mint 特别优化调校\n\n"
                  "开源许可：MIT License\n作者：Leonherben",
            xalign=0
        )
        info_lbl.get_style_context().add_class("setting-hint")
        pane.pack_start(info_lbl, False, False, 0)

        self.stack.add_named(pane, "about")

    def _update_cfg(self, key, value):
        self.config[key] = value
        self.save_config()
        self._update_preview()
