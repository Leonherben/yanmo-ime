#!/usr/bin/env python3
"""
言墨输入法 (YanMo IME) - Linux Mint 桌面端体验器与悬浮候选窗口
提供桌面悬浮输入条、右上角部首速查触控面板以及原生 GTK 3 测试沙盒。
"""

import sys
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from core.engine import YanMoEngine
from core.models import InputMode
from ui.candidate_window import CandidateWindow
from ui.injector import TextInjector


class YanMoDesktopApp:
    def __init__(self):
        self.engine = YanMoEngine()
        self.injector = TextInjector()

        # Build Candidate Floating Window
        self.candidate_window = CandidateWindow(
            engine=self.engine,
            on_commit=self._on_commit_text
        )

        # Build Interactive Testing Sandbox Window
        self.sandbox_window = Gtk.Window(title="言墨输入法 (YanMo IME) - 桌面测试沙盒")
        self.sandbox_window.set_default_size(680, 420)
        self.sandbox_window.set_position(Gtk.WindowPosition.CENTER)
        self.sandbox_window.connect("destroy", Gtk.main_quit)

        self._build_sandbox_ui()
        self._position_candidate_bar()

    def _build_sandbox_ui(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_border_width(16)
        self.sandbox_window.add(vbox)

        # Header Info
        lbl_title = Gtk.Label()
        lbl_title.set_markup("<span size='x-large' weight='bold' color='#2563eb'>🖋️ 言墨输入法 (YanMo IME) 桌面体验沙盒</span>")
        lbl_title.set_xalign(0.0)
        vbox.pack_start(lbl_title, False, False, 0)

        lbl_desc = Gtk.Label()
        lbl_desc.set_markup(
            "<b>功能特性体验指南:</b>\n"
            " • <b>键盘常规输入</b>：在下方文本框中聚焦后，敲击拼音（如 <tt>he</tt>、<tt>yanmo</tt>），悬浮候选条实时跟随。\n"
            " • <b>Tab 键部首筛选</b>：输入拼音后，轻按 <b>Tab</b> 键，输入部首拼音（如 <tt>shui</tt>）精准过滤。\n"
            " • <b>触屏/鼠标视觉流</b>：点击悬浮框右上角 <b>[部首 ▾]</b> 按钮，可直接点击/触控点选偏旁部首！\n"
            " • <b>选词上屏与自学习</b>：按 <b>空格</b> 或 <b>数字键 1-9</b>，字符上屏并自动记录至个人词库。"
        )
        lbl_desc.set_xalign(0.0)
        lbl_desc.set_line_wrap(True)
        vbox.pack_start(lbl_desc, False, False, 0)

        # Interactive Text Area
        frame = Gtk.Frame(label=" 📝 实时打字测试区 (请在此敲击键盘体验) ")
        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.text_view.set_border_width(8)
        self.text_buffer = self.text_view.get_buffer()
        self.text_buffer.set_text("言墨输入法就绪。请直接在此键入拼音测试...\n\n")

        # Key press interception on sandbox
        self.text_view.connect("key-press-event", self._on_key_press)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(180)
        scrolled.add(self.text_view)
        frame.add(scrolled)
        vbox.pack_start(frame, True, True, 0)

        # Action Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_demo = Gtk.Button(label="⚡ 自动打字演示 (Demo)")
        btn_demo.connect("clicked", self._trigger_auto_demo)
        btn_box.pack_start(btn_demo, False, False, 0)

        btn_clear = Gtk.Button(label="清空测试区")
        btn_clear.connect("clicked", lambda b: self.text_buffer.set_text(""))
        btn_box.pack_start(btn_clear, False, False, 0)

        self.lbl_status = Gtk.Label(label="词库状态: 正常 | 用户自学词: 已同步")
        btn_box.pack_end(self.lbl_status, False, False, 0)

        vbox.pack_start(btn_box, False, False, 0)

    def _position_candidate_bar(self):
        """Position candidate window relative to sandbox."""
        self.sandbox_window.show_all()
        # Initial placement below sandbox
        x, y = self.sandbox_window.get_position()
        w, h = self.sandbox_window.get_size()
        self.candidate_window.move(x + 40, y + h - 80)

    def _on_key_press(self, widget, event):
        """Intercept key events and route to YanMo engine."""
        keyval = event.keyval
        key_name = Gdk.keyval_name(keyval)

        # Mapping Gdk key names to YanMo engine keys
        engine_key = None
        if key_name in ("Tab", "ISO_Left_Tab"):
            engine_key = "Tab"
        elif key_name in ("grave", "asciitilde"):
            engine_key = "`"
        elif key_name in ("BackSpace", "Delete"):
            engine_key = "Backspace"
        elif key_name in ("Escape",):
            engine_key = "Escape"
        elif key_name in ("Return", "KP_Enter"):
            engine_key = " "
        elif key_name in ("space",):
            engine_key = " "
        elif key_name and len(key_name) == 1:
            engine_key = key_name

        if engine_key:
            consumed = self.engine.feed_key(engine_key)
            self.candidate_window.update_from_engine()

            # If the engine consumed the key, stop GTK default propagation
            if consumed:
                return True

        return False

    def _on_commit_text(self, text: str):
        """Called when a candidate is confirmed for commit."""
        # Insert directly into sandbox text buffer
        iter_end = self.text_buffer.get_end_iter()
        self.text_buffer.insert(iter_end, text)

        # Update status
        user_cnt = self.engine.pinyin_matcher.user_dict.count()
        self.lbl_status.set_text(f"已上屏: '{text}' | 📚 个人自学词库: {user_cnt} 条")

    def _trigger_auto_demo(self, button):
        """Simulate typing sequence in desktop environment."""
        demo_steps = [
            # Type 'he'
            ("h", 200), ("e", 200),
            # Press Tab
            ("Tab", 600),
            # Type 'shui' (water radical)
            ("s", 250), ("h", 250), ("u", 250), ("i", 300),
            # Select #1 (河)
            ("1", 500),
            # Type 'yanmo'
            ("y", 200), ("a", 200), ("n", 200), ("m", 200), ("o", 200),
            # Select space
            (" ", 500),
        ]

        def run_step(steps_left):
            if not steps_left:
                return False
            key, delay = steps_left[0]
            self.engine.feed_key(key)
            self.candidate_window.update_from_engine()
            if len(steps_left) > 1:
                GLib.timeout_add(delay, run_step, steps_left[1:])
            return False

        run_step(demo_steps)

    def run(self):
        Gtk.main()


def main():
    app = YanMoDesktopApp()
    app.run()


if __name__ == "__main__":
    main()
