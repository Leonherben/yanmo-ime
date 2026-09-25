"""
Data generation script for YanMo IME (言墨输入法).
Generates:
1. data/radicals/radicals.json (Radicals, variants, pinyins, strokes, first_stroke)
2. data/radicals/char_radicals.json (Character -> radical & component mapping)
3. data/dict/core_lexicon.json (Core pinyin dictionary with frequencies)
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RADICALS_DIR = DATA_DIR / "radicals"
DICT_DIR = DATA_DIR / "dict"

RADICALS_DIR.mkdir(parents=True, exist_ok=True)
DICT_DIR.mkdir(parents=True, exist_ok=True)

# 214 Standard Radicals + Common Variants + Pinyins + Stroke Count + First Stroke (h/s/p/d/z)
# h: 横 (一)
# s: 竖 (丨)
# p: 撇 (丿)
# d: 点/捺 (丶)
# z: 折 (乙)
RADICALS_DATA = [
    # 1画
    {"id": 1, "radical": "一", "variants": ["一"], "pinyin": ["yi"], "strokes": 1, "name": "一部", "first_stroke": "h"},
    {"id": 2, "radical": "丨", "variants": ["丨"], "pinyin": ["gun", "shu"], "strokes": 1, "name": "竖笔", "first_stroke": "s"},
    {"id": 3, "radical": "丿", "variants": ["丿"], "pinyin": ["pie"], "strokes": 1, "name": "撇笔", "first_stroke": "p"},
    {"id": 4, "radical": "丶", "variants": ["丶"], "pinyin": ["dian"], "strokes": 1, "name": "点笔", "first_stroke": "d"},
    {"id": 5, "radical": "乙", "variants": ["乙", "乛", "乚", "⺄"], "pinyin": ["yi", "zhe"], "strokes": 1, "name": "乙部", "first_stroke": "z"},
    {"id": 6, "radical": "亅", "variants": ["亅"], "pinyin": ["jue", "gou"], "strokes": 1, "name": "竖钩", "first_stroke": "s"},

    # 2画
    {"id": 7, "radical": "二", "variants": ["二"], "pinyin": ["er"], "strokes": 2, "name": "二部", "first_stroke": "h"},
    {"id": 8, "radical": "亠", "variants": ["亠"], "pinyin": ["tou"], "strokes": 2, "name": "点横/六字头", "first_stroke": "d"},
    {"id": 9, "radical": "人", "variants": ["人", "亻", "入"], "pinyin": ["ren", "danren"], "strokes": 2, "name": "人部/单人旁", "first_stroke": "p"},
    {"id": 10, "radical": "儿", "variants": ["儿"], "pinyin": ["er"], "strokes": 2, "name": "儿部/儿字底", "first_stroke": "p"},
    {"id": 11, "radical": "八", "variants": ["八", "丷"], "pinyin": ["ba"], "strokes": 2, "name": "八部", "first_stroke": "p"},
    {"id": 12, "radical": "冂", "variants": ["冂"], "pinyin": ["tong", "tongzi"], "strokes": 2, "name": "同字框", "first_stroke": "s"},
    {"id": 13, "radical": "冖", "variants": ["冖"], "pinyin": ["mi", "tubaogai"], "strokes": 2, "name": "秃宝盖", "first_stroke": "d"},
    {"id": 14, "radical": "冫", "variants": ["冫"], "pinyin": ["bing", "liangdianshui"], "strokes": 2, "name": "两点水", "first_stroke": "d"},
    {"id": 15, "radical": "几", "variants": ["几"], "pinyin": ["ji"], "strokes": 2, "name": "几部", "first_stroke": "p"},
    {"id": 16, "radical": "凵", "variants": ["凵"], "pinyin": ["qu", "kua"], "strokes": 2, "name": "凶字框", "first_stroke": "s"},
    {"id": 17, "radical": "刀", "variants": ["刀", "刂"], "pinyin": ["dao", "lidao"], "strokes": 2, "name": "刀部/立刀旁", "first_stroke": "z"},
    {"id": 18, "radical": "力", "variants": ["力"], "pinyin": ["li"], "strokes": 2, "name": "力部", "first_stroke": "z"},
    {"id": 19, "radical": "勹", "variants": ["勹"], "pinyin": ["bao"], "strokes": 2, "name": "包字头", "first_stroke": "p"},
    {"id": 20, "radical": "匕", "variants": ["匕"], "pinyin": ["bi"], "strokes": 2, "name": "匕部", "first_stroke": "p"},
    {"id": 21, "radical": "匚", "variants": ["匚"], "pinyin": ["fang"], "strokes": 2, "name": "三框儿", "first_stroke": "h"},
    {"id": 22, "radical": "十", "variants": ["十"], "pinyin": ["shi"], "strokes": 2, "name": "十字儿", "first_stroke": "h"},
    {"id": 23, "radical": "卜", "variants": ["卜"], "pinyin": ["bu"], "strokes": 2, "name": "卜字旁", "first_stroke": "s"},
    {"id": 24, "radical": "卩", "variants": ["卩", "阝"], "pinyin": ["jie", "daner", "erdao"], "strokes": 2, "name": "单耳旁/耳刀", "first_stroke": "z"},
    {"id": 25, "radical": "厂", "variants": ["厂"], "pinyin": ["chang"], "strokes": 2, "name": "厂部/偏厂儿", "first_stroke": "h"},
    {"id": 26, "radical": "厶", "variants": ["厶"], "pinyin": ["si"], "strokes": 2, "name": "私字儿", "first_stroke": "z"},
    {"id": 27, "radical": "又", "variants": ["又"], "pinyin": ["you"], "strokes": 2, "name": "又部", "first_stroke": "z"},

    # 3画
    {"id": 28, "radical": "口", "variants": ["口"], "pinyin": ["kou"], "strokes": 3, "name": "口字旁", "first_stroke": "s"},
    {"id": 29, "radical": "囗", "variants": ["囗"], "pinyin": ["wei", "daguo"], "strokes": 3, "name": "大口框/国字框", "first_stroke": "s"},
    {"id": 30, "radical": "土", "variants": ["土"], "pinyin": ["tu", "tizi"], "strokes": 3, "name": "提土旁/土部", "first_stroke": "h"},
    {"id": 31, "radical": "士", "variants": ["士"], "pinyin": ["shi"], "strokes": 3, "name": "士部", "first_stroke": "h"},
    {"id": 32, "radical": "夂", "variants": ["夂"], "pinyin": ["zhi"], "strokes": 3, "name": "反文头/夂部", "first_stroke": "p"},
    {"id": 33, "radical": "夕", "variants": ["夕"], "pinyin": ["xi"], "strokes": 3, "name": "夕部/夕字旁", "first_stroke": "p"},
    {"id": 34, "radical": "大", "variants": ["大"], "pinyin": ["da"], "strokes": 3, "name": "大部/大字头", "first_stroke": "h"},
    {"id": 35, "radical": "女", "variants": ["女"], "pinyin": ["nv", "nu"], "strokes": 3, "name": "女字旁", "first_stroke": "z"},
    {"id": 36, "radical": "子", "variants": ["子"], "pinyin": ["zi"], "strokes": 3, "name": "子字旁", "first_stroke": "z"},
    {"id": 37, "radical": "宀", "variants": ["宀"], "pinyin": ["mian", "baogai"], "strokes": 3, "name": "宝盖头", "first_stroke": "d"},
    {"id": 38, "radical": "寸", "variants": ["寸"], "pinyin": ["cun"], "strokes": 3, "name": "寸部/寸字旁", "first_stroke": "h"},
    {"id": 39, "radical": "小", "variants": ["小", "⺌"], "pinyin": ["xiao"], "strokes": 3, "name": "小部/小字头", "first_stroke": "s"},
    {"id": 40, "radical": "尸", "variants": ["尸"], "pinyin": ["shi"], "strokes": 3, "name": "尸部/尸字头", "first_stroke": "z"},
    {"id": 41, "radical": "山", "variants": ["山"], "pinyin": ["shan"], "strokes": 3, "name": "山字旁", "first_stroke": "s"},
    {"id": 42, "radical": "巛", "variants": ["巛", "川"], "pinyin": ["chuan"], "strokes": 3, "name": "三拐儿/川部", "first_stroke": "p"},
    {"id": 43, "radical": "工", "variants": ["工"], "pinyin": ["gong"], "strokes": 3, "name": "工部", "first_stroke": "h"},
    {"id": 44, "radical": "己", "variants": ["己", "已", "巳"], "pinyin": ["ji"], "strokes": 3, "name": "己部", "first_stroke": "z"},
    {"id": 45, "radical": "巾", "variants": ["巾"], "pinyin": ["jin"], "strokes": 3, "name": "巾字旁", "first_stroke": "s"},
    {"id": 46, "radical": "干", "variants": ["干"], "pinyin": ["gan"], "strokes": 3, "name": "干部", "first_stroke": "h"},
    {"id": 47, "radical": "幺", "variants": ["幺"], "pinyin": ["yao"], "strokes": 3, "name": "幺部/幺字旁", "first_stroke": "z"},
    {"id": 48, "radical": "广", "variants": ["广"], "pinyin": ["guang"], "strokes": 3, "name": "广字旁", "first_stroke": "d"},
    {"id": 49, "radical": "廴", "variants": ["廴"], "pinyin": ["yin", "jianzhidi"], "strokes": 3, "name": "建字底", "first_stroke": "z"},
    {"id": 50, "radical": "弓", "variants": ["弓"], "pinyin": ["gong"], "strokes": 3, "name": "弓字旁", "first_stroke": "z"},
    {"id": 51, "radical": "彡", "variants": ["彡"], "pinyin": ["shan", "sanpie"], "strokes": 3, "name": "三撇儿", "first_stroke": "p"},
    {"id": 52, "radical": "彳", "variants": ["彳"], "pinyin": ["chi", "shuangren"], "strokes": 3, "name": "双人旁", "first_stroke": "p"},
    {"id": 53, "radical": "心", "variants": ["心", "忄", "⺗"], "pinyin": ["xin", "shuxin"], "strokes": 4, "name": "心字底/竖心旁", "first_stroke": "d"},
    {"id": 54, "radical": "戈", "variants": ["戈"], "pinyin": ["ge"], "strokes": 4, "name": "戈部", "first_stroke": "h"},
    {"id": 55, "radical": "户", "variants": ["户", "戶"], "pinyin": ["hu"], "strokes": 4, "name": "户字头", "first_stroke": "d"},
    {"id": 56, "radical": "手", "variants": ["手", "扌"], "pinyin": ["shou", "tishou"], "strokes": 4, "name": "提手旁", "first_stroke": "h"},
    {"id": 57, "radical": "支", "variants": ["支"], "pinyin": ["zhi"], "strokes": 4, "name": "支部", "first_stroke": "h"},
    {"id": 58, "radical": "攴", "variants": ["攴", "攵"], "pinyin": ["pu", "fanwen"], "strokes": 4, "name": "反文旁", "first_stroke": "p"},
    {"id": 59, "radical": "文", "variants": ["文"], "pinyin": ["wen"], "strokes": 4, "name": "文字头", "first_stroke": "d"},
    {"id": 60, "radical": "斗", "variants": ["斗"], "pinyin": ["dou"], "strokes": 4, "name": "斗部", "first_stroke": "d"},
    {"id": 61, "radical": "斤", "variants": ["斤"], "pinyin": ["jin"], "strokes": 4, "name": "斤字旁", "first_stroke": "p"},
    {"id": 62, "radical": "方", "variants": ["方"], "pinyin": ["fang"], "strokes": 4, "name": "方字旁", "first_stroke": "d"},
    {"id": 63, "radical": "日", "variants": ["日"], "pinyin": ["ri"], "strokes": 4, "name": "日字旁", "first_stroke": "s"},
    {"id": 64, "radical": "曰", "variants": ["曰"], "pinyin": ["yue"], "strokes": 4, "name": "曰部", "first_stroke": "s"},
    {"id": 65, "radical": "月", "variants": ["月"], "pinyin": ["yue", "rou"], "strokes": 4, "name": "月字旁/肉月旁", "first_stroke": "p"},
    {"id": 66, "radical": "木", "variants": ["木"], "pinyin": ["mu"], "strokes": 4, "name": "木字旁", "first_stroke": "h"},
    {"id": 67, "radical": "欠", "variants": ["欠"], "pinyin": ["qian"], "strokes": 4, "name": "欠字旁", "first_stroke": "p"},
    {"id": 68, "radical": "止", "variants": ["止"], "pinyin": ["zhi"], "strokes": 4, "name": "止部", "first_stroke": "s"},
    {"id": 69, "radical": "歹", "variants": ["歹"], "pinyin": ["dai"], "strokes": 4, "name": "歹字旁", "first_stroke": "h"},
    {"id": 70, "radical": "殳", "variants": ["殳"], "pinyin": ["shu"], "strokes": 4, "name": "殳部", "first_stroke": "p"},
    {"id": 71, "radical": "毛", "variants": ["毛"], "pinyin": ["mao"], "strokes": 4, "name": "毛部", "first_stroke": "p"},
    {"id": 72, "radical": "氏", "variants": ["氏"], "pinyin": ["shi"], "strokes": 4, "name": "氏部", "first_stroke": "p"},
    {"id": 73, "radical": "气", "variants": ["气"], "pinyin": ["qi"], "strokes": 4, "name": "气字头", "first_stroke": "p"},
    {"id": 74, "radical": "水", "variants": ["水", "氵", "氺"], "pinyin": ["shui", "sandianshui"], "strokes": 4, "name": "三点水/水部", "first_stroke": "d"},
    {"id": 75, "radical": "火", "variants": ["火", "灬"], "pinyin": ["huo", "sidiandian"], "strokes": 4, "name": "火字旁/四点底", "first_stroke": "d"},
    {"id": 76, "radical": "爪", "variants": ["爪", "爫"], "pinyin": ["zhao", "zhua"], "strokes": 4, "name": "爪字头", "first_stroke": "p"},
    {"id": 77, "radical": "父", "variants": ["父"], "pinyin": ["fu"], "strokes": 4, "name": "父字头", "first_stroke": "p"},
    {"id": 78, "radical": "牛", "variants": ["牛", "牜"], "pinyin": ["niu"], "strokes": 4, "name": "牛字旁", "first_stroke": "p"},
    {"id": 79, "radical": "犬", "variants": ["犬", "犭"], "pinyin": ["quan", "fanquan"], "strokes": 4, "name": "反犬旁", "first_stroke": "p"},
    {"id": 80, "radical": "王", "variants": ["王", "玉"], "pinyin": ["wang", "yu"], "strokes": 4, "name": "王字旁/玉部", "first_stroke": "h"},
    {"id": 81, "radical": "田", "variants": ["田"], "pinyin": ["tian"], "strokes": 5, "name": "田字旁", "first_stroke": "s"},
    {"id": 82, "radical": "疒", "variants": ["疒"], "pinyin": ["bing", "bingzi"], "strokes": 5, "name": "病字头", "first_stroke": "d"},
    {"id": 83, "radical": "白", "variants": ["白"], "pinyin": ["bai"], "strokes": 5, "name": "白字旁", "first_stroke": "p"},
    {"id": 84, "radical": "皮", "variants": ["皮"], "pinyin": ["pi"], "strokes": 5, "name": "皮部", "first_stroke": "z"},
    {"id": 85, "radical": "皿", "variants": ["皿"], "pinyin": ["min", "mindi"], "strokes": 5, "name": "皿字底", "first_stroke": "s"},
    {"id": 86, "radical": "目", "variants": ["目"], "pinyin": ["mu"], "strokes": 5, "name": "目字旁", "first_stroke": "s"},
    {"id": 87, "radical": "石", "variants": ["石"], "pinyin": ["shi"], "strokes": 5, "name": "石字旁", "first_stroke": "h"},
    {"id": 88, "radical": "示", "variants": ["示", "礻"], "pinyin": ["shi"], "strokes": 5, "name": "示字旁/示部", "first_stroke": "d"},
    {"id": 89, "radical": "禾", "variants": ["禾"], "pinyin": ["he"], "strokes": 5, "name": "禾木旁", "first_stroke": "p"},
    {"id": 90, "radical": "穴", "variants": ["穴"], "pinyin": ["xue"], "strokes": 5, "name": "穴宝盖", "first_stroke": "d"},
    {"id": 91, "radical": "立", "variants": ["立"], "pinyin": ["li"], "strokes": 5, "name": "立字旁", "first_stroke": "d"},
    {"id": 92, "radical": "竹", "variants": ["竹", "⺮"], "pinyin": ["zhu"], "strokes": 6, "name": "竹字头", "first_stroke": "p"},
    {"id": 93, "radical": "米", "variants": ["米"], "pinyin": ["mi"], "strokes": 6, "name": "米字旁", "first_stroke": "d"},
    {"id": 94, "radical": "糸", "variants": ["糸", "纟"], "pinyin": ["si", "jiaoisi"], "strokes": 6, "name": "绞丝旁", "first_stroke": "z"},
    {"id": 95, "radical": "缶", "variants": ["缶"], "pinyin": ["fou"], "strokes": 6, "name": "缶部", "first_stroke": "p"},
    {"id": 96, "radical": "羊", "variants": ["羊", "⺷"], "pinyin": ["yang"], "strokes": 6, "name": "羊字头/羊部", "first_stroke": "d"},
    {"id": 97, "radical": "羽", "variants": ["羽"], "pinyin": ["yu"], "strokes": 6, "name": "羽字旁", "first_stroke": "z"},
    {"id": 98, "radical": "老", "variants": ["老", "耂"], "pinyin": ["lao"], "strokes": 6, "name": "老字头", "first_stroke": "h"},
    {"id": 99, "radical": "耳", "variants": ["耳"], "pinyin": ["er"], "strokes": 6, "name": "耳字旁", "first_stroke": "h"},
    {"id": 100, "radical": "舌", "variants": ["舌"], "pinyin": ["she"], "strokes": 6, "name": "舌字旁", "first_stroke": "p"},
    {"id": 101, "radical": "舟", "variants": ["舟"], "pinyin": ["zhou"], "strokes": 6, "name": "舟字旁", "first_stroke": "p"},
    {"id": 102, "radical": "艮", "variants": ["艮"], "pinyin": ["gen"], "strokes": 6, "name": "艮部", "first_stroke": "z"},
    {"id": 103, "radical": "艸", "variants": ["艸", "艹"], "pinyin": ["cao", "caozitou"], "strokes": 6, "name": "草字头", "first_stroke": "h"},
    {"id": 104, "radical": "虍", "variants": ["虍"], "pinyin": ["hu", "huzi"], "strokes": 6, "name": "虎字头", "first_stroke": "s"},
    {"id": 105, "radical": "虫", "variants": ["虫"], "pinyin": ["chong"], "strokes": 6, "name": "虫字旁", "first_stroke": "s"},
    {"id": 106, "radical": "血", "variants": ["血"], "pinyin": ["xue"], "strokes": 6, "name": "血部", "first_stroke": "p"},
    {"id": 107, "radical": "行", "variants": ["行"], "pinyin": ["xing"], "strokes": 6, "name": "行部", "first_stroke": "p"},
    {"id": 108, "radical": "衣", "variants": ["衣", "衤"], "pinyin": ["yi"], "strokes": 6, "name": "衣字旁/衣部", "first_stroke": "d"},
    {"id": 109, "radical": "見", "variants": ["见", "見"], "pinyin": ["jian"], "strokes": 7, "name": "见字旁", "first_stroke": "s"},
    {"id": 110, "radical": "角", "variants": ["角"], "pinyin": ["jiao"], "strokes": 7, "name": "角字旁", "first_stroke": "p"},
    {"id": 111, "radical": "言", "variants": ["言", "讠"], "pinyin": ["yan"], "strokes": 7, "name": "言字旁", "first_stroke": "d"},
    {"id": 112, "radical": "谷", "variants": ["谷"], "pinyin": ["gu"], "strokes": 7, "name": "谷部", "first_stroke": "p"},
    {"id": 113, "radical": "豆", "variants": ["豆"], "pinyin": ["dou"], "strokes": 7, "name": "豆部", "first_stroke": "h"},
    {"id": 114, "radical": "豕", "variants": ["豕"], "pinyin": ["shi"], "strokes": 7, "name": "豕部", "first_stroke": "h"},
    {"id": 115, "radical": "貝", "variants": ["贝", "貝"], "pinyin": ["bei"], "strokes": 7, "name": "贝字旁", "first_stroke": "s"},
    {"id": 116, "radical": "赤", "variants": ["赤"], "pinyin": ["chi"], "strokes": 7, "name": "赤部", "first_stroke": "土"},
    {"id": 117, "radical": "走", "variants": ["走"], "pinyin": ["zou"], "strokes": 7, "name": "走字底", "first_stroke": "h"},
    {"id": 118, "radical": "足", "variants": ["足", "⻊"], "pinyin": ["zu"], "strokes": 7, "name": "足字旁", "first_stroke": "s"},
    {"id": 119, "radical": "身", "variants": ["身"], "pinyin": ["shen"], "strokes": 7, "name": "身字旁", "first_stroke": "p"},
    {"id": 120, "radical": "車", "variants": ["车", "車"], "pinyin": ["che"], "strokes": 7, "name": "车字旁", "first_stroke": "h"},
    {"id": 121, "radical": "辛", "variants": ["辛"], "pinyin": ["xin"], "strokes": 7, "name": "辛部", "first_stroke": "d"},
    {"id": 122, "radical": "辵", "variants": ["辵", "辶"], "pinyin": ["chuo", "zouzhi"], "strokes": 7, "name": "走之底", "first_stroke": "d"},
    {"id": 123, "radical": "邑", "variants": ["邑", "阝"], "pinyin": ["yi", "youerdao"], "strokes": 7, "name": "右耳旁", "first_stroke": "s"},
    {"id": 124, "radical": "酉", "variants": ["酉"], "pinyin": ["you"], "strokes": 7, "name": "酉字旁", "first_stroke": "h"},
    {"id": 125, "radical": "里", "variants": ["里"], "pinyin": ["li"], "strokes": 7, "name": "里字旁", "first_stroke": "s"},
    {"id": 126, "radical": "金", "variants": ["金", "钅"], "pinyin": ["jin"], "strokes": 8, "name": "金字旁", "first_stroke": "p"},
    {"id": 127, "radical": "門", "variants": ["门", "門"], "pinyin": ["men"], "strokes": 8, "name": "门字框", "first_stroke": "d"},
    {"id": 128, "radical": "阜", "variants": ["阜", "阝"], "pinyin": ["fu", "zuoerdao"], "strokes": 8, "name": "左耳旁", "first_stroke": "z"},
    {"id": 129, "radical": "隹", "variants": ["隹"], "pinyin": ["zhui"], "strokes": 8, "name": "隹字旁", "first_stroke": "p"},
    {"id": 130, "radical": "雨", "variants": ["雨", "⻗"], "pinyin": ["yu"], "strokes": 8, "name": "雨字头", "first_stroke": "h"},
    {"id": 131, "radical": "青", "variants": ["青"], "pinyin": ["qing"], "strokes": 8, "name": "青部", "first_stroke": "h"},
    {"id": 132, "radical": "非", "variants": ["非"], "pinyin": ["fei"], "strokes": 8, "name": "非部", "first_stroke": "s"},
    {"id": 133, "radical": "革", "variants": ["革"], "pinyin": ["ge"], "strokes": 9, "name": "革字旁", "first_stroke": "h"},
    {"id": 134, "radical": "音", "variants": ["音"], "pinyin": ["yin"], "strokes": 9, "name": "音字旁", "first_stroke": "d"},
    {"id": 135, "radical": "頁", "variants": ["页", "頁"], "pinyin": ["ye"], "strokes": 9, "name": "页字旁", "first_stroke": "h"},
    {"id": 136, "radical": "風", "variants": ["风", "風"], "pinyin": ["feng"], "strokes": 9, "name": "风字旁", "first_stroke": "p"},
    {"id": 137, "radical": "飛", "variants": ["飞", "飛"], "pinyin": ["fei"], "strokes": 9, "name": "飞部", "first_stroke": "z"},
    {"id": 138, "radical": "食", "variants": ["食", "饣"], "pinyin": ["shi"], "strokes": 9, "name": "食字旁", "first_stroke": "p"},
    {"id": 139, "radical": "首", "variants": ["首"], "pinyin": ["shou"], "strokes": 9, "name": "首部", "first_stroke": "d"},
    {"id": 140, "radical": "香", "variants": ["香"], "pinyin": ["xiang"], "strokes": 9, "name": "香字旁", "first_stroke": "p"},
    {"id": 141, "radical": "馬", "variants": ["马", "馬"], "pinyin": ["ma"], "strokes": 10, "name": "马字旁", "first_stroke": "z"},
    {"id": 142, "radical": "骨", "variants": ["骨"], "pinyin": ["gu"], "strokes": 10, "name": "骨字旁", "first_stroke": "s"},
    {"id": 143, "radical": "高", "variants": ["高"], "pinyin": ["gao"], "strokes": 10, "name": "高部", "first_stroke": "d"},
    {"id": 144, "radical": "鬼", "variants": ["鬼"], "pinyin": ["gui"], "strokes": 10, "name": "鬼部", "first_stroke": "p"},
    {"id": 145, "radical": "魚", "variants": ["鱼", "魚"], "pinyin": ["yu"], "strokes": 11, "name": "鱼字旁", "first_stroke": "p"},
    {"id": 146, "radical": "鳥", "variants": ["鸟", "鳥"], "pinyin": ["niao"], "strokes": 11, "name": "鸟字旁", "first_stroke": "p"},
    {"id": 147, "radical": "鹵", "variants": ["卤", "鹵"], "pinyin": ["lu"], "strokes": 11, "name": "卤部", "first_stroke": "s"},
    {"id": 148, "radical": "鹿", "variants": ["鹿"], "pinyin": ["lu"], "strokes": 11, "name": "鹿字旁", "first_stroke": "d"},
    {"id": 149, "radical": "麥", "variants": ["麦", "麥"], "pinyin": ["mai"], "strokes": 11, "name": "麦字旁", "first_stroke": "h"},
    {"id": 150, "radical": "麻", "variants": ["麻"], "pinyin": ["ma"], "strokes": 11, "name": "麻部", "first_stroke": "d"},
    {"id": 151, "radical": "黄", "variants": ["黄", "黃"], "pinyin": ["huang"], "strokes": 12, "name": "黄部", "first_stroke": "h"},
    {"id": 152, "radical": "黑", "variants": ["黑"], "pinyin": ["hei"], "strokes": 12, "name": "黑字旁", "first_stroke": "s"},
    {"id": 153, "radical": "鼎", "variants": ["鼎"], "pinyin": ["ding"], "strokes": 13, "name": "鼎部", "first_stroke": "s"},
    {"id": 154, "radical": "鼓", "variants": ["鼓"], "pinyin": ["gu"], "strokes": 13, "name": "鼓部", "first_stroke": "h"},
    {"id": 155, "radical": "鼠", "variants": ["鼠"], "pinyin": ["shu"], "strokes": 13, "name": "鼠部", "first_stroke": "p"},
    {"id": 156, "radical": "鼻", "variants": ["鼻"], "pinyin": ["bi"], "strokes": 14, "name": "鼻字旁", "first_stroke": "p"},
    {"id": 157, "radical": "齒", "variants": ["齿", "齒"], "pinyin": ["chi"], "strokes": 15, "name": "齿字旁", "first_stroke": "s"},
    {"id": 158, "radical": "龍", "variants": ["龙", "龍"], "pinyin": ["long"], "strokes": 16, "name": "龙部", "first_stroke": "d"}
]


def main():
    print(f"Updating {RADICALS_DIR / 'radicals.json'} with first_stroke (h/s/p/d/z)...")
    with open(RADICALS_DIR / "radicals.json", "w", encoding="utf-8") as f:
        json.dump(RADICALS_DATA, f, ensure_ascii=False, indent=2)

    print("Radicals data updated successfully!")


if __name__ == "__main__":
    main()
