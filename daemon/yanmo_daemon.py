"""
YanMo IME (言墨输入法) - System-Wide Desktop Daemon.
Runs in background on Linux Mint (Cinnamon / X11) to provide global Chinese typing,
5-stroke radical touch panel, Push-To-Talk offline voice dictation, and system tray.
"""

import ast
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gtk, GLib

from core.engine import YanMoEngine
from core.models import InputMode
from ui.candidate_window import CandidateWindow
from ui.injector import TextInjector
from .keyboard_grabber import KeyboardGrabber
from .tray_indicator import TrayIndicator
from .window_tracker import WindowTracker


PID_DIR = Path.home() / ".local" / "share" / "yanmo"
PID_FILE = PID_DIR / "daemon.pid"


class YanMoDaemon:
    def __init__(self):
        PID_DIR.mkdir(parents=True, exist_ok=True)

        self.engine = YanMoEngine()
        self.injector = TextInjector()
        self.window_tracker = WindowTracker()

        self.is_chinese_mode = True

        # 1. Floating Candidate Window
        self.candidate_window = CandidateWindow(
            engine=self.engine,
            on_commit=self._on_commit_text
        )

        # 2. System Tray
        self.tray = TrayIndicator(
            on_toggle_mode=self.toggle_mode,
            on_open_voice=self.trigger_voice,
            on_open_picker=self.open_radical_picker,
            on_export_dict=self.export_user_dict,
            on_toggle_autostart=self.toggle_autostart,
            on_exit=self.stop
        )

        # 3. Global Keyboard Grabber
        self.grabber = KeyboardGrabber(
            on_key_event=self._on_key_event,
            on_mode_toggle=self.toggle_mode,
            on_voice_toggle=self._on_voice_toggle,
            on_panic_exit=self.panic_stop
        )

    def start(self):
        """Start daemon loop and register signal handlers."""
        self._write_pid()
        ensure_desktop_shortcut()

        # Handle termination signals
        signal.signal(signal.SIGINT, lambda s, f: self.stop())
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())

        # Start keyboard interception
        self.grabber.set_chinese_mode(self.is_chinese_mode)
        self.grabber.start()

        # Start GTK event loop
        Gtk.main()

    def panic_stop(self):
        """Emergency stop triggered by global panic hotkey (Ctrl+Alt+Escape)."""
        print("[YanMo] 🛑 收到全局紧急关闭快捷键 (Ctrl+Alt+Escape)，正在终止输入法守护进程...")
        try:
            subprocess.run([
                "notify-send", "-t", "2500", "-i", "input-keyboard",
                "言墨输入法", "🛑 已强制关闭后台守护进程 (Ctrl+Alt+Esc)"
            ], check=False)
        except Exception:
            pass
        self.stop()

    def stop(self):
        """Clean shutdown of daemon."""
        self.grabber.stop()
        self._remove_pid()
        Gtk.main_quit()

    def _write_pid(self):
        PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

    def _remove_pid(self):
        if PID_FILE.exists():
            try:
                PID_FILE.unlink()
            except Exception:
                pass

    def toggle_mode(self):
        """Toggle Chinese / English input mode (Ctrl+Space)."""
        self.is_chinese_mode = not self.is_chinese_mode
        self.engine.reset()
        self.candidate_window.hide()
        self.grabber.set_chinese_mode(self.is_chinese_mode)
        self.grabber.set_composing(False)
        self.tray.set_chinese_mode(self.is_chinese_mode)

    def trigger_voice(self):
        """Manually toggle voice dictation."""
        if not self.engine.voice_engine.is_recording:
            self._position_candidate_window()
            self.candidate_window.start_voice_recording()
        else:
            self.candidate_window.stop_voice_recording(callback=self._on_commit_text)

    def open_radical_picker(self):
        """Open radical picker panel programmatically."""
        self._position_candidate_window()
        self.candidate_window.show_radical_picker()

    def export_user_dict(self):
        """Export learned user dictionary to Downloads or Home folder."""
        dest = Path.home() / "yanmo_user_dict.tsv"
        count = self.engine.pinyin_matcher.user_dict.export_tsv(dest)
        print(f"[YanMo Daemon] Exported {count} words to {dest}")

    def toggle_autostart(self) -> bool:
        """Toggle desktop autostart entry."""
        autostart_dir = Path.home() / ".config" / "autostart"
        autostart_dir.mkdir(parents=True, exist_ok=True)
        desktop_file = autostart_dir / "yanmo.desktop"

        if desktop_file.exists():
            desktop_file.unlink()
            return False
        else:
            repo_root = Path(__file__).resolve().parent.parent
            script_path = repo_root / "bin" / "yanmo-daemon"
            content = f"""[Desktop Entry]
Type=Application
Name=YanMo IME Daemon
Comment=言墨输入法全局后台守护进程
Exec={script_path} start
Icon=accessories-character-map
Terminal=false
Categories=Utility;InputMethod;
StartupNotify=false
X-GNOME-Autostart-enabled=true
"""
            desktop_file.write_text(content, encoding="utf-8")
            return True

    def _position_candidate_window(self):
        """Position candidate window near active caret or window."""
        self.last_target_window_id = self.window_tracker.get_active_window_id()
        x, y = self.window_tracker.calculate_candidate_position()
        self.candidate_window.move(x, y)

    def _on_key_event(self, key_name: str, is_press: bool):
        """Process intercepted keyboard event from grabber."""
        if not self.is_chinese_mode:
            return

        # If entering composition, position candidate bar near active window
        was_idle = (self.engine.state.mode == InputMode.IDLE and not self.engine.state.pinyin_buffer)
        if was_idle:
            self._position_candidate_window()

        if key_name in ("Tab", "`") and self.engine.state.mode == InputMode.COMPOSING:
            self.candidate_window.show_radical_picker()

        consumed = self.engine.feed_key(key_name)
        self.candidate_window.update_from_engine()

        # Update grabber composing state
        is_composing = bool(
            self.engine.state.pinyin_buffer or 
            self.engine.state.radical_buffer or 
            self.engine.state.candidates
        )
        self.grabber.set_composing(is_composing)

    def _on_voice_toggle(self, is_starting: bool):
        """Triggered by Push-To-Talk (v+Space hold and release)."""
        if is_starting:
            # Clear initial 'v' from engine state if any
            if self.engine.state.pinyin_buffer == "v":
                self.engine.reset()
            self._position_candidate_window()
            self.candidate_window.start_voice_recording()
        else:
            self.candidate_window.stop_voice_recording(callback=self._on_commit_text)

    def _on_commit_text(self, text: str):
        """Commit confirmed text into the active window."""
        if not text:
            return
        target_win = getattr(self, "last_target_window_id", None) or self.window_tracker.get_active_window_id()
        # 1. Hide candidate window and release compose grab immediately
        self.candidate_window.hide()
        self.grabber.set_composing(False)
        # 2. Inject text into target window
        self.injector.inject_text(text, target_window_id=target_win)


