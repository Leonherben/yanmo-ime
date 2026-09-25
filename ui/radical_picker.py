"""
Radical Picker Panel for YanMo IME (言墨输入法).
Visual touch/click panel for selecting radicals and components.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from typing import Callable, Optional

# Curated common radicals grouped by stroke count
COMMON_RADICAL_GROUPS = [
    ("1-2 画", ["一", "丨", "丿", "丶", "乙", "冫", "人", "亻", "几", "刀", "刂", "力", "十", "卜", "厂", "又"]),
    ("3 画", ["口", "囗", "土", "士", "夕", "大", "女", "子", "宀", "寸", "小", "山", "巾", "广", "弓", "彳", "心", "忄", "扌", "氵", "艹"]),
    ("4 画", ["木", "欠", "止", "气", "水", "火", "灬", "爪", "父", "牛", "牜", "犬", "犭", "王", "田", "皿", "目", "石", "示", "礻", "禾", "穴", "立"]),
    ("5+ 画", ["⺮", "米", "纟", "耳", "舟", "虫", "衣", "衤", "讠", "走", "辶", "钅", "门", "雨", "饣", "马", "鸟"]),
]


class RadicalPickerPanel(Gtk.Box):
    def __init__(self, on_selected: Optional[Callable[[str], None]] = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.get_style_context().add_class("yanmo-radical-panel")
        self.on_selected = on_selected
        self.set_can_focus(False)

        self._build_ui()
        self.show_all()

    def _build_ui(self):
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        lbl_title = Gtk.Label(label="📌 常用部首速查 (点击/触碰直接查字或过滤)")
        lbl_title.get_style_context().add_class("yanmo-rad-group-label")
        title_box.pack_start(lbl_title, False, False, 0)
        self.pack_start(title_box, False, False, 0)

        for group_name, rad_list in COMMON_RADICAL_GROUPS:
            group_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

            # Header
            lbl_group = Gtk.Label(label=group_name)
            lbl_group.set_xalign(0.0)
            lbl_group.get_style_context().add_class("yanmo-rad-group-label")
            group_box.pack_start(lbl_group, False, False, 0)

            # Flow / Grid of buttons
            flow_box = Gtk.FlowBox()
            flow_box.set_can_focus(False)
            flow_box.set_selection_mode(Gtk.SelectionMode.NONE)
            flow_box.set_max_children_per_line(12)
            flow_box.set_min_children_per_line(6)
            flow_box.set_row_spacing(2)
            flow_box.set_column_spacing(2)

            for rad in rad_list:
                btn = Gtk.Button(label=rad)
                btn.set_can_focus(False)
                btn.set_focus_on_click(False)
                btn.get_style_context().add_class("yanmo-rad-chip")
                btn.connect("clicked", self._on_button_clicked, rad)
                flow_box.add(btn)

            group_box.pack_start(flow_box, False, False, 0)
            self.pack_start(group_box, False, False, 0)

    def _on_button_clicked(self, button, radical: str):
        if self.on_selected:
            self.on_selected(radical)
