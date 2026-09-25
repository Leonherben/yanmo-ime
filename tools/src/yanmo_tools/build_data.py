"""
Data generation script for YanMo IME (言墨输入法).
Generates:
1. data/radicals/radicals.json (Radicals, variants, pinyins, strokes)
2. data/radicals/char_radicals.json (Character -> radical & component mapping)
3. data/dict/core_lexicon.json (Core pinyin dictionary with frequencies)
"""

import json
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RADICALS_DIR = DATA_DIR / "radicals"
DICT_DIR = DATA_DIR / "dict"

RADICALS_DIR.mkdir(parents=True, exist_ok=True)
DICT_DIR.mkdir(parents=True, exist_ok=True)

# 1. 214 Standard Radicals + Common Variants + Pinyins + Stroke Count
RADICALS_DATA = [
    # 1画
    {"id": 1, "radical": "一", "variants": ["一"], "pinyin": ["yi"], "strokes": 1, "name": "一部"},
    {"id": 2, "radical": "丨", "variants": ["丨"], "pinyin": ["gun", "shu"], "strokes": 1, "name": "竖笔"},
    {"id": 3, "radical": "丿", "variants": ["丿"], "pinyin": ["pie"], "strokes": 1, "name": "撇笔"},
    {"id": 4, "radical": "丶", "variants": ["丶"], "pinyin": ["dian"], "strokes": 1, "name": "点笔"},
    {"id": 5, "radical": "乙", "variants": ["乙", "乛", "乚", "⺄"], "pinyin": ["yi", "zhe"], "strokes": 1, "name": "乙部"},
    {"id": 6, "radical": "亅", "variants": ["亅"], "pinyin": ["jue", "gou"], "strokes": 1, "name": "竖钩"},
    # 2画
    {"id": 7, "radical": "二", "variants": ["二"], "pinyin": ["er"], "strokes": 2, "name": "二部"},
    {"id": 8, "radical": "亠", "variants": ["亠"], "pinyin": ["tou"], "strokes": 2, "name": "点横/六字头"},
    {"id": 9, "radical": "人", "variants": ["人", "亻", "入"], "pinyin": ["ren", "danren"], "strokes": 2, "name": "人部/单人旁"},
    {"id": 10, "radical": "儿", "variants": ["儿"], "pinyin": ["er"], "strokes": 2, "name": "儿部/儿字底"},
    {"id": 11, "radical": "八", "variants": ["八", "丷"], "pinyin": ["ba"], "strokes": 2, "name": "八部"},
    {"id": 12, "radical": "冂", "variants": ["冂"], "pinyin": ["tong", "tongzi"], "strokes": 2, "name": "同字框"},
    {"id": 13, "radical": "冖", "variants": ["冖"], "pinyin": ["mi", "tubaogai"], "strokes": 2, "name": "秃宝盖"},
    {"id": 14, "radical": "冫", "variants": ["冫"], "pinyin": ["bing", "liangdianshui"], "strokes": 2, "name": "两点水"},
    {"id": 15, "radical": "几", "variants": ["几"], "pinyin": ["ji"], "strokes": 2, "name": "几部"},
    {"id": 16, "radical": "凵", "variants": ["凵"], "pinyin": ["qu", "kua"], "strokes": 2, "name": "凶字框"},
    {"id": 17, "radical": "刀", "variants": ["刀", "刂"], "pinyin": ["dao", "lidao"], "strokes": 2, "name": "刀部/立刀旁"},
    {"id": 18, "radical": "力", "variants": ["力"], "pinyin": ["li"], "strokes": 2, "name": "力部"},
    {"id": 19, "radical": "勹", "variants": ["勹"], "pinyin": ["bao"], "strokes": 2, "name": "包字头"},
    {"id": 20, "radical": "匕", "variants": ["匕"], "pinyin": ["bi"], "strokes": 2, "name": "匕部"},
    {"id": 21, "radical": "匚", "variants": ["匚"], "pinyin": ["fang"], "strokes": 2, "name": "三框儿"},
    {"id": 22, "radical": "十", "variants": ["十"], "pinyin": ["shi"], "strokes": 2, "name": "十字儿"},
    {"id": 23, "radical": "卜", "variants": ["卜"], "pinyin": ["bu"], "strokes": 2, "name": "卜字旁"},
    {"id": 24, "radical": "卩", "variants": ["卩", "阝"], "pinyin": ["jie", "daner", "erdao"], "strokes": 2, "name": "单耳旁/耳刀"},
    {"id": 25, "radical": "厂", "variants": ["厂"], "pinyin": ["chang"], "strokes": 2, "name": "厂部/偏厂儿"},
    {"id": 26, "radical": "厶", "variants": ["厶"], "pinyin": ["si"], "strokes": 2, "name": "私字儿"},
    {"id": 27, "radical": "又", "variants": ["又"], "pinyin": ["you"], "strokes": 2, "name": "又部"},
    # 3画
    {"id": 28, "radical": "口", "variants": ["口"], "pinyin": ["kou"], "strokes": 3, "name": "口字旁"},
    {"id": 29, "radical": "囗", "variants": ["囗"], "pinyin": ["wei", "daguo"], "strokes": 3, "name": "大口框/国字框"},
    {"id": 30, "radical": "土", "variants": ["土"], "pinyin": ["tu", "tizi"], "strokes": 3, "name": "提土旁/土部"},
    {"id": 31, "radical": "士", "variants": ["士"], "pinyin": ["shi"], "strokes": 3, "name": "士部"},
    {"id": 32, "radical": "夂", "variants": ["夂"], "pinyin": ["zhi"], "strokes": 3, "name": "反文头/夂部"},
    {"id": 33, "radical": "夕", "variants": ["夕"], "pinyin": ["xi"], "strokes": 3, "name": "夕部/夕字旁"},
    {"id": 34, "radical": "大", "variants": ["大"], "pinyin": ["da"], "strokes": 3, "name": "大部/大字头"},
    {"id": 35, "radical": "女", "variants": ["女"], "pinyin": ["nv", "nu"], "strokes": 3, "name": "女字旁"},
    {"id": 36, "radical": "子", "variants": ["子"], "pinyin": ["zi"], "strokes": 3, "name": "子字旁"},
    {"id": 37, "radical": "宀", "variants": ["宀"], "pinyin": ["mian", "baogai"], "strokes": 3, "name": "宝盖头"},
    {"id": 38, "radical": "寸", "variants": ["寸"], "pinyin": ["cun"], "strokes": 3, "name": "寸部/寸字旁"},
    {"id": 39, "radical": "小", "variants": ["小", "⺌"], "pinyin": ["xiao"], "strokes": 3, "name": "小部/小字头"},
    {"id": 40, "radical": "尸", "variants": ["尸"], "pinyin": ["shi"], "strokes": 3, "name": "尸部/尸字头"},
    {"id": 41, "radical": "山", "variants": ["山"], "pinyin": ["shan"], "strokes": 3, "name": "山字旁"},
    {"id": 42, "radical": "巛", "variants": ["巛", "川"], "pinyin": ["chuan"], "strokes": 3, "name": "三拐儿/川部"},
    {"id": 43, "radical": "工", "variants": ["工"], "pinyin": ["gong"], "strokes": 3, "name": "工部"},
    {"id": 44, "radical": "己", "variants": ["己", "已", "巳"], "pinyin": ["ji"], "strokes": 3, "name": "己部"},
    {"id": 45, "radical": "巾", "variants": ["巾"], "pinyin": ["jin"], "strokes": 3, "name": "巾字旁"},
    {"id": 46, "radical": "干", "variants": ["干"], "pinyin": ["gan"], "strokes": 3, "name": "干部"},
    {"id": 47, "radical": "幺", "variants": ["幺"], "pinyin": ["yao"], "strokes": 3, "name": "幺部/幺字旁"},
    {"id": 48, "radical": "广", "variants": ["广"], "pinyin": ["guang"], "strokes": 3, "name": "广字旁"},
    {"id": 49, "radical": "廴", "variants": ["廴"], "pinyin": ["yin", "jianzhidi"], "strokes": 3, "name": "建字底"},
    {"id": 50, "radical": "弓", "variants": ["弓"], "pinyin": ["gong"], "strokes": 3, "name": "弓字旁"},
    {"id": 51, "radical": "彡", "variants": ["彡"], "pinyin": ["shan", "sanpie"], "strokes": 3, "name": "三撇儿"},
    {"id": 52, "radical": "彳", "variants": ["彳"], "pinyin": ["chi", "shuangren"], "strokes": 3, "name": "双人旁"},
    {"id": 53, "radical": "心", "variants": ["心", "忄", "⺗"], "pinyin": ["xin", "shuxin"], "strokes": 4, "name": "心字底/竖心旁"},
    {"id": 54, "radical": "戈", "variants": ["戈"], "pinyin": ["ge"], "strokes": 4, "name": "戈部"},
    {"id": 55, "radical": "户", "variants": ["户", "戶"], "pinyin": ["hu"], "strokes": 4, "name": "户字头"},
    {"id": 56, "radical": "手", "variants": ["手", "扌"], "pinyin": ["shou", "tishou"], "strokes": 4, "name": "提手旁"},
    {"id": 57, "radical": "支", "variants": ["支"], "pinyin": ["zhi"], "strokes": 4, "name": "支部"},
    {"id": 58, "radical": "攴", "variants": ["攴", "攵"], "pinyin": ["pu", "fanwen"], "strokes": 4, "name": "反文旁"},
    {"id": 59, "radical": "文", "variants": ["文"], "pinyin": ["wen"], "strokes": 4, "name": "文字头"},
    {"id": 60, "radical": "斗", "variants": ["斗"], "pinyin": ["dou"], "strokes": 4, "name": "斗部"},
    {"id": 61, "radical": "斤", "variants": ["斤"], "pinyin": ["jin"], "strokes": 4, "name": "斤字旁"},
    {"id": 62, "radical": "方", "variants": ["方"], "pinyin": ["fang"], "strokes": 4, "name": "方字旁"},
    {"id": 63, "radical": "日", "variants": ["日"], "pinyin": ["ri"], "strokes": 4, "name": "日字旁"},
    {"id": 64, "radical": "曰", "variants": ["曰"], "pinyin": ["yue"], "strokes": 4, "name": "曰部"},
    {"id": 65, "radical": "月", "variants": ["月"], "pinyin": ["yue", "rou"], "strokes": 4, "name": "月字旁/肉月旁"},
    {"id": 66, "radical": "木", "variants": ["木"], "pinyin": ["mu"], "strokes": 4, "name": "木字旁"},
    {"id": 67, "radical": "欠", "variants": ["欠"], "pinyin": ["qian"], "strokes": 4, "name": "欠字旁"},
    {"id": 68, "radical": "止", "variants": ["止"], "pinyin": ["zhi"], "strokes": 4, "name": "止部"},
    {"id": 69, "radical": "歹", "variants": ["歹"], "pinyin": ["dai"], "strokes": 4, "name": "歹字旁"},
    {"id": 70, "radical": "殳", "variants": ["殳"], "pinyin": ["shu"], "strokes": 4, "name": "殳部"},
    {"id": 71, "radical": "毛", "variants": ["毛"], "pinyin": ["mao"], "strokes": 4, "name": "毛部"},
    {"id": 72, "radical": "氏", "variants": ["氏"], "pinyin": ["shi"], "strokes": 4, "name": "氏部"},
    {"id": 73, "radical": "气", "variants": ["气"], "pinyin": ["qi"], "strokes": 4, "name": "气字头"},
    {"id": 74, "radical": "水", "variants": ["水", "氵", "氺"], "pinyin": ["shui", "sandianshui"], "strokes": 4, "name": "三点水/水部"},
    {"id": 75, "radical": "火", "variants": ["火", "灬"], "pinyin": ["huo", "sidiandian"], "strokes": 4, "name": "火字旁/四点底"},
    {"id": 76, "radical": "爪", "variants": ["爪", "爫"], "pinyin": ["zhao", "zhua"], "strokes": 4, "name": "爪字头"},
    {"id": 77, "radical": "父", "variants": ["父"], "pinyin": ["fu"], "strokes": 4, "name": "父字头"},
    {"id": 78, "radical": "牛", "variants": ["牛", "牜"], "pinyin": ["niu"], "strokes": 4, "name": "牛字旁"},
    {"id": 79, "radical": "犬", "variants": ["犬", "犭"], "pinyin": ["quan", "fanquan"], "strokes": 4, "name": "反犬旁"},
    {"id": 80, "radical": "王", "variants": ["王", "玉"], "pinyin": ["wang", "yu"], "strokes": 4, "name": "王字旁/玉部"},
    {"id": 81, "radical": "田", "variants": ["田"], "pinyin": ["tian"], "strokes": 5, "name": "田字旁"},
    {"id": 82, "radical": "疒", "variants": ["疒"], "pinyin": ["bing", "bingzi"], "strokes": 5, "name": "病字头"},
    {"id": 83, "radical": "白", "variants": ["白"], "pinyin": ["bai"], "strokes": 5, "name": "白字旁"},
    {"id": 84, "radical": "皮", "variants": ["皮"], "pinyin": ["pi"], "strokes": 5, "name": "皮部"},
    {"id": 85, "radical": "皿", "variants": ["皿"], "pinyin": ["min", "mindi"], "strokes": 5, "name": "皿字底"},
    {"id": 86, "radical": "目", "variants": ["目"], "pinyin": ["mu"], "strokes": 5, "name": "目字旁"},
    {"id": 87, "radical": "石", "variants": ["石"], "pinyin": ["shi"], "strokes": 5, "name": "石字旁"},
    {"id": 88, "radical": "示", "variants": ["示", "礻"], "pinyin": ["shi"], "strokes": 5, "name": "示字旁/示部"},
    {"id": 89, "radical": "禾", "variants": ["禾"], "pinyin": ["he"], "strokes": 5, "name": "禾木旁"},
    {"id": 90, "radical": "穴", "variants": ["穴"], "pinyin": ["xue"], "strokes": 5, "name": "穴宝盖"},
    {"id": 91, "radical": "立", "variants": ["立"], "pinyin": ["li"], "strokes": 5, "name": "立字旁"},
    {"id": 92, "radical": "竹", "variants": ["竹", "⺮"], "pinyin": ["zhu"], "strokes": 6, "name": "竹字头"},
    {"id": 93, "radical": "米", "variants": ["米"], "pinyin": ["mi"], "strokes": 6, "name": "米字旁"},
    {"id": 94, "radical": "糸", "variants": ["糸", "纟"], "pinyin": ["si", "jiaoisi"], "strokes": 6, "name": "绞丝旁"},
    {"id": 95, "radical": "缶", "variants": ["缶"], "pinyin": ["fou"], "strokes": 6, "name": "缶部"},
    {"id": 96, "radical": "羊", "variants": ["羊", "⺷"], "pinyin": ["yang"], "strokes": 6, "name": "羊字头/羊部"},
    {"id": 97, "radical": "羽", "variants": ["羽"], "pinyin": ["yu"], "strokes": 6, "name": "羽字旁"},
    {"id": 98, "radical": "老", "variants": ["老", "耂"], "pinyin": ["lao"], "strokes": 6, "name": "老字头"},
    {"id": 99, "radical": "耳", "variants": ["耳"], "pinyin": ["er"], "strokes": 6, "name": "耳字旁"},
    {"id": 100, "radical": "舌", "variants": ["舌"], "pinyin": ["she"], "strokes": 6, "name": "舌字旁"},
    {"id": 101, "radical": "舟", "variants": ["舟"], "pinyin": ["zhou"], "strokes": 6, "name": "舟字旁"},
    {"id": 102, "radical": "艮", "variants": ["艮"], "pinyin": ["gen"], "strokes": 6, "name": "艮部"},
    {"id": 103, "radical": "艸", "variants": ["艸", "艹"], "pinyin": ["cao", "caozitou"], "strokes": 6, "name": "草字头"},
    {"id": 104, "radical": "虍", "variants": ["虍"], "pinyin": ["hu", "huzi"], "strokes": 6, "name": "虎字头"},
    {"id": 105, "radical": "虫", "variants": ["虫"], "pinyin": ["chong"], "strokes": 6, "name": "虫字旁"},
    {"id": 106, "radical": "血", "variants": ["血"], "pinyin": ["xue"], "strokes": 6, "name": "血部"},
    {"id": 107, "radical": "行", "variants": ["行"], "pinyin": ["xing"], "strokes": 6, "name": "行部"},
    {"id": 108, "radical": "衣", "variants": ["衣", "衤"], "pinyin": ["yi"], "strokes": 6, "name": "衣字旁/衣部"},
    {"id": 109, "radical": "見", "variants": ["见", "見"], "pinyin": ["jian"], "strokes": 7, "name": "见字旁"},
    {"id": 110, "radical": "角", "variants": ["角"], "pinyin": ["jiao"], "strokes": 7, "name": "角字旁"},
    {"id": 111, "radical": "言", "variants": ["言", "讠"], "pinyin": ["yan"], "strokes": 7, "name": "言字旁"},
    {"id": 112, "radical": "谷", "variants": ["谷"], "pinyin": ["gu"], "strokes": 7, "name": "谷部"},
    {"id": 113, "radical": "豆", "variants": ["豆"], "pinyin": ["dou"], "strokes": 7, "name": "豆部"},
    {"id": 114, "radical": "豕", "variants": ["豕"], "pinyin": ["shi"], "strokes": 7, "name": "豕部"},
    {"id": 115, "radical": "貝", "variants": ["贝", "貝"], "pinyin": ["bei"], "strokes": 7, "name": "贝字旁"},
    {"id": 116, "radical": "赤", "variants": ["赤"], "pinyin": ["chi"], "strokes": 7, "name": "赤部"},
    {"id": 117, "radical": "走", "variants": ["走"], "pinyin": ["zou"], "strokes": 7, "name": "走字底"},
    {"id": 118, "radical": "足", "variants": ["足", "⻊"], "pinyin": ["zu"], "strokes": 7, "name": "足字旁"},
    {"id": 119, "radical": "身", "variants": ["身"], "pinyin": ["shen"], "strokes": 7, "name": "身字旁"},
    {"id": 120, "radical": "車", "variants": ["车", "車"], "pinyin": ["che"], "strokes": 7, "name": "车字旁"},
    {"id": 121, "radical": "辛", "variants": ["辛"], "pinyin": ["xin"], "strokes": 7, "name": "辛部"},
    {"id": 122, "radical": "辵", "variants": ["辵", "辶"], "pinyin": ["chuo", "zouzhi"], "strokes": 7, "name": "走之底"},
    {"id": 123, "radical": "邑", "variants": ["邑", "阝"], "pinyin": ["yi", "youerdao"], "strokes": 7, "name": "右耳旁"},
    {"id": 124, "radical": "酉", "variants": ["酉"], "pinyin": ["you"], "strokes": 7, "name": "酉字旁"},
    {"id": 125, "radical": "里", "variants": ["里"], "pinyin": ["li"], "strokes": 7, "name": "里字旁"},
    {"id": 126, "radical": "金", "variants": ["金", "钅"], "pinyin": ["jin"], "strokes": 8, "name": "金字旁"},
    {"id": 127, "radical": "門", "variants": ["门", "門"], "pinyin": ["men"], "strokes": 8, "name": "门字框"},
    {"id": 128, "radical": "阜", "variants": ["阜", "阝"], "pinyin": ["fu", "zuoerdao"], "strokes": 8, "name": "左耳旁"},
    {"id": 129, "radical": "隹", "variants": ["隹"], "pinyin": ["zhui"], "strokes": 8, "name": "隹字旁"},
    {"id": 130, "radical": "雨", "variants": ["雨", "⻗"], "pinyin": ["yu"], "strokes": 8, "name": "雨字头"},
    {"id": 131, "radical": "青", "variants": ["青"], "pinyin": ["qing"], "strokes": 8, "name": "青部"},
    {"id": 132, "radical": "非", "variants": ["非"], "pinyin": ["fei"], "strokes": 8, "name": "非部"},
    {"id": 133, "radical": "革", "variants": ["革"], "pinyin": ["ge"], "strokes": 9, "name": "革字旁"},
    {"id": 134, "radical": "音", "variants": ["音"], "pinyin": ["yin"], "strokes": 9, "name": "音字旁"},
    {"id": 135, "radical": "頁", "variants": ["页", "頁"], "pinyin": ["ye"], "strokes": 9, "name": "页字旁"},
    {"id": 136, "radical": "風", "variants": ["风", "風"], "pinyin": ["feng"], "strokes": 9, "name": "风字旁"},
    {"id": 137, "radical": "飛", "variants": ["飞", "飛"], "pinyin": ["fei"], "strokes": 9, "name": "飞部"},
    {"id": 138, "radical": "食", "variants": ["食", "饣"], "pinyin": ["shi"], "strokes": 9, "name": "食字旁"},
    {"id": 139, "radical": "首", "variants": ["首"], "pinyin": ["shou"], "strokes": 9, "name": "首部"},
    {"id": 140, "radical": "香", "variants": ["香"], "pinyin": ["xiang"], "strokes": 9, "name": "香字旁"},
    {"id": 141, "radical": "馬", "variants": ["马", "馬"], "pinyin": ["ma"], "strokes": 10, "name": "马字旁"},
    {"id": 142, "radical": "骨", "variants": ["骨"], "pinyin": ["gu"], "strokes": 10, "name": "骨字旁"},
    {"id": 143, "radical": "高", "variants": ["高"], "pinyin": ["gao"], "strokes": 10, "name": "高部"},
    {"id": 144, "radical": "鬼", "variants": ["鬼"], "pinyin": ["gui"], "strokes": 10, "name": "鬼部"},
    {"id": 145, "radical": "魚", "variants": ["鱼", "魚"], "pinyin": ["yu"], "strokes": 11, "name": "鱼字旁"},
    {"id": 146, "radical": "鳥", "variants": ["鸟", "鳥"], "pinyin": ["niao"], "strokes": 11, "name": "鸟字旁"},
    {"id": 147, "radical": "鹵", "variants": ["卤", "鹵"], "pinyin": ["lu"], "strokes": 11, "name": "卤部"},
    {"id": 148, "radical": "鹿", "variants": ["鹿"], "pinyin": ["lu"], "strokes": 11, "name": "鹿字旁"},
    {"id": 149, "radical": "麥", "variants": ["麦", "麥"], "pinyin": ["mai"], "strokes": 11, "name": "麦字旁"},
    {"id": 150, "radical": "麻", "variants": ["麻"], "pinyin": ["ma"], "strokes": 11, "name": "麻部"},
    {"id": 151, "radical": "黄", "variants": ["黄", "黃"], "pinyin": ["huang"], "strokes": 12, "name": "黄部"},
    {"id": 152, "radical": "黑", "variants": ["黑"], "pinyin": ["hei"], "strokes": 12, "name": "黑字旁"},
    {"id": 153, "radical": "鼎", "variants": ["鼎"], "pinyin": ["ding"], "strokes": 13, "name": "鼎部"},
    {"id": 154, "radical": "鼓", "variants": ["鼓"], "pinyin": ["gu"], "strokes": 13, "name": "鼓部"},
    {"id": 155, "radical": "鼠", "variants": ["鼠"], "pinyin": ["shu"], "strokes": 13, "name": "鼠部"},
    {"id": 156, "radical": "鼻", "variants": ["鼻"], "pinyin": ["bi"], "strokes": 14, "name": "鼻字旁"},
    {"id": 157, "radical": "齒", "variants": ["齿", "齒"], "pinyin": ["chi"], "strokes": 15, "name": "齿字旁"},
    {"id": 158, "radical": "龍", "variants": ["龙", "龍"], "pinyin": ["long"], "strokes": 16, "name": "龙部"}
]

