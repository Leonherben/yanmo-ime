"""
Comprehensive Lexicon and Character Database Builder for YanMo IME (言墨输入法).
Generates:
1. data/dict/core_lexicon.json (~35,000+ words + 6,763 GB2312 characters)
2. data/radicals/char_radicals.json (Complete radical, stroke, and component metadata for all common Chinese characters)
"""

import json
import math
import os
import sys
import subprocess
from pathlib import Path
import opencc
from pypinyin import pinyin, lazy_pinyin, Style
from cnradical import Radical, RunOption

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DICT_DIR = DATA_DIR / "dict"
RADICALS_DIR = DATA_DIR / "radicals"

DICT_DIR.mkdir(parents=True, exist_ok=True)
RADICALS_DIR.mkdir(parents=True, exist_ok=True)


def get_all_gb2312_characters():
    """Extract all 6,763 official GB2312 simplified Chinese characters."""
    chars = []
    # Level 1: 3,755 high-frequency characters (0xB0 to 0xD7, 0xA1 to 0xFE)
    for b1 in range(0xB0, 0xD8):
        for b2 in range(0xA1, 0xFF):
            try:
                ch = bytes([b1, b2]).decode("gb2312")
                chars.append(ch)
            except Exception:
                pass

    # Level 2: 3,008 characters (0xD8 to 0xF7, 0xA1 to 0xFE)
    for b1 in range(0xD8, 0xF8):
        for b2 in range(0xA1, 0xFF):
            try:
                ch = bytes([b1, b2]).decode("gb2312")
                chars.append(ch)
            except Exception:
                pass
    return chars


