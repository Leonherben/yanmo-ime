"""
Build expanded lexicon for YanMo IME (言墨输入法).
Generates rich vocabulary across common life, science, technology, idioms, and computing.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DICT_DIR = BASE_DIR / "data" / "dict"
RADICALS_DIR = BASE_DIR / "data" / "radicals"

# Load existing character radicals so all characters are included
char_radicals_file = RADICALS_DIR / "char_radicals.json"
char_radicals = {}
if char_radicals_file.exists():
    with open(char_radicals_file, "r", encoding="utf-8") as f:
        char_radicals = json.load(f)

# Extended Vocabulary Database
EXTENDED_VOCABULARY = [
    # 科技与计算机 (Technology & Computing)
    ("人工智能", "rengongzhihuineng", 9950),
    ("算法", "suanfa", 9800),
    ("模型", "moxing", 9850),
    ("深度学习", "shenduxuexi", 9700),
    ("神经网络", "shenjingwangluo", 9600),
    ("数据结构", "shujujiegou", 9650),
    ("数据库", "shujuku", 9800),
    ("操作系统", "caozuoxitong", 9750),
    ("开源", "kaiyuan", 9700),
    ("代码", "daima", 9900),
    ("仓库", "cangku", 9500),
    ("架构", "jiagou", 9650),
    ("引擎", "yinqing", 9600),
    ("输入法", "shurufa", 9999),
    ("言墨", "yanmo", 10000),
    ("部首", "bushou", 9900),
    ("拼音", "pinyin", 9950),
    ("词库", "ciku", 9850),
    ("终端", "zhongduan", 9700),
    ("编译器", "bianyiqi", 9500),
    ("内存", "neicun", 9800),
    ("性能", "xingneng", 9850),
    ("优化", "youhua", 9800),
    ("网络", "wangluo", 9920),
    ("协议", "xieyi", 9700),
    ("接口", "jiekou", 9800),
    ("服务", "fuwu", 9900),
    ("客户端", "kehuduan", 9750),
    ("浏览器", "liulanqi", 9850),
    ("文件", "wenjian", 9900),
    ("目录", "mulu", 9700),
    ("搜索", "sousuo", 9900),
    ("检索", "jiansuo", 9600),

    # 日常高频与社交沟通 (Daily Life & Communication)
    ("你好", "nihao", 10000),
    ("谢谢", "xiexie", 9990),
    ("早上好", "zaoshanghao", 9800),
    ("晚上好", "wanshanghao", 9800),
    ("没问题", "meiwenti", 9850),
    ("可以", "keyi", 9980),
    ("好的", "haode", 9990),
    ("今天", "jintian", 9980),
    ("明天", "mingtian", 9970),
    ("昨天", "zuotian", 9950),
    ("现在", "xianzai", 9980),
    ("时间", "shijian", 9980),
    ("朋友", "pengyou", 9930),
    ("同学", "tongxue", 9850),
    ("工作", "gongzuo", 9980),
    ("学习", "xuexi", 9970),
    ("生活", "shenghuo", 9960),
    ("世界", "shijie", 9950),
    ("国家", "guojia", 9970),
    ("社会", "shehui", 9940),
    ("人民", "renmin", 9960),
    ("中国", "zhongguo", 10000),
    ("中文", "zhongwen", 9990),
    ("文化", "wenhua", 9920),
    ("历史", "lishi", 9910),
    ("经济", "jingji", 9930),
    ("发展", "fazhan", 9940),
    ("未来", "weilai", 9920),
    ("希望", "xiwang", 9910),
    ("成功", "chenggong", 9900),
    ("计划", "jihua", 9880),
    ("目标", "mubiao", 9870),
    ("任务", "renwu", 9860),

    # 常用成语 (Idioms)
    ("心有灵犀", "xinyoulingxi", 9200),
    ("循序渐进", "xunxujianjin", 9100),
    ("实事求是", "shishiqiushi", 9300),
    ("知行合一", "zhixingheyi", 9200),
    ("日新月异", "rixinyueyi", 9150),
    ("厚积薄发", "houjibofa", 9250),
    ("聚沙成塔", "jushachengta", 9050),
    ("迎刃而解", "yingrenerjie", 9100),
    ("精益求精", "jingyiciujing", 9200),
    ("持之以恒", "chizhiyiheng", 9250),
]


def main():
    seen_words = set()
    full_lexicon = []

    # 1. Add single characters from character mapping
    for ch, meta in char_radicals.items():
        full_lexicon.append({
            "word": ch,
            "pinyin": meta["pinyin"],
            "freq": meta.get("freq", 5000),
            "radical": meta.get("radical")
        })
        seen_words.add(ch)

    # 2. Add extended vocabulary
    for word, pinyin, freq in EXTENDED_VOCABULARY:
        if word not in seen_words:
            full_lexicon.append({
                "word": word,
                "pinyin": pinyin,
                "freq": freq
            })
            seen_words.add(word)

    out_file = DICT_DIR / "core_lexicon.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_lexicon, f, ensure_ascii=False, indent=2)

    print(f"Expanded lexicon generated: {len(full_lexicon)} entries saved to {out_file}")


if __name__ == "__main__":
    main()