# 2. Chinese Character Decomposition & Radical Mapping
# Sample comprehensive set of common characters with pinyin, radical and decomposition components
SAMPLE_CHAR_MAPPING = {
    # 水部 (氵, 水)
    "河": {"pinyin": "he", "radical": "氵", "components": ["氵", "可"], "freq": 9800},
    "涸": {"pinyin": "he", "radical": "氵", "components": ["氵", "固"], "freq": 1200},
    "渮": {"pinyin": "he", "radical": "氵", "components": ["氵", "苛"], "freq": 200},
    "江": {"pinyin": "jiang", "radical": "氵", "components": ["氵", "工"], "freq": 9500},
    "海": {"pinyin": "hai", "radical": "氵", "components": ["氵", "每"], "freq": 9900},
    "湖": {"pinyin": "hu", "radical": "氵", "components": ["氵", "胡"], "freq": 8900},
    "波": {"pinyin": "bo", "radical": "氵", "components": ["氵", "皮"], "freq": 8800},
    "浪": {"pinyin": "lang", "radical": "氵", "components": ["氵", "良"], "freq": 8700},
    "流": {"pinyin": "liu", "radical": "氵", "components": ["氵", "充"], "freq": 9200},
    "清": {"pinyin": "qing", "radical": "氵", "components": ["氵", "青"], "freq": 9300},
    "池": {"pinyin": "chi", "radical": "氵", "components": ["氵", "也"], "freq": 8600},
    "洋": {"pinyin": "yang", "radical": "氵", "components": ["氵", "羊"], "freq": 9100},
    "洗": {"pinyin": "xi", "radical": "氵", "components": ["氵", "先"], "freq": 8500},
    "润": {"pinyin": "run", "radical": "氵", "components": ["氵", "闰"], "freq": 7800},
    "深": {"pinyin": "shen", "radical": "氵", "components": ["氵", "冖", "木"], "freq": 9300},
    "温": {"pinyin": "wen", "radical": "氵", "components": ["氵", "日", "皿"], "freq": 8900},
    "港": {"pinyin": "gang", "radical": "氵", "components": ["氵", "巷"], "freq": 8400},
    "测": {"pinyin": "ce", "radical": "氵", "components": ["氵", "贝", "刂"], "freq": 8700},
    "渺": {"pinyin": "miao", "radical": "氵", "components": ["氵", "目", "少"], "freq": 4500},
    "淼": {"pinyin": "miao", "radical": "水", "components": ["水", "水", "水"], "freq": 2100},

    # 木部
    "核": {"pinyin": "he", "radical": "木", "components": ["木", "亥"], "freq": 8900},
    "林": {"pinyin": "lin", "radical": "木", "components": ["木", "木"], "freq": 9200},
    "森": {"pinyin": "sen", "radical": "木", "components": ["木", "木", "木"], "freq": 8700},
    "休": {"pinyin": "xiu", "radical": "亻", "components": ["亻", "木"], "freq": 8500},
    "树": {"pinyin": "shu", "radical": "木", "components": ["木", "又", "寸"], "freq": 9000},
    "机": {"pinyin": "ji", "radical": "木", "components": ["木", "几"], "freq": 9950},
    "枝": {"pinyin": "zhi", "radical": "木", "components": ["木", "支"], "freq": 7600},
    "果": {"pinyin": "guo", "radical": "木", "components": ["日", "木"], "freq": 9100},
    "根": {"pinyin": "gen", "radical": "木", "components": ["木", "艮"], "freq": 8800},
    "桥": {"pinyin": "qiao", "radical": "木", "components": ["木", "乔"], "freq": 8700},
    "梁": {"pinyin": "liang", "radical": "木", "components": ["刃", "水", "木"], "freq": 8400},
    "校": {"pinyin": "xiao", "radical": "木", "components": ["木", "交"], "freq": 9300},

    # 口部与口构件
    "和": {"pinyin": "he", "radical": "口", "components": ["禾", "口"], "freq": 9990},
    "合": {"pinyin": "he", "radical": "口", "components": ["人", "一", "口"], "freq": 9850},
    "喝": {"pinyin": "he", "radical": "口", "components": ["口", "日", "勹", "人"], "freq": 8700},
    "品": {"pinyin": "pin", "radical": "口", "components": ["口", "口", "口"], "freq": 9300},
    "器": {"pinyin": "qi", "radical": "口", "components": ["口", "口", "犬", "口", "口"], "freq": 8900},
    "唱": {"pinyin": "chang", "radical": "口", "components": ["口", "昌"], "freq": 8200},
    "叫": {"pinyin": "jiao", "radical": "口", "components": ["口", "丩"], "freq": 8900},
    "问": {"pinyin": "wen", "radical": "门", "components": ["门", "口"], "freq": 9500},
    "听": {"pinyin": "ting", "radical": "口", "components": ["口", "斤"], "freq": 9200},

    # 草字头 (艹)
    "荷": {"pinyin": "he", "radical": "艹", "components": ["艹", "何"], "freq": 8100},
    "苗": {"pinyin": "miao", "radical": "艹", "components": ["艹", "田"], "freq": 8000},
    "草": {"pinyin": "cao", "radical": "艹", "components": ["艹", "早"], "freq": 9100},
    "花": {"pinyin": "hua", "radical": "艹", "components": ["艹", "化"], "freq": 9600},
    "茶": {"pinyin": "cha", "radical": "艹", "components": ["艹", "人", "木"], "freq": 8800},
    "若": {"pinyin": "ruo", "radical": "艹", "components": ["艹", "右"], "freq": 8900},
    "苦": {"pinyin": "ku", "radical": "艹", "components": ["艹", "古"], "freq": 8700},

    # 人部 (人, 亻)
    "何": {"pinyin": "he", "radical": "亻", "components": ["亻", "可"], "freq": 9600},
    "你": {"pinyin": "ni", "radical": "亻", "components": ["亻", "尔"], "freq": 9999},
    "他": {"pinyin": "ta", "radical": "亻", "components": ["亻", "也"], "freq": 9990},
    "们": {"pinyin": "men", "radical": "亻", "components": ["亻", "门"], "freq": 9980},
    "化": {"pinyin": "hua", "radical": "亻", "components": ["亻", "匕"], "freq": 9300},
    "信": {"pinyin": "xin", "radical": "亻", "components": ["亻", "言"], "freq": 9400},
    "作": {"pinyin": "zuo", "radical": "亻", "components": ["亻", "乍"], "freq": 9700},

    # 禾木旁 (禾)
    "禾": {"pinyin": "he", "radical": "禾", "components": ["禾"], "freq": 7500},
    "秋": {"pinyin": "qiu", "radical": "禾", "components": ["禾", "火"], "freq": 8600},
    "科": {"pinyin": "ke", "radical": "禾", "components": ["禾", "斗"], "freq": 9400},
    "租": {"pinyin": "zu", "radical": "禾", "components": ["禾", "且"], "freq": 8300},
    "程": {"pinyin": "cheng", "radical": "禾", "components": ["禾", "呈"], "freq": 9100},
    "秀": {"pinyin": "xiu", "radical": "禾", "components": ["禾", "乃"], "freq": 8700},

    # 日月与光 (日, 月)
    "明": {"pinyin": "ming", "radical": "日", "components": ["日", "月"], "freq": 9700},
    "晶": {"pinyin": "jing", "radical": "日", "components": ["日", "日", "日"], "freq": 8200},
    "晴": {"pinyin": "qing", "radical": "日", "components": ["日", "青"], "freq": 8800},
    "早": {"pinyin": "zao", "radical": "日", "components": ["日", "十"], "freq": 9100},
    "晨": {"pinyin": "chen", "radical": "日", "components": ["日", "辰"], "freq": 8400},
    "阳": {"pinyin": "yang", "radical": "阝", "components": ["阝", "日"], "freq": 9300},
    "朋": {"pinyin": "peng", "radical": "月", "components": ["月", "月"], "freq": 9200},
    "朝": {"pinyin": "chao", "radical": "月", "components": ["十", "日", "十", "月"], "freq": 8900},

    # 金 (钅, 金)
    "金": {"pinyin": "jin", "radical": "金", "components": ["金"], "freq": 9500},
    "银": {"pinyin": "yin", "radical": "钅", "components": ["钅", "艮"], "freq": 9000},
    "铜": {"pinyin": "tong", "radical": "钅", "components": ["钅", "同"], "freq": 8700},
    "铁": {"pinyin": "tie", "radical": "钅", "components": ["钅", "失"], "freq": 8900},
    "鑫": {"pinyin": "xin", "radical": "金", "components": ["金", "金", "金"], "freq": 6500},
    "钢": {"pinyin": "gang", "radical": "钅", "components": ["钅", "冈"], "freq": 8800},
    "钱": {"pinyin": "qian", "radical": "钅", "components": ["钅", "戋"], "freq": 9400},
    "钟": {"pinyin": "zhong", "radical": "钅", "components": ["钅", "中"], "freq": 8800},

    # 火 (火, 灬)
    "火": {"pinyin": "huo", "radical": "火", "components": ["火"], "freq": 9200},
    "炎": {"pinyin": "yan", "radical": "火", "components": ["火", "火"], "freq": 8100},
    "焱": {"pinyin": "yan", "radical": "火", "components": ["火", "火", "火"], "freq": 3500},
    "热": {"pinyin": "re", "radical": "灬", "components": ["执", "灬"], "freq": 9200},
    "点": {"pinyin": "dian", "radical": "灬", "components": ["占", "灬"], "freq": 9800},
    "照": {"pinyin": "zhao", "radical": "灬", "components": ["昭", "灬"], "freq": 9100},
    "熊": {"pinyin": "xiong", "radical": "灬", "components": ["能", "灬"], "freq": 8500},

    # 土与石 (土, 石)
    "土": {"pinyin": "tu", "radical": "土", "components": ["土"], "freq": 9000},
    "地": {"pinyin": "di", "radical": "土", "components": ["土", "也"], "freq": 9950},
    "场": {"pinyin": "chang", "radical": "土", "components": ["土", "昜"], "freq": 9400},
    "城": {"pinyin": "cheng", "radical": "土", "components": ["土", "成"], "freq": 9300},
    "石": {"pinyin": "shi", "radical": "石", "components": ["石"], "freq": 9200},
    "磊": {"pinyin": "lei", "radical": "石", "components": ["石", "石", "石"], "freq": 7500},
    "研": {"pinyin": "yan", "radical": "石", "components": ["石", "开"], "freq": 9300},
    "破": {"pinyin": "po", "radical": "石", "components": ["石", "皮"], "freq": 9000},

    # 言 (讠, 言)
    "言": {"pinyin": "yan", "radical": "言", "components": ["言"], "freq": 9100},
    "语": {"pinyin": "yu", "radical": "讠", "components": ["讠", "吾"], "freq": 9600},
    "话": {"pinyin": "hua", "radical": "讠", "components": ["讠", "舌"], "freq": 9600},
    "说": {"pinyin": "shuo", "radical": "讠", "components": ["讠", "兑"], "freq": 9800},
    "诗": {"pinyin": "shi", "radical": "讠", "components": ["讠", "寺"], "freq": 8900},
    "词": {"pinyin": "ci", "radical": "讠", "components": ["讠", "司"], "freq": 9100},
    "讯": {"pinyin": "xun", "radical": "讠", "components": ["讠", "十"], "freq": 8600},

    # 手 (扌, 手)
    "手": {"pinyin": "shou", "radical": "手", "components": ["手"], "freq": 9400},
    "打": {"pinyin": "da", "radical": "扌", "components": ["扌", "丁"], "freq": 9700},
    "提": {"pinyin": "ti", "radical": "扌", "components": ["扌", "是"], "freq": 9300},
    "持": {"pinyin": "chi", "radical": "扌", "components": ["扌", "寺"], "freq": 9200},
    "把": {"pinyin": "ba", "radical": "扌", "components": ["扌", "巴"], "freq": 9600},
    "找": {"pinyin": "zhao", "radical": "扌", "components": ["扌", "戈"], "freq": 9400},
    "接": {"pinyin": "jie", "radical": "扌", "components": ["扌", "妾"], "freq": 9300},

    # 心 (忄, 心)
    "心": {"pinyin": "xin", "radical": "心", "components": ["心"], "freq": 9800},
    "情": {"pinyin": "qing", "radical": "忄", "components": ["忄", "青"], "freq": 9600},
    "快": {"pinyin": "kuai", "radical": "忄", "components": ["忄", "夬"], "freq": 9400},
    "慢": {"pinyin": "man", "radical": "忄", "components": ["忄", "曼"], "freq": 9000},
    "想": {"pinyin": "xiang", "radical": "心", "components": ["相", "心"], "freq": 9700},
    "思": {"pinyin": "si", "radical": "心", "components": ["田", "心"], "freq": 9500},
    "念": {"pinyin": "nian", "radical": "心", "components": ["今", "心"], "freq": 9100},

    # 其他常用字
    "中": {"pinyin": "zhong", "radical": "丨", "components": ["丨", "口"], "freq": 9999},
    "文": {"pinyin": "wen", "radical": "文", "components": ["文"], "freq": 9950},
    "国": {"pinyin": "guo", "radical": "囗", "components": ["囗", "玉"], "freq": 9998},
    "家": {"pinyin": "jia", "radical": "宀", "components": ["宀", "豕"], "freq": 9900},
    "学": {"pinyin": "xue", "radical": "子", "components": ["⺌", "冖", "子"], "freq": 9800},
    "生": {"pinyin": "sheng", "radical": "生", "components": ["生"], "freq": 9920},
    "自": {"pinyin": "zi", "radical": "自", "components": ["自"], "freq": 9800},
    "用": {"pinyin": "yong", "radical": "用", "components": ["用"], "freq": 9850},
    "墨": {"pinyin": "mo", "radical": "土", "components": ["黑", "土"], "freq": 8200},
    "言": {"pinyin": "yan", "radical": "言", "components": ["言"], "freq": 9100},
    "码": {"pinyin": "ma", "radical": "石", "components": ["石", "马"], "freq": 8800},
    "法": {"pinyin": "fa", "radical": "氵", "components": ["氵", "去"], "freq": 9800},
    "入": {"pinyin": "ru", "radical": "入", "components": ["入"], "freq": 9600},
    "输": {"pinyin": "shu", "radical": "车", "components": ["车", "俞"], "freq": 9100},
}

