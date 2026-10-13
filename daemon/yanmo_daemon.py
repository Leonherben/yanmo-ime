"""
YanMo IME (言墨输入法) - System-Wide Desktop Daemon.
Runs in background on Linux Mint (Cinnamon / X11) to provide global Chinese typing,
C++20 high-performance engine, WeChat-style candidate window, tray menu, and settings.
"""

import ast
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GLib", "2.0")
gi.require_version("Gio", "2.0")
import json
from gi.repository import Gtk, GLib, Gio

from core.cpp_engine import YanMoCppEngine
from core.user_dict import UserDictionary
from ui.candidate_window import CandidateWindow
from ui.settings_window import SettingsWindow
from ui.injector import TextInjector
from .keyboard_grabber import KeyboardGrabber
from .tray_indicator import TrayIndicator
from .window_tracker import WindowTracker


PID_DIR = Path.home() / ".local" / "share" / "yanmo"
PID_FILE = PID_DIR / "daemon.pid"

_FALLBACK_CHAR_MAP = None

def _get_fallback_char_map() -> dict:
    global _FALLBACK_CHAR_MAP
    if _FALLBACK_CHAR_MAP is not None:
        return _FALLBACK_CHAR_MAP

    char_map = {
        "系": "xi", "地": "de", "着": "zhe", "得": "de",
        "长": "chang", "乐": "le", "重": "zhong", "行": "xing",
        "便": "bian", "强": "qiang", "发": "fa", "差": "cha",
        "入": "ru"
    }
    core_lex_path = Path(__file__).resolve().parent.parent / "data" / "dict" / "core_lexicon.tsv"
    if core_lex_path.exists():
        try:
            with open(core_lex_path, "r", encoding="utf-8", errors="ignore") as clf:
                for cl in clf:
                    cp = cl.strip().split("\t")
                    if len(cp) >= 2 and len(cp[0]) == 1 and cp[0] not in char_map:
                        char_map[cp[0]] = cp[1]
        except Exception:
            pass
    _FALLBACK_CHAR_MAP = char_map
    return _FALLBACK_CHAR_MAP


