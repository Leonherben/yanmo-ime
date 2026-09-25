"""
Data models for YanMo IME (言墨输入法).
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Set


class InputMode(Enum):
    IDLE = auto()               # 空闲状态
    COMPOSING = auto()          # 拼音输入组合状态
    RADICAL_FILTER = auto()     # Tab 辅码部首过滤状态


@dataclass
class RadicalInfo:
    id: int
    radical: str
    variants: List[str]
    pinyin: List[str]
    strokes: int
    name: str


@dataclass
class Candidate:
    text: str                   # 候选文本，如 "河"
    pinyin: str                 # 拼音，如 "he"
    freq: int                   # 词频
    radical: Optional[str] = None      # 所属部首，如 "氵"
    comment: Optional[str] = None      # 提示说明，如 "氵/水部"
    is_radical_matched: bool = False   # 是否由部首精确筛选中


@dataclass
class EngineState:
    mode: InputMode = InputMode.IDLE
    pinyin_buffer: str = ""            # 当前拼音输入，例如 "he"
    radical_buffer: str = ""           # 当前部首输入，例如 "shui"
    candidates: List[Candidate] = field(default_factory=list)
    selected_index: int = 0
    committed_text: str = ""           # 本次已上屏文本