# 3. High-Frequency Lexicon (Word -> Pinyin & Frequency)
COMMON_WORDS = [
    # 言墨特色与输入法词汇
    {"word": "言墨", "pinyin": "yanmo", "freq": 10000},
    {"word": "输入法", "pinyin": "shurufa", "freq": 9800},
    {"word": "中文", "pinyin": "zhongwen", "freq": 9900},
    {"word": "中国", "pinyin": "zhongguo", "freq": 9999},
    {"word": "编码", "pinyin": "bianma", "freq": 9100},
    {"word": "部首", "pinyin": "bushou", "freq": 9500},
    {"word": "拼音", "pinyin": "pinyin", "freq": 9600},
    {"word": "词库", "pinyin": "ciku", "freq": 9400},
    {"word": "语音", "pinyin": "yuyin", "freq": 9500},
    {"word": "核心", "pinyin": "hexin", "freq": 9300},
    {"word": "河水", "pinyin": "heshui", "freq": 8900},
    {"word": "和平", "pinyin": "heping", "freq": 9400},
    {"word": "合作", "pinyin": "hezuo", "freq": 9600},
    {"word": "合同", "pinyin": "hetong", "freq": 9500},
    {"word": "荷花", "pinyin": "hehua", "freq": 8800},
    {"word": "喝水", "pinyin": "heshui", "freq": 8900},
    {"word": "合力", "pinyin": "heli", "freq": 8700},
    {"word": "合理", "pinyin": "heli", "freq": 9200},
    {"word": "森林", "pinyin": "senlin", "freq": 9200},
    {"word": "树木", "pinyin": "shumu", "freq": 9100},
    {"word": "明月", "pinyin": "mingyue", "freq": 9000},
    {"word": "明白", "pinyin": "mingbai", "freq": 9700},
    {"word": "明天", "pinyin": "mingtian", "freq": 9800},
    {"word": "晶莹", "pinyin": "jingying", "freq": 8600},
    {"word": "品质", "pinyin": "pinzhi", "freq": 9400},
    {"word": "作品", "pinyin": "zuopin", "freq": 9300},
    {"word": "科学", "pinyin": "kexue", "freq": 9700},
    {"word": "技术", "pinyin": "jishu", "freq": 9800},
    {"word": "系统", "pinyin": "xitong", "freq": 9800},
    {"word": "开发", "pinyin": "kaifa", "freq": 9700},
    {"word": "程序", "pinyin": "chengxu", "freq": 9600},
    {"word": "机器", "pinyin": "jiqi", "freq": 9500},
    {"word": "学习", "pinyin": "xuexi", "freq": 9800},
    {"word": "我们", "pinyin": "women", "freq": 9990},
    {"word": "你们", "pinyin": "nimen", "freq": 9950},
    {"word": "他们", "pinyin": "tamen", "freq": 9960},
    {"word": "自己", "pinyin": "ziji", "freq": 9920},
    {"word": "国家", "pinyin": "guojia", "freq": 9950},
    {"word": "时间", "pinyin": "shijian", "freq": 9940},
    {"word": "问题", "pinyin": "wenti", "freq": 9920},
    {"word": "工作", "pinyin": "gongzuo", "freq": 9910},
]


