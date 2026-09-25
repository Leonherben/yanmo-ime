"""
Export YanMo lexicon and radical dictionary into RIME schema and dictionary format.
Generates rime/yanmo.schema.yaml and rime/yanmo.dict.yaml for Fcitx-Rime compatibility.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RIME_DIR = BASE_DIR / "rime"
RIME_DIR.mkdir(parents=True, exist_ok=True)


def generate_rime_schema():
    schema_content = """# Rime schema
# encoding: utf-8

schema:
  schema_id: yanmo
  name: "言墨拼音"
  version: "1.0"
  author:
    - "Leonherben"
  description: |
    言墨输入法 (YanMo IME) - 拼音与部首辅码 Rime 适配方案
  dependencies:
    - stroke

switches:
  - name: ascii_mode
    reset: 0
    states: [ 中文, 西文 ]
  - name: full_shape
    states: [ 半角, 全角 ]
  - name: simplification
    reset: 1
    states: [ 漢字, 汉字 ]
  - name: ascii_punct
    states: [ 。，, ．， ]

engine:
  processors:
    - ascii_composer
    - recognizer
    - key_binder
    - speller
    - punctuator
    - selector
    - navigator
    - express_editor
  segmentors:
    - ascii_segmentor
    - matcher
    - abc_segmentor
    - punct_segmentor
    - fallback_segmentor
  translators:
    - punct_translator
    - script_translator
  filters:
    - simplifier
    - uniquifier

speller:
  alphabet: zyxwvutsrqponmlkjihgfedcba
  initials: zyxwvutsrqponmlkjihgfedcba
  delimiter: " '"
  algebra:
    - erase/^xx$/
    - abbrev/^([a-z]).+$/$1/

translator:
  dictionary: yanmo
  preedit_format:
    - xform/([nl])v/$1ü/
    - xform/([nl])ue/$1üe/
    - xform/([jqxy])v/$1u/

punctuator:
  import_preset: default

key_binder:
  import_preset: default
"""
    schema_file = RIME_DIR / "yanmo.schema.yaml"
    schema_file.write_text(schema_content, encoding="utf-8")
    print(f"Generated {schema_file}")


def generate_rime_dict():
    # Load core lexicon and char radicals
    lexicon_file = DATA_DIR / "dict" / "core_lexicon.json"
    char_rad_file = DATA_DIR / "radicals" / "char_radicals.json"
    entries = []
    seen = set()

    if lexicon_file.exists():
        with open(lexicon_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                text = item.get("word", "")
                pinyin = item.get("pinyin", "")
                freq = item.get("freq", 1000)
                if text and pinyin and (text, pinyin) not in seen:
                    seen.add((text, pinyin))
                    entries.append((text, pinyin, freq))

    if char_rad_file.exists():
        with open(char_rad_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for ch, info in data.items():
                py = info.get("pinyin", "")
                freq = info.get("freq", 1000)
                if ch and py and (ch, py) not in seen:
                    seen.add((ch, py))
                    entries.append((ch, py, freq))

    header = """# Rime dictionary
# encoding: utf-8
#
# YanMo IME Base Dictionary

---
name: yanmo
version: "1.0"
sort: by_weight
use_preset_vocabulary: true
...

"""
    dict_file = RIME_DIR / "yanmo.dict.yaml"
    with open(dict_file, "w", encoding="utf-8") as f:
        f.write(header)
        for text, py, freq in entries:
            f.write(f"{text}\t{py}\t{freq}\n")

    print(f"Generated {dict_file} with {len(entries)} words")


def main():
    generate_rime_schema()
    generate_rime_dict()
    print("Rime bridge generation complete!")


if __name__ == "__main__":
    main()