class YanMoDaemon:
    def __init__(self):
        PID_DIR.mkdir(parents=True, exist_ok=True)

        self.user_dict = UserDictionary()
        self.engine = YanMoCppEngine()
        self.injector = TextInjector()
        self.window_tracker = WindowTracker()

        self.is_chinese_mode = True
        self.is_chinese_punct = True
        self.is_full_width = False
        self.settings_window: Optional[SettingsWindow] = None
        self.last_target_window_id = None

        self.engine.set_full_width_punct(self.is_chinese_punct)
        self.engine.set_full_width_char(self.is_full_width)

        # 1. Floating Candidate Window
        self.candidate_window = CandidateWindow(
            engine=self.engine,
            on_commit=self._on_commit_text,
            on_open_settings=self.open_settings,
            on_user_dragged=self._on_candidate_window_dragged
        )
        self.injector.use_clipboard = self.candidate_window.config.get("use_clipboard_injection", True)

        # 2. System Tray Indicator
        self.tray = TrayIndicator(
            on_toggle_mode=self.toggle_mode,
            on_toggle_punct=self.toggle_punct,
            on_toggle_fullwidth=self.toggle_fullwidth,
            on_open_settings=self.open_settings,
            on_toggle_autostart=self.toggle_autostart,
            on_restart=self.restart,
            on_exit=self.stop
        )

        # 3. Global Keyboard Grabber
        self.grabber = KeyboardGrabber(
            on_key_event=self._on_key_event,
            on_mode_toggle=self.toggle_mode,
            on_punct_toggle=self.toggle_punct,
            on_fullwidth_toggle=self.toggle_fullwidth,
            on_voice_toggle=self._on_voice_toggle,
            on_panic_exit=self.panic_stop
        )

        # 4. Config File Auto-Reload Monitor
        self._init_config_monitor()

    def _init_config_monitor(self):
        config_path = Path.home() / ".config" / "yanmo" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if not config_path.exists():
            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(self.candidate_window.config, f, indent=2)
            except Exception:
                pass
        try:
            config_file = Gio.File.new_for_path(str(config_path))
            self.file_monitor = config_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
            self.file_monitor.connect("changed", self._on_config_file_changed)
        except Exception as e:
            print("[YanMo] Config file monitor error:", e)

    def _on_config_file_changed(self, monitor, file, other_file, event_type):
        if event_type in (Gio.FileMonitorEvent.CHANGED, Gio.FileMonitorEvent.CHANGES_DONE_HINT):
            GLib.idle_add(self._reload_config_from_disk)

    def _reload_config_from_disk(self):
        cfg_path = Path.home() / ".config" / "yanmo" / "config.json"
        if cfg_path.exists():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.candidate_window.apply_config(cfg)
            except Exception:
                pass

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
        print("[YanMo] 收到全局紧急关闭快捷键 (Ctrl+Alt+Escape)，正在终止守护进程...")
        try:
            self._remove_pid()
        except Exception:
            pass
        try:
            subprocess.run([
                "notify-send", "-t", "2500", "-i", "input-keyboard",
                "言墨输入法", "已强制关闭后台守护进程 (Ctrl+Alt+Esc)"
            ], check=False)
        except Exception:
            pass
        os._exit(0)

    def stop(self):
        """Clean shutdown of daemon."""
        self.grabber.stop()
        self._remove_pid()
        Gtk.main_quit()

    def restart(self):
        """Restart daemon process."""
        print("[YanMo] 正在重启守护进程...")
        self.stop()
        repo_root = Path(__file__).resolve().parent.parent
        script_path = repo_root / "bin" / "yanmo-daemon"
        subprocess.Popen([str(script_path), "start"])

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

    def _on_candidate_window_dragged(self, x: int, y: int):
        """Record candidate window user dragged position for future placement."""
        self.window_tracker.set_user_offset(x, y, window_id=self.last_target_window_id)

    def toggle_punct(self):
        """Toggle Chinese / English punctuation mode (Ctrl+.)."""
        self.is_chinese_punct = not self.is_chinese_punct
        self.engine.set_full_width_punct(self.is_chinese_punct)
        self.grabber.set_chinese_punct(self.is_chinese_punct)
        self.tray.set_chinese_punct(self.is_chinese_punct)
        punct_str = "中文标点" if self.is_chinese_punct else "英文/半角标点"
        try:
            subprocess.run([
                "notify-send", "-t", "1500", "-i", "accessories-character-map",
                "言墨输入法", f"已切换标点：{punct_str} (Ctrl+.)"
            ], check=False)
        except Exception:
            pass

    def toggle_fullwidth(self):
        """Toggle Full-width / Half-width character mode (Shift+Space)."""
        self.is_full_width = not self.is_full_width
        self.engine.set_full_width_char(self.is_full_width)
        self.grabber.set_full_width(self.is_full_width)
        self.tray.set_full_width(self.is_full_width)
        mode_str = "全角字符" if self.is_full_width else "半角字符"
        try:
            subprocess.run([
                "notify-send", "-t", "1500", "-i", "accessories-character-map",
                "言墨输入法", f"已切换字符：{mode_str} (Shift+Space)"
            ], check=False)
        except Exception:
            pass

    def open_settings(self, tab: str = "appearance"):
        """Open settings window with requested tab."""
        if not self.settings_window:
            self.settings_window = SettingsWindow(
                on_config_changed=self._on_config_changed,
                on_lexicon_updated=self._on_lexicon_updated,
            )
            self.settings_window.connect("delete-event", self._on_settings_closed)
        self.settings_window.switch_to_tab(tab)
        self.settings_window.present()

    def _on_lexicon_updated(self):
        """Hot-reload user lexicon into active C++ engine without restarting."""
        user_dict_tsv = Path.home() / ".local" / "share" / "yanmo" / "user_dict.tsv"
        if user_dict_tsv.exists():
            self.engine.load_user_dict(str(user_dict_tsv))

    def _on_settings_closed(self, win, event):
        win.hide()
        return True

    def _on_config_changed(self, cfg: dict):
        """Callback when user edits appearance or behavior in settings."""
        self.candidate_window.apply_config(cfg)
        if "use_clipboard_injection" in cfg:
            self.injector.use_clipboard = bool(cfg["use_clipboard_injection"])

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

    def _on_key_event(self, key_name: str, is_press: bool = True, is_shift: bool = False, keycode: Optional[int] = None):
        """Process intercepted keyboard event from grabber."""
        if not self.is_chinese_mode:
            return

        status_before = self.engine.get_status()
        was_idle = (status_before["mode"] == "IDLE" and not status_before["pinyin_buffer"])
        if was_idle:
            self._position_candidate_window()
        else:
            # Dynamically follow moving caret in AT-SPI enabled apps
            if self.window_tracker.get_caret_position():
                self._position_candidate_window()

        consumed = self.engine.feed_key(key_name, is_shift=is_shift)
        self.candidate_window.update_from_engine()

        # Update grabber composing state
        status_after = self.engine.get_status()
        is_composing = bool(
            status_after["mode"] != "IDLE" or 
            status_after["pinyin_buffer"] or 
            status_after["total_candidates"] > 0
        )
        self.grabber.set_composing(is_composing)

        # P1-1: If key was not consumed by engine, reinject it to active window via XTEST
        if not consumed:
            target_win = self.last_target_window_id or self.window_tracker.get_active_window_id()
            self.grabber.suspend_grabs()
            try:
                self.injector.inject_key(key_name, is_shift=is_shift, keycode=keycode, target_window_id=target_win)
            finally:
                self.grabber.resume_grabs()

    def _on_voice_toggle(self, is_starting: bool):
        """Triggered by Push-To-Talk (v+Space hold and release)."""
        if is_starting:
            if self.engine.get_buffer() == "v":
                self.engine.reset()
            self._position_candidate_window()
            self.candidate_window.set_voice_recording(True)
            if hasattr(self.engine, "start_voice_recording"):
                self.engine.start_voice_recording()
        else:
            self.candidate_window.set_voice_recording(False)
            if hasattr(self.engine, "stop_voice_recording"):
                def _async_voice_decode():
                    try:
                        text = self.engine.stop_voice_recording()
                        if text:
                            GLib.idle_add(lambda: self._on_commit_text(text))
                    except Exception as ex:
                        print(f"[Daemon] Async voice transcription error: {ex}")

                threading.Thread(target=_async_voice_decode, daemon=True).start()

    def _on_commit_text(self, text: str):
        """Commit confirmed text into the active window."""
        if not text:
            return

        # P1-2: Always obtain the active window at the exact moment of commitment
        current_focus = self.window_tracker.get_active_window_id()
        target_win = current_focus or self.last_target_window_id
        self.last_target_window_id = None

        # P1-2 & P1-4: Check if target window is a password dialog
        is_password = self.injector.is_window_password(target_win)
        if is_password:
            print(f"[Daemon] Security warning: Target window {target_win} is a password/auth dialog. Text injection ABORTED.")
            self.grabber.set_composing(False)
            self.candidate_window.show_security_blocked(text)
            return

        # Only record words containing Chinese characters and when self-learning is enabled
        if self.candidate_window.config.get("self_learning", True) and any('\u4e00' <= ch <= '\u9fff' for ch in text):
            try:
                py = ""
                try:
                    from pypinyin import lazy_pinyin
                    py = "".join(lazy_pinyin(text))
                except Exception:
                    pass
                if not py:
                    char_map = _get_fallback_char_map()
                    py = "".join(char_map.get(ch, "") for ch in text)
                if py and py != text:
                    self.user_dict.record_selection(text, py)
                    self.user_dict.sync_to_tsv()
                    self._on_lexicon_updated()
                    if hasattr(self.engine, "save_user_bigram"):
                        self.engine.save_user_bigram()
            except Exception:
                pass

        self.candidate_window.hide()
        self.grabber.set_composing(False)
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
        print("启动言墨输入法守护进程 (YanMo Daemon)...")
        daemon = YanMoDaemon()
        daemon.start()

    elif action in ("--stop", "stop"):
        pid = get_running_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                # P1-3: Wait briefly; if process doesn't terminate, fallback to SIGKILL (kill -9)
                for _ in range(10):
                    time.sleep(0.05)
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        break
                else:
                    try:
                        os.kill(pid, signal.SIGKILL)
                        print(f"守护进程未响应 SIGTERM，已强制杀除 (SIGKILL PID: {pid})")
                    except OSError:
                        pass
                print(f"已停止言墨守护进程 (PID: {pid})")
            except OSError as e:
                print(f"停止失败: {e}")
        subprocess.run(["pkill", "-9", "-f", "daemon.yanmo_daemon run"], check=False)
        if PID_FILE.exists():
            try:
                PID_FILE.unlink()
            except Exception:
                pass

    elif action in ("--toggle", "toggle"):
        pid = get_running_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                for _ in range(10):
                    time.sleep(0.05)
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        break
                else:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except OSError:
                        pass
                print(f"已强制关闭言墨守护进程 (PID: {pid})")
                subprocess.run([
                    "notify-send", "-t", "2000", "-i", "input-keyboard",
                    "言墨输入法", "已强制关闭后台守护进程"
                ], check=False)
            except OSError as e:
                print(f"关闭失败: {e}")
        else:
            print("正在强制启动言墨守护进程...")
            repo_root = Path(__file__).resolve().parent.parent
            script_path = repo_root / "bin" / "yanmo-daemon"
            subprocess.run([str(script_path), "start"], check=False)
            subprocess.run([
                "notify-send", "-t", "2000", "-i", "accessories-character-map",
                "言墨输入法", "言墨输入法已强制启动"
            ], check=False)

    elif action in ("--register-shortcut", "register-shortcut"):
        ensure_desktop_shortcut()
        print("已成功注册 Linux Mint / Cinnamon 全局快捷键：")
        print("   - Ctrl + Alt + Escape")
        print("   - Win(Super) + Y")
        print("   按下上述任意快捷键即可一键强制启动/关闭言墨输入法。")

    elif action in ("--status", "status"):
        pid = get_running_pid()
        if pid:
            print(f"言墨守护进程正常运行中 (PID: {pid})")
        else:
            print("言墨守护进程未运行。")

    elif action in ("--settings", "settings", "config", "--config"):
        tab = sys.argv[2] if len(sys.argv) > 2 else "appearance"
        win = SettingsWindow()
        win.connect("destroy", Gtk.main_quit)
        win.switch_to_tab(tab)
        win.show_all()
        Gtk.main()

    elif action in ("--restart", "restart"):
        pid = get_running_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
            time.sleep(0.5)
        daemon = YanMoDaemon()
        daemon.start()

    else:
        daemon = YanMoDaemon()
        daemon.start()


if __name__ == "__main__":
    main()
