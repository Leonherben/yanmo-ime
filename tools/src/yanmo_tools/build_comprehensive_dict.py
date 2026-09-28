"""
Comprehensive Lexicon and Character Database Builder for YanMo IME (言墨输入法).
Generates:
1. data/dict/core_lexicon.json (~110,000+ words + 20,000+ CJK characters)
2. data/radicals/char_radicals.json (Complete radical, stroke, and component metadata for all characters)
"""

import json
import math
import os
import sys
import subprocess
from pathlib import Path
import opencc
import pypinyin
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


def load_cjk_characters_from_rime():
    """Load all single CJK characters and their pinyin pronunciations from luna_pinyin.dict.yaml."""
    dict_file = Path("/usr/share/rime-data/luna_pinyin.dict.yaml")
    char_pinyins = {}
    if not dict_file.exists():
        return {}

    with open(dict_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-") or line.startswith("..."):
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                word = parts[0]
                py = parts[1].split()[0]  # strip tone or percentage if present
                if len(word) == 1 and "\u4e00" <= word <= "\u9fff":
                    if word not in char_pinyins:
                        char_pinyins[word] = []
                    if py not in char_pinyins[word]:
                        char_pinyins[word].append(py)

    return char_pinyins


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


def load_word_frequencies(limit_words=80000):
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


def load_pypinyin_phrases():
    """Load 47,000+ standard idioms and phrases from pypinyin package."""
    pkg_dir = os.path.dirname(pypinyin.__file__)
    phrases_file = os.path.join(pkg_dir, "phrases_dict.json")
    if os.path.exists(phrases_file):
        with open(phrases_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# 著名三国人物、历史名人、古地名与高频典故
THREE_KINGDOMS_AND_HISTORY = [
    # 三国魏晋人物
    ("张郃", "zhanghe", 9500),
    ("曹操", "caocao", 9900),
    ("曹丕", "caopi", 9600),
    ("曹植", "caozhi", 9600),
    ("曹仁", "caoren", 9400),
    ("曹洪", "caohong", 9300),
    ("曹真", "caozhen", 9300),
    ("曹休", "caoxiu", 9200),
    ("夏侯惇", "xiahoudun", 9500),
    ("夏侯渊", "xiahouyuan", 9500),
    ("夏侯霸", "xiahouba", 9200),
    ("司马懿", "simayi", 9900),
    ("司马师", "simashi", 9500),
    ("司马昭", "simazhao", 9600),
    ("司马炎", "simayan", 9500),
    ("司马徽", "simahui", 9200),
    ("张辽", "zhangliao", 9600),
    ("徐晃", "xuhuang", 9500),
    ("于禁", "yujin", 9400),
    ("乐进", "yuejin", 9400),
    ("庞德", "pangde", 9300),
    ("荀彧", "xunyu", 9600),
    ("荀攸", "xunyou", 9400),
    ("郭嘉", "guojia", 9600),
    ("贾诩", "jiaxu", 9500),
    ("程昱", "chengyu", 9300),
    ("典韦", "dianwei", 9500),
    ("许褚", "xuchu", 9500),
    ("钟会", "zhonghui", 9400),
    ("邓艾", "dengai", 9500),
    ("羊祜", "yanghu", 9200),
    ("杜预", "duyu", 9200),
    ("郭淮", "guohuai", 9200),
    ("郝昭", "haozhao", 9200),
    ("满宠", "manchong", 9100),
    ("田豫", "tianyu", 9100),
    ("文聘", "wenpin", 9100),
    ("李典", "lidian", 9200),
    ("甄宓", "zhenfu", 9200),
    ("蔡文姬", "caiwenji", 9400),
    ("曹冲", "caochong", 9300),

    # 三国蜀汉人物
    ("刘备", "liubei", 9900),
    ("诸葛亮", "zhugeliang", 9990),
    ("关羽", "guanyu", 9950),
    ("张飞", "zhangfei", 9900),
    ("赵云", "zhaoyun", 9950),
    ("马超", "machao", 9700),
    ("黄忠", "huangzhong", 9700),
    ("魏延", "weiyan", 9600),
    ("姜维", "jiangwei", 9600),
    ("庞统", "pangtong", 9600),
    ("法正", "fazheng", 9500),
    ("蒋琬", "jiangwan", 9300),
    ("费祎", "feiyi", 9300),
    ("董允", "dongyun", 9200),
    ("严颜", "yanyan", 9200),
    ("马岱", "madai", 9300),
    ("关平", "guanping", 9300),
    ("关兴", "guanxing", 9200),
    ("张苞", "zhangbao", 9200),
    ("关银屏", "guanyinping", 9100),
    ("黄月英", "huangyueying", 9300),
    ("徐庶", "xushu", 9500),
    ("糜竺", "mizhu", 9100),
    ("简雍", "jianyong", 9100),
    ("孙乾", "sunqian", 9100),
    ("廖化", "liaohua", 9300),
    ("王平", "wangping", 9300),
    ("诸葛瞻", "zhugezhan", 9200),
    ("孟获", "menghuo", 9400),
    ("祝融", "zhurong", 9300),

    # 三国东吴人物
    ("孙权", "sunquan", 9900),
    ("孙策", "sunce", 9700),
    ("孙坚", "sunjian", 9600),
    ("周瑜", "zhouyu", 9900),
    ("鲁肃", "lusu", 9700),
    ("吕蒙", "lvmeng", 9700),
    ("陆逊", "luxun", 9700),
    ("陆抗", "lukang", 9300),
    ("太史慈", "taishici", 9600),
    ("甘宁", "ganning", 9600),
    ("周泰", "zhoutai", 9500),
    ("黄盖", "huanggai", 9600),
    ("程普", "chengpu", 9300),
    ("韩当", "handang", 9300),
    ("凌统", "lingtong", 9300),
    ("潘璋", "panzhang", 9200),
    ("丁奉", "dingfeng", 9300),
    ("诸葛瑾", "zhugejin", 9300),
    ("诸葛恪", "zhugeke", 9300),
    ("张昭", "zhangzhao", 9400),
    ("张纮", "zhanghong", 9200),
    ("大乔", "daqiao", 9500),
    ("小乔", "xiaoqiao", 9500),
    ("孙尚香", "sunshangxiang", 9500),
    ("步练师", "bulianshi", 9200),

    # 群雄与东汉末年
    ("董卓", "dongzhuo", 9800),
    ("吕布", "lvbu", 9900),
    ("貂蝉", "diaochan", 9850),
    ("陈宫", "chengong", 9400),
    ("高顺", "gaoshun", 9300),
    ("张辽", "zhangliao", 9600),
    ("袁绍", "yuanshao", 9700),
    ("袁术", "yuanshu", 9600),
    ("颜良", "yanliang", 9500),
    ("文丑", "wenchou", 9500),
    ("沮授", "jushou", 9200),
    ("田丰", "tianfeng", 9300),
    ("公孙瓒", "gongsunzan", 9400),
    ("陶谦", "taoqian", 9300),
    ("孔融", "kongrong", 9400),
    ("刘表", "liubiao", 9400),
    ("刘璋", "liuzhang", 9300),
    ("马腾", "mateng", 9400),
    ("韩遂", "hansui", 9300),
    ("华佗", "huatuo", 9600),
    ("张角", "zhangjiao", 9500),
    ("汉献帝", "hanxiandi", 9400),
    ("水镜先生", "shuijingxiansheng", 9200),

    # 著名地名与典故
    ("郃阳", "heyang", 9200),
    ("许昌", "xuchang", 9500),
    ("洛阳", "luoyang", 9800),
    ("长安", "changan", 9800),
    ("邺城", "yecheng", 9200),
    ("荆州", "jingzhou", 9600),
    ("益州", "yizhou", 9500),
    ("汉中", "hanzhong", 9500),
    ("襄阳", "xiangyang", 9600),
    ("定军山", "dingjunshan", 9300),
    ("街亭", "jieting", 9400),
    ("五丈原", "wuzhangyuan", 9400),
    ("白帝城", "baidicheng", 9400),
    ("赤壁", "chibi", 9700),
    ("官渡", "guandu", 9600),
    ("逍遥津", "xiaoyaojin", 9300),
    ("剑门关", "jianmengan", 9400),
    ("桃园结义", "taoyuanjieyi", 9500),
    ("三顾茅庐", "sangumaolu", 9600),
    ("草船借箭", "caochuanjiejian", 9600),
    ("万事俱备", "wanshijubei", 9500),
    ("只欠东风", "zhiqiandongfeng", 9500),
    ("单刀赴会", "dandaofuhui", 9500),
    ("刮骨疗毒", "guaguliaodu", 9500),
    ("乐不思蜀", "lebusishu", 9600),
    ("七擒七纵", "qiqinqizong", 9500),
    ("六出祁山", "liuchuqishan", 9500),
    ("空城计", "kongchengji", 9600),
    ("鞠躬尽瘁", "jugongjincui", 9600),
    ("死而后已", "sierhouyi", 9600),
]


def main():
    print("🚀 开始构建言墨输入法全量词库与部首字典 (超大字表与历史人物增强版)...")

    # 1. Load resources
    print("1. 加载五笔画表、字根组件与词频语料...")
    strokes_map = load_stroke_dictionary()
    print(f"   已加载 {len(strokes_map)} 个汉字的笔画数据")

    curated_components = load_curated_components()
    print(f"   已加载 {len(curated_components)} 个汉字拆字组件")

    char_raw_freqs, top_multi_words = load_word_frequencies(limit_words=80000)
    print(f"   已精选 {len(top_multi_words)} 条现代汉语高频词汇")

    pypinyin_phrases = load_pypinyin_phrases()
    print(f"   已加载 {len(pypinyin_phrases)} 条标准成语短语词库")

    rime_chars = load_cjk_characters_from_rime()
    print(f"   已就绪 {len(rime_chars)} 个 CJK 汉字发音表")

    gb_chars = set(get_all_gb2312_characters())
    all_chars = set(gb_chars) | set(rime_chars.keys())
    print(f"   合并后汉字总数: {len(all_chars)} 个汉字")

    rad_tool = Radical(RunOption.Radical)

    # 2. Build char_radicals.json and single characters in lexicon
    print("2. 正在提取汉字部首、笔画与频率元数据...")
    char_radicals_dict = {}
    lexicon_entries = []
    seen_lexicon = set()

    for ch in all_chars:
        # Pinyin(s)
        py_list = rime_chars.get(ch, [])
        if not py_list:
            py_list = pinyin(ch, style=Style.NORMAL, heteronym=True)[0]
        primary_pinyin = py_list[0] if py_list else ""

        # Radical
        rad = rad_tool.trans_ch(ch)
        if not rad or rad == "None":
            rad = ch

        # Strokes
        stk_seq = strokes_map.get(ch, "")
        first_stk = stk_seq[0] if stk_seq else None

        # Frequency: scale log frequency to 1500 - 9999
        raw_cnt = char_raw_freqs.get(ch, 0)
        if raw_cnt > 0:
            freq = min(9999, max(1800, int(1800 + 1300 * math.log10(raw_cnt + 1))))
        elif ch in gb_chars:
            freq = 2500  # GB2312 Level 2 baseline
        else:
            freq = 1500  # Rare / CJK extension baseline

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

    # 3. Add Top Multi-character Words from essay.txt
    print("3. 正在生成语料库高频词汇拼音索引与权重...")
    for word, cnt in top_multi_words:
        py = "".join(lazy_pinyin(word))
        # Scale frequency 2500 - 9990 based on real usage distribution
        rel_freq = min(9990, max(2500, int(2000 + 1400 * math.log10(cnt + 1))))
        key = (word, py)
        if key not in seen_lexicon:
            seen_lexicon.add(key)
            lexicon_entries.append({
                "word": word,
                "pinyin": py,
                "freq": rel_freq
            })

    # 4. Add pypinyin standard phrases & idioms
    print("4. 正在融合标准成语与短语词库...")
    for phrase in pypinyin_phrases.keys():
        if len(phrase) >= 2 and all("\u4e00" <= c <= "\u9fff" for c in phrase):
            py = "".join(lazy_pinyin(phrase))
            key = (phrase, py)
            if key not in seen_lexicon:
                seen_lexicon.add(key)
                lexicon_entries.append({
                    "word": phrase,
                    "pinyin": py,
                    "freq": 6500  # Solid baseline for idioms
                })

    # 5. Add Three Kingdoms & Historical Figures
    print("5. 正在注入三国人物、历史名人与经典典故词条...")
    for w, py, f in THREE_KINGDOMS_AND_HISTORY:
        # Scale historical figures to 6800-7950 so common daily words (如 国家、关于) take precedence, while easily beating rare words (如 章和、草草)
        scaled_f = int(6800 + (f - 9000) * 1.15)
        key = (w, py)
        if key in seen_lexicon:
            for item in lexicon_entries:
                if item["word"] == w and item["pinyin"] == py:
                    item["freq"] = max(item["freq"], scaled_f)
                    break
        else:
            seen_lexicon.add(key)
            lexicon_entries.append({
                "word": w,
                "pinyin": py,
                "freq": scaled_f
            })

    # 6. Add Tech, Science & High-Priority Domain Words
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

    # 7. Save outputs
    print("6. 保存字典文件到 data/ 目录...")
    out_lexicon_file = DICT_DIR / "core_lexicon.json"
    with open(out_lexicon_file, "w", encoding="utf-8") as f:
        json.dump(lexicon_entries, f, ensure_ascii=False, indent=1)

    out_radicals_file = RADICALS_DIR / "char_radicals.json"
    with open(out_radicals_file, "w", encoding="utf-8") as f:
        json.dump(char_radicals_dict, f, ensure_ascii=False, indent=1)

    print(f"✅ 词库构建全部完成！")
    print(f"   - 词典词条总数: {len(lexicon_entries)} (保存至 {out_lexicon_file})")
    print(f"   - 汉字全量字典: {len(char_radicals_dict)} (保存至 {out_radicals_file})")


if __name__ == "__main__":
    main()
