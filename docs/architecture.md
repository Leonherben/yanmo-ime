# 言墨输入法 (yanmo-ime) 架构设计规范

本文档定义言墨输入法系统的整体模块分工、数据流转机制与跨平台接口规范。

---

## 1. 核心设计原则

1. **大脑与外壳解耦 (Core-Adapter Decoupling)**：
   - 核心层（`yanmo-core`）不包含任何 GUI 代码或特定操作系统的 API 调用。
   - 所有输入状态机、词库检索、部首过滤均在核心层完成。
2. **轻量与低延迟 (Lightweight & Low Latency)**：
   - 按键响应时间控制在 **5ms 以内**。
   - 核心内存常驻开销控制在 **10MB ~ 20MB**。
   - 采用前缀树（Trie）与内存映射（mmap）机制，避免一次性加载巨型词库挤占系统内存（严格适应 8GB RAM 物理限制）。
3. **安全自包含的离线语音 (Zero-Cloud Voice)**：
   - 基于 Sherpa-ONNX 离线轻量运行时（SenseVoice-Small INT8），无后台常驻 CPU 损耗，仅在按键激活时运行推理。

---

## 2. 层次结构与数据流

```text
+-------------------------------------------------------------+
|                     用户输入交互层 (UI & Adapter)             |
|   - 键盘/快捷键事件拦截 (Key Event Hook / Push-To-Talk)       |
|   - 候选词浮窗渲染 (Candidate Window: 候选词矩阵 + [部首]面板)   |
|   - 最终字符上屏 (Commit Text via Clipboard/XTEST)          |
+------------------------------+------------------------------+
                               | 原始击键流 (KeyCode / Raw Pinyin)
                               v
+-------------------------------------------------------------+
|                  言墨核心引擎 (yanmo-core / C++20)           |
|                                                             |
|   +-----------------------------------------------------+   |
|   | 输入状态机 (Input State Machine)                     |   |
|   | 状态: Empty -> Pinyin -> RadicalFilter -> Selected   |   |
|   +--------------------------+--------------------------+   |
|                              | 原始拼写 (如 "zhaogn", "shuosmn")
|                              v
|   +-----------------------------------------------------+   |
|   | 拼写代数引擎 (Speller Engine)                        |   |
|   | - 规范化与正字法 (jv->ju, LUE->lve)                   |   |
|   | - 击键手误自动纠错 (zhaogn -> zhang)                 |   |
|   | - 隔音符切分与歧义解析 (xi'an vs xian)                |   |
|   | - 413 全音节 DP 切分与全简拼混输分析 (shuo + smn)      |   |
|   | - 模糊音变体生成 (zh<->z, an<->ang 等)                |   |
|   +--------------------------+--------------------------+   |
|                              | 拼写切分结构体 SpellingParse
|                              v
|         +--------------------+--------------------+         |
|         v                                         v         |
|   +-----------------------+             +-----------------+ |
|   | 拼音检索与简拼匹配模块 |             | 部首/IDS 过滤树 | |
|   | (Pinyin Matcher)      |             | (Radical Index) | |
|   +-----------+-----------+             +--------+--------+ |
|               |                                  |          |
|               v                                  |          |
|   +-----------------------+                      |          |
|   | 2-Gram 与长句解码引擎  |                      |          |
|   | (Sentence Decoder)    |                      |          |
|   +-----------+-----------+                      |          |
|               |                                  |          |
|               +----------------+-----------------+          |
|                                v                            |
|             +-------------------------------------+         |
|             | 候选词排序与加权引擎 (Candidate Ranker) |         |
|             | - 基础词频 + 2-Gram 转移分 + 动态自学习|         |
|             | - 全简拼混合成词 + 最大前缀兜底保障     |         |
|             +------------------+------------------+         |
|                                |                            |
+--------------------------------+----------------------------+
                                 | 候选列表: [{"text": "说什么呢", "comment": ""}]
                                 v
                     [ 外壳层渲染候选并等待选择 ]
```

---

## 3. 核心子系统设计

### 3.1 拼写代数引擎 (Speller Engine)
- **定位**：位于输入状态机与词库检索之间，作为字符级与音素级的预处理与语法分析中枢（实现于 `cpp/include/yanmo/speller.h` 与 `cpp/src/speller.cpp`）。
- **主要职责**：
  1. **拼写规范化与正字法 (Orthography Normalization)**：自动清洗大小写与特殊映射（如 `LUE` $\to$ `lve`, `jv/qv/xv` $\to$ `ju/qu/xu`）。
  2. **智能手误容错 (Typo Auto-Correction)**：自动修正搜狗式常见击键倒装手误（如 `zhaogn` $\to$ `zhang`，`dign` $\to$ `ding`，`liou` $\to$ `liu`）。
  3. **隔音符处理 (Apostrophe Delimiters)**：支持单引号显式切音（如 `xi'an` $\to$ `["xi", "an"]` 优先匹配“西安”而非“先”）。
  4. **413 音节动态规划切分 (DP DAG Syllable Segmentation)**：基于中国拼音正词法 413 个标准全拼音节库，进行无歧义 DAG 最优切分并保留歧义备选（如 `xian` $\to$ `["xian"]` 与 `["xi", "an"]`）。
  5. **全拼与简拼混输分析 (Hybrid Segmentation)**：当用户输入全拼与多辅音尾缀时（如 `shuosmn`），智能切分为全拼主音节 `["shuo"]` 与辅音序列尾缀 `"smn"`，为后续混合成词奠定基础。
  6. **模糊音派生矩阵 (Fuzzy Matrix)**：支持可配置的平翘舌（`zh/ch/sh` $\leftrightarrow$ `z/c/s`）、前后鼻音（`an/en/in` $\leftrightarrow$ `ang/eng/ing`）及声母（`l` $\leftrightarrow$ `n`, `f` $\leftrightarrow$ `h`）笛卡尔积派生。

