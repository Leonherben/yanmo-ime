# 言墨输入法 (YanMo IME)

> **声形兼备，轻巧自如** —— 面向现代 Linux 与跨平台桌面的轻量自用输入法。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux%20%7C%20Cross--Platform-brightgreen.svg)]()
[![Status: Planning & Prototyping](https://img.shields.io/badge/Status-Prototyping-orange.svg)]()

---

## 📖 项目愿景

**言墨 (YanMo)** 旨在打造一款真正属于自己的极简、高效、现代化的桌面输入法。
- **“言”**：集成本地轻量离线语音听写，随时一键长按录音、毫秒级精准转写上屏。
- **“墨”**：基于汉字部件拆解与部首（IDS）辅助检索，遇到同音字或生僻字时，通过部首精准定位，告别大海捞针翻页。
- **“轻”**：拒绝臃肿的云端监控与冗余进程，常驻后台极低内存占用（<15MB 核心），专为高流畅度打字与中低资源设备优化。

---

## ✨ 核心特性

### 1. 🔠 双轨部首过滤与拆字检索
- **键盘盲打流 (`Tab` 辅码)**：输入拼音（如 `he`）后，直接按下 `Tab` 键即可输入部首拼音（如 `shui`）或首笔画，候选项即刻收敛为水部字（河、涸、渮等）。
- **触屏/鼠标视觉流（右上角 `[部首 ▾]` 按钮）**：候选框右上角常驻部首面板入口，点击即展开常用部首网格，触屏一点即过滤，生僻字与易混字查字更轻松。
- **构件拆字输入**：支持依据汉字表意描述序列（IDS）直接拆解拼装生僻字（如输入部件拼音直接组字）。

### 2. 📚 极速多层词库系统
- **零延迟启动**：核心词库采用紧凑前缀树（Trie）与内存映射（mmap）机制，毫秒级冷启动，按需读取。
- **用户自造词与频次学习**：自动记忆个性化短语与词频，支持一键纯文本导出与备份。
- **离线词库生成链**：词库构建与清洗工具基于现代化 `uv` 驱动，轻巧便捷。

### 3. 🎙️ 本地离线轻量语音输入
- **安全私密**：完全离线运行，无需联网上传录音数据。
- **超低硬件开销**：集成基于 Sherpa-ONNX 的微型语音识别引擎（SenseVoice-Small INT8），内存开销低，无需独立显卡，在 CPU 上即可实现高倍速实时推理。
- **即按即说**：支持全局快捷键长按录音，松开即上屏。

---

## 🏛️ 整体架构设计（大脑与外壳分离）

为了保证**当下在 Linux Mint 上极致轻快**，同时**未来轻松迁移至 Windows / macOS**，言墨采用“内核（Core）与适配层（Adapter）解耦”的工业级架构：

```text
┌────────────────────────────────────────────────────────┐
│               外壳层（OS 交互与界面 UI）                │
│  [现阶段] Linux: Fcitx 桥接 / 轻量悬浮窗               │
│  [规划中] Windows (TSF) / macOS (InputMethodKit)       │
└───────────────────────────┬────────────────────────────┘
                            │ (调用接口: 标准 C ABI / IPC)
┌───────────────────────────▼────────────────────────────┐
│              言墨核心引擎（yanmo-core）                   │
│   ★ 跨平台通用纯逻辑，毫秒级响应，极低内存消耗          │
│   ├── 1. 拼音分词与检索器 (Pinyin Matcher)             │
│   ├── 2. 部首反查与构件过滤树 (Radical/IDS Indexer)    │
│   ├── 3. 分级词库与词频引擎 (Lexicon Trie & SQLite)    │
│   └── 4. 离线语音转写调度器 (Sherpa-ONNX ASR Bridge)   │
└────────────────────────────────────────────────────────┘
```

详见架构设计文档：[docs/architecture.md](docs/architecture.md)。

---

## 📂 项目结构

```text
yanmo-ime/
├── docs/                   # 架构设计、交互规范与数据格式规范
│   ├── architecture.md     # 核心分层架构详细说明
│   └── interaction.md      # 键盘输入、Tab部首过滤与语音按键交互指南
├── data/                   # 词库与汉字构件基础数据
│   ├── radicals/           # 部首表与 IDS 汉字拆解数据库
│   └── dict/               # 基础词库源文本与词频数据
├── tools/                  # 离线词库编译与部首数据提取工具 (Python + uv)
│   ├── pyproject.toml      # uv 项目配置文件
│   └── build_dict.py       # 词库打包构建脚本
└── README.md
```

---

## 🚀 开发路线图 (Roadmap)

- [x] **Phase 0: 项目立项与规范确立** (已完成)
  - 确立项目命名：言墨 (`yanmo-ime`)
  - 确立“大脑与外壳分离”可迁移架构
  - 规范键盘 `Tab` 辅码 + 右上角触控面板的双轨交互
- [x] **Phase 1: 汉字部件/部首数据库与检索原型** (已完成)
  - 导入 214 康熙部首与常用变体数据库 (`data/radicals/radicals.json`)
  - 建立常用汉字部首反查与拆解索引 (`data/radicals/char_radicals.json`)
  - 终端交互式验证原型 (`yanmo_cli.py`)
- [x] **Phase 2: 拼音与多层自学习词库引擎** (已完成)
  - 内存紧凑前缀树 Trie (`core/trie.py`) 实现 <1ms 快速拼音前缀索引
  - SQLite 用户个人自学词库 (`core/user_dict.py`)，打字选词自动加频与记忆
  - 复合匹配器与词库导出备份支持
- [x] **Phase 3: 桌面原生 GTK 3 悬浮条与五笔画直观部首面板** (已完成)
  - Linux 原生透明磨砂悬浮候选条 (`ui/candidate_window.py`, `ui/styles.css`)
  - **五大基本笔画全景部首面板** (`一 横 H`、`丨 竖 S`、`丿 撇 P`、`丶 点 D`、`乙 折 Z`) 全部直观在列
  - Tab 双模检索：支持部首拼音与首笔画单键自动聚焦过滤
  - 原生焦点保护与防夺焦点沙盒 (`yanmo_gui.py`)
- [x] **Phase 4: 本地离线轻量语音听写 (SenseVoice)** (已完成)
  - 基于 Sherpa-ONNX + SenseVoice-Small INT8 本地轻量模型 (~229MB)
  - 无需独立显卡，Surface / 普通 CPU 实时毫秒级离线解码
  - 悬浮候选条 `[🎙️ 语音]` 按钮与沙盒 `F2` 全局热键听写上屏
- [x] **Phase 5: 系统级输入法常驻守护进程与 Fcitx-Rime 桥接** (已完成)
  - 全局后台守护进程 (`bin/yanmo-daemon`、`daemon/yanmo_daemon.py`)
  - Linux Mint (Cinnamon / X11) 全局热键 `Ctrl + Space` 无缝切换中/英输入
  - 全局任意应用支持 **`v + 空格` 长按即说、松开即上屏**
  - 活动窗口焦点与光标自适应悬浮跟随 (`daemon/window_tracker.py`)
  - 任务栏系统托盘指示器 (`daemon/tray_indicator.py`) 与开机自启动
  - Fcitx-Rime 兼容桥接方案 (`rime/yanmo.schema.yaml`, `rime/yanmo.dict.yaml`)

---

## 🏃 快速上手与使用指南

### 1. 系统级全局常驻使用 (推荐)
无需打开测试窗口，直接在系统的任意应用（浏览器、代码编辑器、终端、办公套件）中使用言墨输入法：

```bash
# 启动言墨后台守护进程
yanmo-daemon start

# 检查运行状态
yanmo-daemon status

# 停止或重启
yanmo-daemon stop
yanmo-daemon restart
```

- **切换中/英文**：全局按下 **`Ctrl + Space`** 随时切换。
- **全局语音输入**：在任何窗口中长按 **`v + 空格`**，直接说话，**松开按键**立即秒级离线转写上屏！
- **部首查字与输入**：键入拼音后按 `Tab`，再敲笔画首键（如 `d` 点），候选条锁定水部字！
- **系统托盘**：屏幕右下角任务栏常驻“言”字托盘图标，右键可进行快速设置、开机自启切换与词库导出。

### 2. 独立沙盒体验窗口 (测试模式)
```bash
tools/.venv/bin/python yanmo_gui.py
```

### 3. Fcitx-Rime 方案桥接 (可选)
如果希望直接使用现有的 Fcitx 框架调度言墨词库：
```bash
cp rime/yanmo.* ~/.config/fcitx/rime/
# 在 fcitx-configtool 或 rime 方案列表中勾选 "言墨拼音"
```



