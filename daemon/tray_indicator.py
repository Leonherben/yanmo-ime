"""
Linux Mint System Tray Indicator for YanMo IME Daemon.
Uses AyatanaAppIndicator3 (native Linux Mint / Cinnamon StatusNotifierItem)
with graceful fallback to Gtk.StatusIcon, providing a pure-text menu without emojis.
"""

from pathlib import Path
from typing import Callable, Optional
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

HAS_APP_INDICATOR = False
try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3
    HAS_APP_INDICATOR = True
except Exception:
    pass


class TrayIndicator:
    def __init__(
        self,
        on_toggle_mode: Optional[Callable[[], None]] = None,
        on_toggle_punct: Optional[Callable[[], None]] = None,
        on_toggle_fullwidth: Optional[Callable[[], None]] = None,
        on_open_settings: Optional[Callable[[str], None]] = None,
        on_toggle_autostart: Optional[Callable[[], bool]] = None,
        on_restart: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
    ):
        self.on_toggle_mode = on_toggle_mode
        self.on_toggle_punct = on_toggle_punct
        self.on_toggle_fullwidth = on_toggle_fullwidth
        self.on_open_settings = on_open_settings
        self.on_toggle_autostart = on_toggle_autostart
        self.on_restart = on_restart
        self.on_exit = on_exit

        self.is_chinese_mode = True
        self.is_chinese_punct = True
        self.is_full_width = False
        self._updating_menu = False

        self.menu = self._build_menu()

        if HAS_APP_INDICATOR:
            self.indicator = AyatanaAppIndicator3.Indicator.new(
                "yanmo-ime",
                "accessories-character-map",
                AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS
            )
            self.indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
            self.indicator.set_title("言墨输入法")
            self.indicator.set_icon_full("accessories-character-map", "言墨输入法 - 中文")
            self.indicator.set_menu(self.menu)
            self.status_icon = None
        else:
            self.indicator = None
            self.status_icon = Gtk.StatusIcon()
            self.status_icon.set_from_icon_name("accessories-character-map")
            self.status_icon.set_tooltip_text("言墨输入法 - 中文")
            self.status_icon.set_visible(True)
            self.status_icon.connect("activate", self._on_status_icon_left_click)
            self.status_icon.connect("popup-menu", self._on_status_icon_right_click)

    def _build_menu(self) -> Gtk.Menu:
        menu = Gtk.Menu()

        # 1. Chinese Mode Toggle
        self.item_mode = Gtk.CheckMenuItem(label="中文模式 (Shift / Ctrl+Space)")
        self.item_mode.set_active(self.is_chinese_mode)
        self.item_mode.connect("toggled", self._on_mode_toggled)
        menu.append(self.item_mode)

        # 2. Chinese Punctuation Toggle
        self.item_punct = Gtk.CheckMenuItem(label="中文标点 (Ctrl+.)")
        self.item_punct.set_active(self.is_chinese_punct)
        self.item_punct.connect("toggled", self._on_punct_toggled)
        menu.append(self.item_punct)

        # 3. Full-width Characters Toggle
        self.item_fullwidth = Gtk.CheckMenuItem(label="全角字符 (Shift+Space)")
        self.item_fullwidth.set_active(self.is_full_width)
        self.item_fullwidth.connect("toggled", self._on_fullwidth_toggled)
        menu.append(self.item_fullwidth)

        menu.append(Gtk.SeparatorMenuItem())

        # 3. Settings Window
        item_settings = Gtk.MenuItem(label="设置...")
        if self.on_open_settings:
            item_settings.connect("activate", lambda w: self.on_open_settings("appearance"))
        menu.append(item_settings)

        # 4. Radical Dictionary Tool
        item_radical = Gtk.MenuItem(label="生僻字字典工具...")
        if self.on_open_settings:
            item_radical.connect("activate", lambda w: self.on_open_settings("radical"))
        menu.append(item_radical)

        # 5. Lexicon Management
        item_lexicon = Gtk.MenuItem(label="词库管理 (导入/导出)...")
        if self.on_open_settings:
            item_lexicon.connect("activate", lambda w: self.on_open_settings("lexicon"))
        menu.append(item_lexicon)

        menu.append(Gtk.SeparatorMenuItem())

        # 5. Autostart Setting
        self.item_autostart = Gtk.CheckMenuItem(label="开机自动启动")
        autostart_path = Path.home() / ".config" / "autostart" / "yanmo.desktop"
        self.item_autostart.set_active(autostart_path.exists())
        self.item_autostart.connect("toggled", self._on_autostart_toggled)
        menu.append(self.item_autostart)

        menu.append(Gtk.SeparatorMenuItem())

        # 6. Restart & Exit
        item_restart = Gtk.MenuItem(label="重启言墨服务")
        if self.on_restart:
            item_restart.connect("activate", lambda w: self.on_restart())
        menu.append(item_restart)

        item_exit = Gtk.MenuItem(label="退出言墨")
        if self.on_exit:
            item_exit.connect("activate", lambda w: self.on_exit())
        menu.append(item_exit)

        menu.show_all()
        return menu

    def _on_mode_toggled(self, widget):
        if self._updating_menu:
            return
        if self.on_toggle_mode:
            self.on_toggle_mode()

    def _on_punct_toggled(self, widget):
        if self._updating_menu:
            return
        if self.on_toggle_punct:
            self.on_toggle_punct()

    def _on_fullwidth_toggled(self, widget):
        if self._updating_menu:
            return
        if self.on_toggle_fullwidth:
            self.on_toggle_fullwidth()

    def _on_autostart_toggled(self, widget):
        if self._updating_menu:
            return
        if self.on_toggle_autostart:
            self.on_toggle_autostart()

    def set_chinese_mode(self, enabled: bool):
        """Update tray tooltip and icon reflecting current state."""
        self.is_chinese_mode = enabled
        icon_name = "accessories-character-map" if enabled else "input-keyboard"
        tooltip = "言墨输入法 - 中文 (Shift / Ctrl+Space)" if enabled else "言墨输入法 - 英文 (Shift / Ctrl+Space)"

        if self.indicator:
            self.indicator.set_icon_full(icon_name, tooltip)
        elif self.status_icon:
            self.status_icon.set_tooltip_text(tooltip)
            self.status_icon.set_from_icon_name(icon_name)

        if hasattr(self, "item_mode") and self.item_mode:
            self._updating_menu = True
            self.item_mode.set_active(enabled)
            self._updating_menu = False

    def set_chinese_punct(self, enabled: bool):
        self.is_chinese_punct = enabled
        if hasattr(self, "item_punct") and self.item_punct:
            self._updating_menu = True
            self.item_punct.set_active(enabled)
            self._updating_menu = False

    def set_full_width(self, enabled: bool):
        self.is_full_width = enabled
        if hasattr(self, "item_fullwidth") and self.item_fullwidth:
            self._updating_menu = True
            self.item_fullwidth.set_active(enabled)
            self._updating_menu = False

    def _on_status_icon_left_click(self, icon):
        if self.on_toggle_mode:
            self.on_toggle_mode()

    def _on_status_icon_right_click(self, icon, button, activate_time):
        self.menu.popup(None, None, Gtk.StatusIcon.position_menu, self.status_icon, button, activate_time)
