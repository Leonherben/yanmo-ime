#!/usr/bin/env python3
"""
言墨输入法 (YanMo IME) - 交互式体验终端 (支持 Phase 2 自学习词库)
支持拼音检索、Tab 键部首辅码过滤、数字选词、动态词频自学习演示。
"""

import sys
import tty
import termios
import time
from core.engine import YanMoEngine
from core.models import InputMode


def render_ui(engine: YanMoEngine, log_msg: str = ""):
    """Render the candidate bar and visual status in the terminal."""
    sys.stdout.write("\033[2J\033[H")  # Clear screen and move cursor to top
    print("=" * 68)
    print("   🖋️   言墨输入法 (YanMo IME) - 词库与部首检索交互终端")
    print("=" * 68)
    user_word_count = engine.pinyin_matcher.user_dict.count()
    print("【操作指引】")
    print(" • 输入拼音 (a-z) 检索词库")
    print(" • 按 [Tab] 或 [~] 键进入/退出【部首辅码过滤】")
    print(" • 按 [数字 1-9] 或 [空格] 选词上屏（系统会自动记忆并动态调整词频）")
    print(" • 按 [Backspace] 退格，按 [Esc] 或 [Ctrl+C] 退出")
    print(f" • 📚 用户自学词库: \033[1;36m{user_word_count}\033[0m 条已记录")
    print("-" * 68)

    # 1. Input status line
    state = engine.state
    if state.mode == InputMode.IDLE:
        mode_str = "\033[90m[空闲待机]\033[0m"
        buffer_str = "(等待敲击拼音...)"
    elif state.mode == InputMode.COMPOSING:
        mode_str = "\033[92m[拼音输入]\033[0m"
        buffer_str = f"\033[1m{state.pinyin_buffer}\033[0m"
    elif state.mode == InputMode.RADICAL_FILTER:
        mode_str = "\033[93m[部首筛选模式]\033[0m"
        rad_disp = state.radical_buffer if state.radical_buffer else "_"
        buffer_str = f"{state.pinyin_buffer} \033[1;33m[部首: {rad_disp}]\033[0m"

    print(f"当前状态: {mode_str}   编码: {buffer_str}   \033[36m[部首 ▾]\033[0m")
    print("-" * 68)

    # 2. Candidate bar
    print("候选词列表:")
    if state.candidates:
        cands_formatted = []
        for i, cand in enumerate(state.candidates[:9]):
            idx = i + 1
            if cand.comment == "自学词":
                cands_formatted.append(f"\033[1m{idx}.\033[0m{cand.text}\033[1;35m(★自学词)\033[0m")
            elif cand.comment:
                cands_formatted.append(f"\033[1m{idx}.\033[0m{cand.text}\033[90m({cand.comment})\033[0m")
            else:
                cands_formatted.append(f"\033[1m{idx}.\033[0m{cand.text}")
        print("  " + "   ".join(cands_formatted))
    else:
        if state.mode != InputMode.IDLE:
            print("  \033[90m(无匹配候选)\033[0m")
        else:
            print("  \033[90m(暂无候选词)\033[0m")

    print("-" * 68)
    if state.committed_text:
        print(f"\033[92m✔ 上屏文字:\033[0m \033[1;32m{state.committed_text}\033[0m")
    if log_msg:
        print(f"\033[94mℹ️  提示:\033[0m {log_msg}")
    print("=" * 68)
    sys.stdout.flush()


def run_demo(engine: YanMoEngine):
    """Run an automated demonstration of key scenarios including self-learning."""
    scenarios = [
        ("场景 1: 输入全拼 'yanmo' 检索言墨输入法", ["y", "a", "n", "m", "o", " "]),
        ("场景 2: 输入 'he'，候选项众多，'何' 位于后列", ["h", "e"]),
        ("场景 3: 用户主动选择 '何' (按数字 4) 上屏", ["4"]),
        ("场景 4: 再次输入 'he'，'何' 自动跃升为首选第 1 位 (★自学词动态调频)！", ["h", "e"]),
        ("场景 5: 按 Tab 键进入部首筛选，输入 'shui' (水部)，候选收敛为水部字", ["Tab", "s", "h", "u", "i"]),
        ("场景 6: 选中候选 '1' (河) 上屏", ["1"]),
        ("场景 7: 输入 'he'，右上角点选 '艹' (草字头)，筛选出 '荷'", ["h", "e", "CLICK_CAO", "1"]),
    ]

    for title, steps in scenarios:
        engine.reset()
        render_ui(engine, f"正在演示: {title}")
        time.sleep(1.0)

        for step in steps:
            time.sleep(0.35)
            if step == "CLICK_CAO":
                engine.apply_visual_radical_filter("艹")
                render_ui(engine, f"点击了右上角 [部首 ▾] -> 选择 '艹' (草部)")
            else:
                engine.feed_key(step)
                render_ui(engine, f"按下了按键: [{step}]")
        time.sleep(1.2)

    render_ui(engine, "演示完成！言墨 Trie 前缀索引与自学习词库运作完美！")


def interactive_loop(engine: YanMoEngine):
    """Run interactive keyboard event loop."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        render_ui(engine, "就绪，请按下任意字母键键入拼音...")

        while True:
            ch = sys.stdin.read(1)

            # Ctrl+C
            if ch == "\x03":
                break

            # Escape
            if ch == "\x1b":
                engine.feed_key("Escape")
                render_ui(engine, "已取消 (Esc)")
                continue

            # Tab
            if ch == "\t":
                engine.feed_key("Tab")
                render_ui(engine, "进入/切换 [部首筛选模式] (Tab)")
                continue

            # Backspace / DEL
            if ch in ("\x7f", "\x08"):
                engine.feed_key("Backspace")
                render_ui(engine)
                continue

            # Enter or Space
            if ch in ("\r", "\n", " "):
                engine.feed_key(" ")
                render_ui(engine, "选词上屏，词频已自动自学！")
                continue

            # Backtick / Tilde
            if ch in ("`", "~"):
                engine.feed_key("`")
                render_ui(engine, "切换 [部首筛选模式] (~)")
                continue

            # Digits 1-9
            if ch in "123456789":
                consumed = engine.feed_key(ch)
                if consumed:
                    render_ui(engine, f"选择候选 #{ch} 上屏，已记入个人自学词库！")
                continue

            # Alphabet
            if ch.isalpha():
                engine.feed_key(ch)
                render_ui(engine)
                continue

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print("\n已退出言墨输入法体验终端。\n")


def main():
    engine = YanMoEngine()
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        run_demo(engine)
    else:
        if sys.stdin.isatty():
            interactive_loop(engine)
        else:
            run_demo(engine)


if __name__ == "__main__":
    main()
