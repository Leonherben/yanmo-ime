"""
Radical Picker Panel for YanMo IME (言墨输入法).
Categorized by 5 Basic Strokes (一横 丨竖 丿撇 丶点 乙折) + Keyboard H/S/P/D/Z mapping.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from typing import Callable, Dict, List, Optional

# Radicals categorized strictly by their first stroke (横、竖、撇、点、折)
STROKE_CATEGORIES = {
    "h": {
        "name": "一 横 (H)",
        "radicals": ["一", "十", "厂", "匚", "土", "士", "工", "干", "木", "寸", "王", "石", "车", "耳", "雨", "西", "革"]
    },
    "s": {
        "name": "丨 竖 (S)",
        "radicals": ["丨", "卜", "刂", "口", "囗", "山", "巾", "日", "目", "田", "皿", "虫", "止", "非", "齿", "骨"]
    },
    "p": {
        "name": "丿 撇 (P)",
        "radicals": ["丿", "人", "亻", "八", "几", "夕", "大", "女", "牛", "牜", "白", "禾", "竹", "⺮", "月", "舟", "金", "钅", "鸟", "鱼"]
    },
    "d": {
        "name": "丶 点 (D)",
        "radicals": ["丶", "冫", "氵", "广", "门", "宀", "穴", "心", "忄", "户", "文", "方", "火", "灬", "示", "礻", "衣", "衤", "言", "讠"]
    },
    "z": {
        "name": "乙 折 (Z)",
        "radicals": ["乙", "刀", "力", "又", "弓", "己", "子", "纟", "走", "辶", "阝", "马", "鬼"]
    }
}


class RadicalPickerPanel(Gtk.Box):
    def __init__(self, on_selected: Optional[Callable[[str], None]] = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.get_style_context().add_class("yanmo-radical-panel")
        self.on_selected = on_selected
        self.set_can_focus(False)

        self.current_stroke: Optional[str] = None
        self.tab_buttons: Dict[str, Gtk.Button] = {}
        self.group_boxes: Dict[str, Gtk.Box] = {}

        self._build_ui()
        self.show_all()

    def _build_ui(self):
        # 1. Header Bar with Tabs: [全部] [一 横 H] [丨 竖 S] [丿 撇 P] [丶 点 D] [乙 折 Z]
        tab_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        tab_bar.set_can_focus(False)

        btn_all = Gtk.Button(label="全部")
        btn_all.set_can_focus(False)
        btn_all.set_focus_on_click(False)
        btn_all.get_style_context().add_class("yanmo-rad-tab")
        btn_all.connect("clicked", lambda b: self.filter_by_stroke(None))
        tab_bar.pack_start(btn_all, False, False, 0)
        self.tab_buttons["all"] = btn_all

        for key, info in STROKE_CATEGORIES.items():
            btn = Gtk.Button(label=info["name"])
            btn.set_can_focus(False)
            btn.set_focus_on_click(False)
            btn.get_style_context().add_class("yanmo-rad-tab")
            btn.connect("clicked", lambda b, k=key: self.filter_by_stroke(k))
            tab_bar.pack_start(btn, False, False, 0)
            self.tab_buttons[key] = btn

        self.pack_start(tab_bar, False, False, 0)

        # 2. Content Area for Radicals
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self.content_box.set_can_focus(False)
        self.pack_start(self.content_box, False, False, 0)

        for key, info in STROKE_CATEGORIES.items():
            group_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            group_box.set_can_focus(False)

            # Flow grid for this stroke
            flow_box = Gtk.FlowBox()
            flow_box.set_can_focus(False)
            flow_box.set_selection_mode(Gtk.SelectionMode.NONE)
            flow_box.set_max_children_per_line(12)
            flow_box.set_min_children_per_line(6)
            flow_box.set_row_spacing(2)
            flow_box.set_column_spacing(2)

            for rad in info["radicals"]:
                btn_rad = Gtk.Button(label=rad)
                btn_rad.set_can_focus(False)
                btn_rad.set_focus_on_click(False)
                btn_rad.get_style_context().add_class("yanmo-rad-chip")
                btn_rad.connect("clicked", self._on_button_clicked, rad)
                flow_box.add(btn_rad)

            group_box.pack_start(flow_box, False, False, 0)
            self.group_boxes[key] = group_box
            self.content_box.pack_start(group_box, False, False, 0)

    def filter_by_stroke(self, stroke: Optional[str]):
        """Filter visible radicals by stroke key: 'h', 's', 'p', 'd', 'z' or None (All)."""
        self.current_stroke = stroke

        # Update tab active styles
        for key, btn in self.tab_buttons.items():
            ctx = btn.get_style_context()
            ctx.remove_class("active")
            if (stroke is None and key == "all") or (stroke == key):
                ctx.add_class("active")

        # Show/hide corresponding group boxes
        for key, box in self.group_boxes.items():
            if stroke is None or stroke == key:
                box.show_all()
            else:
                box.hide()

    def _on_button_clicked(self, button, radical: str):
        if self.on_selected:
            self.on_selected(radical)