def ensure_desktop_shortcut():
    """Ensure Cinnamon global shortcut for one-key force start/stop toggle is registered."""
    try:
        res = subprocess.check_output(
            ["gsettings", "get", "org.cinnamon.desktop.keybindings", "custom-list"],
            encoding="utf-8"
        ).strip()
        lst = ast.literal_eval(res)
        if "custom-yanmo" not in lst:
            lst.append("custom-yanmo")
            subprocess.run(["gsettings", "set", "org.cinnamon.desktop.keybindings", "custom-list", str(lst)], check=False)

        path = "org.cinnamon.desktop.keybindings.custom-keybinding:/org/cinnamon/desktop/keybindings/custom-keybindings/custom-yanmo/"
        subprocess.run(["gsettings", "set", path, "name", "言墨输入法一键启停"], check=False)
        cmd_path = str(Path.home() / ".local" / "bin" / "yanmo-daemon")
        subprocess.run(["gsettings", "set", path, "command", f"{cmd_path} toggle"], check=False)
        subprocess.run(["gsettings", "set", path, "binding", "['<Primary><Alt>Escape', '<Super>y']"], check=False)
    except Exception:
        pass


def get_running_pid() -> Optional[int]:
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text(encoding="utf-8").strip())
            # Check if process is alive
            os.kill(pid, 0)
            return pid
        except (ValueError, OSError):
            pass
    return None


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "run"

    if action in ("--start", "start"):
        pid = get_running_pid()
        if pid:
            print(f"言墨守护进程已在运行中 (PID: {pid})")
            sys.exit(0)
        print("🚀 启动言墨输入法守护进程 (YanMo Daemon)...")
        daemon = YanMoDaemon()
        daemon.start()

    elif action in ("--stop", "stop"):
        pid = get_running_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"已停止言墨守护进程 (PID: {pid})")
            except OSError as e:
                print(f"停止失败: {e}")
        else:
            print("言墨守护进程未在运行。")

    elif action in ("--toggle", "toggle"):
        pid = get_running_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"🛑 已强制关闭言墨守护进程 (PID: {pid})")
                subprocess.run([
                    "notify-send", "-t", "2000", "-i", "input-keyboard",
                    "言墨输入法", "🛑 已强制关闭后台守护进程"
                ], check=False)
            except OSError as e:
                print(f"关闭失败: {e}")
        else:
            print("🚀 正在强制启动言墨守护进程...")
            repo_root = Path(__file__).resolve().parent.parent
            script_path = repo_root / "bin" / "yanmo-daemon"
            subprocess.run([str(script_path), "start"], check=False)
            subprocess.run([
                "notify-send", "-t", "2000", "-i", "accessories-character-map",
                "言墨输入法", "🚀 言墨输入法已强制启动"
            ], check=False)

    elif action in ("--register-shortcut", "register-shortcut"):
        ensure_desktop_shortcut()
        print("✅ 已成功注册 Linux Mint / Cinnamon 全局快捷键：")
        print("   - Ctrl + Alt + Escape")
        print("   - Win(Super) + Y")
        print("   按下上述任意快捷键即可一键强制启动/关闭言墨输入法。")

    elif action in ("--status", "status"):
        pid = get_running_pid()
        if pid:
            print(f"🟢 言墨守护进程正常运行中 (PID: {pid})")
        else:
            print("⚪ 言墨守护进程未运行。")

    elif action in ("--restart", "restart"):
        pid = get_running_pid()
        if pid:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
        daemon = YanMoDaemon()
        daemon.start()

    else:
        # Default foreground run
        daemon = YanMoDaemon()
        daemon.start()


if __name__ == "__main__":
    main()
