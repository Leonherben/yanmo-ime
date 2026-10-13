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

### 1. ⚡ C++20 纯原生核心加速
- **微秒级拼写代数 (Speller)**：单次击键拼写纠错与切分 $< 4\mu\text{s}$，基于 413 国标全拼音节进行无歧义 DAG 最优切分。
- **搜狗式智能纠错**：自动容错常见击键倒装（如 `zhaogn` $\to$ `zhang`，`dign` $\to$ `ding`，`liou` $\to$ `liu`）。
- **全简拼混合与前缀兜底**：输入 `shuosmn` 自动组词匹配“说什么呢”，未知音节自动回退至最大有效前缀，候选浮窗绝不白屏。
- **隔音符与模糊音**：支持 `'` 隔音切分（`xi'an` 优先“西安”）与平翘舌、前后鼻音自由切换。

### 2. 🧠 2-Gram 语言模型与 Viterbi 长句解码
- **智能整句联想**：集成高效二元语言模型（`BigramModel`），基于 Viterbi DP 算法自动求解高概率长句（如输入 `zenmeshuon` 直出“怎么说呢”）。
- **动态自适应学习**：用户选词后即刻动态学习词频与上下文搭配加权（选词即刻提至首选）。
- **成对智能标点**：双引号、括号等自动按顺序输出左/右匹配成对符号。

### 3. 🔠 双轨部首过滤与拆字检索
- **键盘盲打流 (`Tab` 辅码)**：输入拼音（如 `he`）后，直接按下 `Tab` 键即可输入部首拼音（如 `shui`）或首笔画，候选项即刻收敛为水部字（河、涸、渮等）。
- **触屏/鼠标视觉流（右上角 `[部首 ▾]` 按钮）**：候选框右上角常驻部首面板入口，点击即展开常用部首网格，触屏一点即过滤，生僻字与易混字查字更轻松。
- **构件拆字输入**：支持依据汉字表意描述序列（IDS）直接拆解拼装生僻字。

### 4. 🎙️ 本地离线轻量语音与异步 AI 辅助
- **安全私密语音 (Sherpa-ONNX)**：内置 SenseVoice-Small INT8 本地模型，待机 0% CPU 占用，全局长按 `v + 空格` 毫秒级语音秒速转写上屏。
- **非阻塞异步大模型辅助通道**：基于 C++ Future 与 Python 异步服务，开箱即用规则降噪（清洗“呃/那个”等口语助词），支持扩展对接本地 Ollama 或任意兼容 OpenAI 规范的云端大模型 API。

---

## 🏛️ 整体架构设计（大脑与外壳分离）

为了保证**当下在 Linux Mint 上极致轻快**，同时**未来轻松迁移至 Windows / macOS**，言墨采用“内核（Core）与适配层（Adapter）解耦”的工业级架构：

```text
┌────────────────────────────────────────────────────────┐
│               外壳层（OS 交互与桌面 UI）                │
│  - Linux: 键盘事件拦截、浮窗渲染、剪贴板/XTEST 注入     │
│  - 跨平台: Windows (TSF) / macOS (InputMethodKit) 规划 │
└───────────────────────────┬────────────────────────────┘
                            │ (调用接口: 标准 C ABI / IPC)
┌───────────────────────────▼────────────────────────────┐
│              言墨核心引擎（C++20 高性能内核）           │
│   ★ 跨平台通用纯逻辑，毫秒级响应，极低内存消耗          │
│   ├── 1. 拼写代数引擎 (Speller: 413音节/纠错/模糊/混输) │
│   ├── 2. 词库前缀树与检索器 (Pinyin/Abbrev Trie)        │
│   ├── 3. 语言模型与长句解码 (Bigram & Sentence Decoder) │
│   ├── 4. 部首反查与构件过滤树 (Radical/IDS Indexer)    │
│   ├── 5. 离线语音听写调度器 (Sherpa-ONNX Voice Bridge) │
│   └── 6. 异步大模型辅助通道 (ILLMProvider / Future)     │
└────────────────────────────────────────────────────────┘
```

详见架构设计文档：[docs/architecture.md](docs/architecture.md)。

---

## 📂 项目结构

```text
yanmo-ime/
├── cpp/                    # C++20 核心加速引擎（高性能纯逻辑）
│   ├── include/yanmo/      # 核心头文件 (speller, bigram, decoder, engine, llm)
│   ├── src/                # 引擎实现源码与 C-ABI 导出
│   ├── tests/              # 完整的 C++ 单元测试套件 (25/25 全部通过)
│   └── Makefile            # 高性能编译脚本 (-O3 优化)
├── docs/                   # 架构设计、交互规范与数据格式规范
│   ├── architecture.md     # 核心分层架构详细说明
│   └── interaction.md      # 键盘输入、Tab部首过滤与语音按键交互指南
├── data/                   # 词库与汉字构件基础数据
│   ├── dict/               # 基础核心词库与 2-Gram 转移概率数据
│   ├── radicals/           # 部首表与 IDS 汉字拆解数据库
│   └── models/             # Sherpa-ONNX 本地离线语音量化模型
├── core/                   # Python 核心绑定与服务层
│   ├── cpp_engine.py       # C++20 动态库 ctypes 高速桥接
│   ├── ai_service.py       # 异步 AI 智能辅助与规则降噪服务
│   └── user_dict.py        # 用户自造词与动态词频管理
├── daemon/                 # Linux 桌面全局后台守护进程
│   ├── yanmo_daemon.py     # 主守护进程管理
│   ├── keyboard_grabber.py # 全局键盘事件监听与 Push-To-Talk
│   ├── window_tracker.py   # 活动窗口光标自动跟随
│   └── tray_indicator.py   # 系统托盘指示器
├── ui/                     # 现代化透明磨砂候选窗与设置面板
├── bin/                    # 便捷启动脚本 (yanmo-daemon)
└── tests/                  # Python 自动化测试套件
```

---

## 🚀 开发路线图 (Roadmap)

- [x] **Phase 0: 项目立项与规范确立** (已完成)
- [x] **Phase 1: 汉字部件/部首数据库与检索原型** (已完成)
- [x] **Phase 2: 拼音与多层自学习词库引擎** (已完成)
- [x] **Phase 3: 桌面原生 GTK 3 悬浮条与五笔画直观部首面板** (已完成)
- [x] **Phase 4: 本地离线轻量语音听写 (SenseVoice)** (已完成)
- [x] **Phase 5: 系统级输入法常驻守护进程与 Fcitx-Rime 桥接** (已完成)
- [x] **Phase 6: C++20 原生内核加速与 RIME 级拼写代数重构** (已完成)
- [x] **Phase 7: 搜狗级 2-Gram 语言模型长句解码与动态自学习** (已完成)
- [x] **Phase 8: 全简拼混合输入 (如 shuosmn) 与前缀兜底保障** (已完成)
- [x] **Phase 9: 异步大模型辅助通道与离线语音全链路打通** (已完成)

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