### 3.2 部首与汉字结构引擎 (Radical & IDS Engine)
- **数据源**：Unicode 汉字表意描述字符集（IDS, Ideographic Description Sequences）与常用 214 康熙部首/现代常用部首表（`cpp/src/radical_matcher.cpp`）。
- **倒排索引（Inverted Index）**：
  - 结构：`部首拼音 / 标识符 -> 构件集合 -> 汉字集合`
  - 示例：
    - `shui` 或 `氵` $\rightarrow$ `[江, 河, 湖, 海, 涸, 渴, ...]`
    - `mu` 或 `木` $\rightarrow$ `[林, 森, 树, 栋, 梁, ...]`
- **双向检索能力**：
  1. **辅码过滤**：给定已匹配的同音候选集 $C$，执行 $C \cap S_{\text{radical}}$ 求交集，毫秒级缩减候选。
  2. **部件拼装**：输入部件（如 `kou kou kou`）直接定位 `品`。

### 3.3 语言模型与长句解码器 (Bigram & Sentence Decoder)
- **定位**：实现搜狗式流畅长句输入的关键模块（`cpp/src/bigram.cpp` 与 `cpp/src/decoder.cpp`）。
- **2-Gram 转移概率模型 (BigramModel)**：
  - 采用轻量紧凑哈希索引管理二元词组转移奖励（`word_A + word_B`），常驻内存 $< 1\text{MB}$；
  - 支持动态自适应学习：当用户连续确认搭配时，自动动态累加转移加权。
- **Viterbi DP 整句解码器 (SentenceDecoder)**：
  - 基于动态规划评估 Unigram 词频、词长奖励与 2-Gram 转移分，求全局最优解；
  - 支持未闭合前缀长句推导（如输入 `zenmeshuon` 自动推导出最优组合“怎么说呢”）。

### 3.4 分级词库体系与检索器 (Lexicon & Pinyin Matcher)
- **Layer 1: 系统核心词库 (SysDict)**
  - 只读紧凑 Trie 前缀树索引，加载约 10 万~30 万词条（`data/dict/core_lexicon.tsv`）。
  - 双前缀树架构：`trie_`（全拼检索树）与 `abbrev_trie_`（首字母简拼检索树）。
  - **全简拼混输组词 (Hybrid Matcher)**：支持全拼前缀与简拼后缀动态交叉组词（如 `shuo` + `smn` $\to$ “说” + “什么呢” $\to$ **“说什么呢”**）。
  - **前缀兜底机制 (Prefix Fallback)**：对任意输入保证逐级前缀回退，候选词永不白屏。
- **Layer 2: 动态用户自学习词库 (UserDict)**
  - 内存与持久化两级缓存（`~/.local/share/yanmo/user_dict.json`）；
  - 输入即学习：选中词即刻获得动态加权（+35000），下次输入瞬间提至首选。

### 3.5 离线语音引擎 (Voice ASR Subsystem)
- **引擎架构**：Sherpa-ONNX C/C++ 动态链接库绑定（SenseVoice-Small INT8 量化模型，~110MB）。
- **交互协议**：Push-To-Talk（`v+Space` 长按唤醒）：
  - 待机状态：仅保留模型句柄，不占用音频设备，CPU 使用率为 0%；
  - 录音状态：捕获 16kHz 16bit 单声道音频流，浮窗展示动态倾听波纹；
  - 释放状态：按键物理释放瞬间，即刻完成毫秒级端侧推理并秒速上屏。

### 3.6 异步大模型辅助通道 (ILLMProvider / AIService)
- **C++ 抽象接口 (`ILLMProvider`)**：纯虚基类，主输入循环调用 `predict_async` 耗时 $< 2\text{ms}$ 返回 `std::future`，绝不阻塞打字。
- **Python 异步服务 (`AIService`)**：
  - 默认本地离线规则降级：秒级剔除口语停顿词（如“呃/那个/就是说”）并规范句末标点；
  - 自由扩展大模型：支持对接本地 Ollama（如 `qwen2.5-coder:1.5b`）或火山引擎豆包等 OpenAI 规范云端 API。

---

## 4. 跨平台适配层规范 (Adapter Interface)

为了保证后续迁移 Windows / macOS 不受限于 Linux，核心引擎暴露出最小化的 C 风格 API（或跨平台 IPC 协议）：

```c
// 1. 初始化引擎
YanMoEngine* yanmo_create(const char* data_dir);

// 2. 处理按键事件 (返回是否已被输入法拦截)
bool yanmo_process_key(YanMoEngine* engine, int keycode, int modifiers);

// 3. 获取当前候选词列表
int yanmo_get_candidates(YanMoEngine* engine, CandidateItem* out_list, int max_count);

// 4. 选择候选词并返回上屏文本
const char* yanmo_select_candidate(YanMoEngine* engine, int index);

// 5. 语音输入控制
void yanmo_voice_start(YanMoEngine* engine);
const char* yanmo_voice_stop(YanMoEngine* engine);

// 6. 销毁引擎
void yanmo_destroy(YanMoEngine* engine);
```

通过这一套极简接口，无论是在 Linux（Fcitx5 / 独立进程）、Windows（TSF）还是 macOS（InputMethodKit），均只需编写一层薄薄的系统级封装。
