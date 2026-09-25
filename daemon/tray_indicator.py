"""
Linux Mint System Tray Indicator for YanMo IME Daemon.
Uses Gtk.StatusIcon to display active status (Chinese/English) and provides quick settings menu.
"""

from pathlib import Path
from typing import Callable, Optional
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class TrayIndicator:
    def __init__(
        self,
        on_toggle_mode: Optional[Callable[[], None]] = None,
        on_open_voice: Optional[Callable[[], None]] = None,
        on_open_picker: Optional[Callable[[], None]] = None,
        on_export_dict: Optional[Callable[[], None]] = None,
        on_toggle_autostart: Optional[Callable[[], bool]] = None,
        on_exit: Optional[Callable[[], None]] = None,
    ):
        self.on_toggle_mode = on_toggle_mode
        self.on_open_voice = on_open_voice
        self.on_open_picker = on_open_picker
        self.on_export_dict = on_export_dict
        self.on_toggle_autostart = on_toggle_autostart
        self.on_exit = on_exit

        self.is_chinese_mode = True

        self.status_icon = Gtk.StatusIcon()
        self.status_icon.set_from_icon_name("accessories-character-map")
        self.status_icon.set_tooltip_text("言墨输入法 - 中文")
        self.status_icon.set_visible(True)

        self.status_icon.connect("activate", self._on_left_click)
        self.status_icon.connect("popup-menu", self._on_right_click)

    def set_chinese_mode(self, enabled: bool):
        """Update tray tooltip and icon reflecting current state."""
        self.is_chinese_mode = enabled
        if enabled:
            self.status_icon.set_tooltip_text("言墨输入法 - 中文 (Ctrl+Space切换)")
            self.status_icon.set_from_icon_name("accessories-character-map")
        else:
            self.status_icon.set_tooltip_text("言墨输入法 - 英文 (Ctrl+Space切换)")
            self.status_icon.set_from_icon_name("input-keyboard")

    def _on_left_click(self, icon):
        """Left click toggles Chinese / English."""
        if self.on_toggle_mode:
            self.on_toggle_mode()

    def _on_right_click(self, icon, button, activate_time):
        """Right click shows context menu."""
        menu = Gtk.Menu()

        # 1. Mode Item
        mode_text = "切换为 [英文模式]" if self.is_chinese_mode else "切换为 [中文模式]"
        item_mode = Gtk.MenuItem(label=f"🌐 {mode_text}")
        if self.on_toggle_mode:
            item_mode.connect("activate", lambda w: self.on_toggle_mode())
        menu.append(item_mode)

        # 2. Voice Dictation
        item_voice = Gtk.MenuItem(label="🎙️ 离线语音听写 (v+空格长按)")
        if self.on_open_voice:
            item_voice.connect("activate", lambda w: self.on_open_voice())
        menu.append(item_voice)

        # 3. Radical Picker
        item_picker = Gtk.MenuItem(label="📌 五笔画部首全景面板")
        if self.on_open_picker:
            item_picker.connect("activate", lambda w: self.on_open_picker())
        menu.append(item_picker)

        menu.append(Gtk.SeparatorMenuItem())

        # 4. Export Dictionary
        item_export = Gtk.MenuItem(label="📚 导出自学词库 (TSV)")
        if self.on_export_dict:
            item_export.connect("activate", lambda w: self.on_export_dict())
        menu.append(item_export)

        # 5. Autostart Setting
        item_autostart = Gtk.CheckMenuItem(label="⚙️ 开机自动启动")
        autostart_path = Path.home() / ".config" / "autostart" / "yanmo.desktop"
        item_autostart.set_active(autostart_path.exists())
        if self.on_toggle_autostart:
            item_autostart.connect("toggled", lambda w: self.on_toggle_autostart())
        menu.append(item_autostart)

        menu.append(Gtk.SeparatorMenuItem())

        # 6. Exit
        item_exit = Gtk.MenuItem(label="❌ 退出言墨守护进程")
        if self.on_exit:
            item_exit.connect("activate", lambda w: self.on_exit())
        menu.append(item_exit)

        menu.show_all()
        menu.popup(None, None, Gtk.StatusIcon.position_menu, self.status_icon, button, activate_time)