def main():
    print(f"[1/3] Generating {RADICALS_DIR / 'radicals.json'}...")
    with open(RADICALS_DIR / "radicals.json", "w", encoding="utf-8") as f:
        json.dump(RADICALS_DATA, f, ensure_ascii=False, indent=2)

    print(f"[2/3] Generating {RADICALS_DIR / 'char_radicals.json'}...")
    with open(RADICALS_DIR / "char_radicals.json", "w", encoding="utf-8") as f:
        json.dump(SAMPLE_CHAR_MAPPING, f, ensure_ascii=False, indent=2)

    print(f"[3/3] Generating {DICT_DIR / 'core_lexicon.json'}...")
    # Combine single characters from SAMPLE_CHAR_MAPPING into lexicon as well
    full_lexicon = list(COMMON_WORDS)
    for ch, meta in SAMPLE_CHAR_MAPPING.items():
        full_lexicon.append({
            "word": ch,
            "pinyin": meta["pinyin"],
            "freq": meta["freq"],
            "radical": meta["radical"]
        })

    with open(DICT_DIR / "core_lexicon.json", "w", encoding="utf-8") as f:
        json.dump(full_lexicon, f, ensure_ascii=False, indent=2)

    print(f"Data generation complete!")
    print(f" - Radicals: {len(RADICALS_DATA)}")
    print(f" - Characters: {len(SAMPLE_CHAR_MAPPING)}")
    print(f" - Lexicon entries: {len(full_lexicon)}")


if __name__ == "__main__":
    main()
