"""
Radical Picker Panel for YanMo IME (言墨输入法).
All 5 Basic Stroke Categories (一横, 丨竖, 丿撇, 丶点, 乙折) displayed simultaneously!
Zero extra clicks needed: visual overview of all radicals with keyboard H/S/P/D/Z instant spotlight.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from typing import Callable, Dict, List, Optional

# Radicals categorized strictly by their first stroke (横、竖、撇、点、折)
STROKE_ROWS = [
    ("h", "一 横 (H)", ["一", "十", "厂", "匚", "土", "士", "工", "干", "木", "寸", "王", "石", "车", "耳", "雨", "西", "革"]),
    ("s", "丨 竖 (S)", ["丨", "卜", "刂", "口", "囗", "山", "巾", "日", "目", "田", "皿", "虫", "止", "非", "齿", "骨"]),
    ("p", "丿 撇 (P)", ["丿", "人", "亻", "八", "几", "夕", "大", "女", "牛", "牜", "白", "禾", "竹", "⺮", "月", "舟", "金", "钅", "鸟", "鱼"]),
    ("d", "丶 点 (D)", ["丶", "冫", "氵", "广", "门", "宀", "穴", "心", "忄", "户", "文", "方", "火", "灬", "示", "礻", "衣", "衤", "言", "讠"]),
    ("z", "乙 折 (Z)", ["乙", "刀", "力", "又", "弓", "己", "子", "纟", "走", "辶", "阝", "马", "鬼"]),
]


class RadicalPickerPanel(Gtk.Box):
    def __init__(
        self,
        on_selected: Optional[Callable[[str], None]] = None,
        on_stroke_category: Optional[Callable[[str], None]] = None
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.get_style_context().add_class("yanmo-radical-panel")
        self.on_selected = on_selected
        self.on_stroke_category = on_stroke_category
        self.set_can_focus(False)

        self.row_widgets: Dict[str, Gtk.Box] = {}
        self.badge_buttons: Dict[str, Gtk.Button] = {}

        self._build_ui()
        self.show_all()

    def _build_ui(self):
        # Header title
        lbl_hint = Gtk.Label(label="📌 五笔画部首直观全景 (敲击或点击 H/S/P/D/Z 直接高亮归类，点击部首直接过滤)")
        lbl_hint.set_xalign(0.0)
        lbl_hint.get_style_context().add_class("yanmo-rad-hint")
        self.pack_start(lbl_hint, False, False, 0)

        # Build all 5 stroke categories in direct view
        for stroke_key, label_name, radicals in STROKE_ROWS:
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            row_box.set_can_focus(False)
            row_box.get_style_context().add_class("yanmo-stroke-row")

            # Left: Category badge button (Clicking it selects the whole stroke group!)
            btn_badge = Gtk.Button(label=label_name)
            btn_badge.set_can_focus(False)
            btn_badge.set_focus_on_click(False)
            btn_badge.get_style_context().add_class("yanmo-stroke-badge")
            btn_badge.connect("clicked", self._on_badge_clicked, stroke_key)
            row_box.pack_start(btn_badge, False, False, 0)
            self.badge_buttons[stroke_key] = btn_badge

            # Right: Horizontal flow of radicals belonging to this stroke
            flow_box = Gtk.FlowBox()
            flow_box.set_can_focus(False)
            flow_box.set_selection_mode(Gtk.SelectionMode.NONE)
            flow_box.set_max_children_per_line(22)
            flow_box.set_min_children_per_line(8)
            flow_box.set_row_spacing(2)
            flow_box.set_column_spacing(2)

            for rad in radicals:
                btn_rad = Gtk.Button(label=rad)
                btn_rad.set_can_focus(False)
                btn_rad.set_focus_on_click(False)
                btn_rad.get_style_context().add_class("yanmo-rad-chip")
                btn_rad.connect("clicked", self._on_radical_clicked, rad)
                flow_box.add(btn_rad)

            row_box.pack_start(flow_box, True, True, 0)
            self.row_widgets[stroke_key] = row_box
            self.pack_start(row_box, False, False, 0)

    def highlight_stroke(self, stroke_key: Optional[str]):
        """Highlight the active stroke row and dim others."""
        for key, row in self.row_widgets.items():
            ctx = row.get_style_context()
            ctx.remove_class("highlighted")
            if stroke_key and key == stroke_key.lower():
                ctx.add_class("highlighted")

    def _on_badge_clicked(self, button, stroke_key: str):
        if self.on_stroke_category:
            self.on_stroke_category(stroke_key)

    def _on_radical_clicked(self, button, radical: str):
        if self.on_selected:
            self.on_selected(radical)