def load_stroke_dictionary():
    """Load character stroke decompositions and first stroke from Rime stroke table."""
    stroke_file = Path("/usr/share/rime-data/stroke.dict.yaml")
    strokes_map = {}
    if stroke_file.exists():
        with open(stroke_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-") or line.startswith("..."):
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    char = parts[0]
                    stk = parts[1].replace("n", "d")  # map n (捺) to d (点)
                    if char not in strokes_map:
                        strokes_map[char] = stk
    return strokes_map


def load_curated_components():
    """Load curated multi-component decompositions from previous database or git."""
    curated_file = Path("/tmp/curated_components.json")
    if curated_file.exists():
        try:
            with open(curated_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Fallback to git show HEAD:data/radicals/char_radicals.json
    try:
        out = subprocess.check_output(
            ["git", "show", "HEAD:data/radicals/char_radicals.json"],
            encoding="utf-8",
            cwd=str(BASE_DIR)
        )
        data = json.loads(out)
        return {ch: meta["components"] for ch, meta in data.items() if len(meta.get("components", [])) >= 2}
    except Exception:
        return {}


def load_word_frequencies(limit_words=32000):
    """Load high frequency words from Rime essay.txt corpus, converted to simplified Chinese."""
    essay_file = Path("/usr/share/rime-data/essay.txt")
    if not essay_file.exists():
        return {}, []

    cc = opencc.OpenCC("t2s")
    raw_freqs = {}

    with open(essay_file, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                w = cc.convert(parts[0])
                try:
                    cnt = int(parts[1])
                except ValueError:
                    cnt = 0
                if cnt > 0:
                    if w not in raw_freqs or cnt > raw_freqs[w]:
                        raw_freqs[w] = cnt

    # Filter multi-character Chinese words
    multi_words = []
    for w, cnt in raw_freqs.items():
        if len(w) >= 2 and all("\u4e00" <= c <= "\u9fff" for c in w):
            multi_words.append((w, cnt))

    # Sort descending by frequency
    multi_words.sort(key=lambda x: x[1], reverse=True)
    selected_words = multi_words[:limit_words]

    return raw_freqs, selected_words


def main():
    print("🚀 开始构建言墨输入法全量词库与部首字典...")

    # 1. Load resources
    print("1. 加载五笔画表、字根组件与词频语料...")
    strokes_map = load_stroke_dictionary()
    print(f"   已加载 {len(strokes_map)} 个汉字的笔画数据")

    curated_components = load_curated_components()
    print(f"   已加载 {len(curated_components)} 个汉字拆字组件")

    char_raw_freqs, top_multi_words = load_word_frequencies(limit_words=32000)
    print(f"   已精选 {len(top_multi_words)} 条现代汉语高频词汇")

    rad_tool = Radical(RunOption.Radical)
    gb_chars = get_all_gb2312_characters()
    print(f"   已就绪 {len(gb_chars)} 个 GB2312 标准常用汉字")

    # 2. Build char_radicals.json
    print("2. 正在提取汉字部首、笔画与频率元数据...")
    char_radicals_dict = {}
    lexicon_entries = []
    seen_lexicon = set()

    for ch in gb_chars:
        # Pinyin(s)
        py_list = pinyin(ch, style=Style.NORMAL, heteronym=True)[0]
        primary_pinyin = py_list[0] if py_list else ""

        # Radical
        rad = rad_tool.trans_ch(ch)
        if not rad or rad == "None":
            rad = ch

        # Strokes
        stk_seq = strokes_map.get(ch, "")
        first_stk = stk_seq[0] if stk_seq else None

        # Frequency: scale log frequency to 1000 - 9999
        raw_cnt = char_raw_freqs.get(ch, 0)
        if raw_cnt > 0:
            freq = min(9999, max(1500, int(1500 + 1300 * math.log10(raw_cnt + 1))))
        else:
            freq = 2000  # Default baseline for GB2312 Level 2 characters

        # Components: use curated if available, else [rad, ch]
        if ch in curated_components:
            components = list(curated_components[ch])
        else:
            components = [rad] if rad != ch else []
            if ch not in components:
                components.append(ch)

        char_radicals_dict[ch] = {
            "pinyin": primary_pinyin,
            "radical": rad,
            "components": components,
            "freq": freq,
            "strokes": stk_seq,
            "first_stroke": first_stk
        }

        # Add single character to lexicon (support heteronyms)
        for py in py_list:
            key = (ch, py)
            if key not in seen_lexicon:
                seen_lexicon.add(key)
                lexicon_entries.append({
                    "word": ch,
                    "pinyin": py,
                    "freq": freq,
                    "radical": rad
                })

    # 3. Add Top Multi-character Words
    print("3. 正在生成高频词汇拼音索引与权重...")
    for word, cnt in top_multi_words:
        py = "".join(lazy_pinyin(word))
        # Scale frequency 2500 - 9990
        rel_freq = min(9990, max(2500, int(2500 + 1200 * math.log10(cnt + 1))))
        key = (word, py)
        if key not in seen_lexicon:
            seen_lexicon.add(key)
            lexicon_entries.append({
                "word": word,
                "pinyin": py,
                "freq": rel_freq
            })

    # 4. Add Tech, Science & High-Priority Domain Words
    tech_words = [
        ("言墨", "yanmo", 10000),
        ("输入法", "shurufa", 10000),
        ("你好", "nihao", 10000),
        ("谢谢", "xiexie", 9995),
        ("人工智能", "rengongzhineng", 9950),
        ("深度学习", "shenduxuexi", 9800),
        ("大模型", "damoxing", 9850),
        ("自然语言处理", "ziranyuyanchuli", 9750),
        ("算法", "suanfa", 9850),
        ("操作系统", "caozuoxitong", 9800),
        ("开源", "kaiyuan", 9800),
        ("代码", "daima", 9900),
        ("仓库", "cangku", 9600),
        ("架构", "jiagou", 9700),
        ("引擎", "yinqing", 9700),
        ("终端", "zhongduan", 9800),
        ("部首", "bushou", 9900),
        ("拼音", "pinyin", 9950),
        ("词库", "ciku", 9850),
        ("内存", "neicun", 9800),
        ("性能", "xingneng", 9850),
        ("优化", "youhua", 9850),
        ("客户端", "kehuduan", 9800),
        ("浏览器", "liulanqi", 9850),
        ("服务器", "fuwuqi", 9850),
        ("数据库", "shujuku", 9850),
    ]
    for w, py, f in tech_words:
        key = (w, py)
        if key in seen_lexicon:
            for item in lexicon_entries:
                if item["word"] == w and item["pinyin"] == py:
                    item["freq"] = max(item["freq"], f)
                    break
        else:
            seen_lexicon.add(key)
            lexicon_entries.append({
                "word": w,
                "pinyin": py,
                "freq": f
            })

    # Sort lexicon by frequency descending
    lexicon_entries.sort(key=lambda x: x["freq"], reverse=True)

    # 5. Save outputs
    print("4. 保存字典文件到 data/ 目录...")
    out_lexicon_file = DICT_DIR / "core_lexicon.json"
    with open(out_lexicon_file, "w", encoding="utf-8") as f:
        json.dump(lexicon_entries, f, ensure_ascii=False, indent=1)

    out_radicals_file = RADICALS_DIR / "char_radicals.json"
    with open(out_radicals_file, "w", encoding="utf-8") as f:
        json.dump(char_radicals_dict, f, ensure_ascii=False, indent=1)

    print(f"✅ 词库生成完成！")
    print(f"   - 词典词条总数: {len(lexicon_entries)} (保存至 {out_lexicon_file})")
    print(f"   - 汉字部首字典: {len(char_radicals_dict)} (保存至 {out_radicals_file})")


if __name__ == "__main__":
    main()
