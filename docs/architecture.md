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
|   - 键盘/快捷键事件拦截 (Key Event Hook)                       |
|   - 候选词浮窗渲染 (Candidate Window: 候选词列表 + [部首]按钮)    |
|   - 最终字符上屏 (Commit Text)                                 |
+------------------------------+------------------------------+
                               | 标准输入事件 (KeyCode / Modifiers)
                               v
+-------------------------------------------------------------+
|                  言墨核心引擎 (yanmo-core)                    |
|                                                             |
|   +-----------------------------------------------------+   |
|   | 输入状态机 (Input State Machine)                     |   |
|   | 状态: Empty -> Pinyin -> RadicalFilter -> Selected   |   |
|   +--------------------------+--------------------------+   |
|                              |                              |
|         +--------------------+--------------------+         |
|         v                                         v         |
|   +-----------------------+             +-----------------+ |
|   | 拼音检索与分词模块     |             | 部首/IDS 过滤树 | |
|   | (Pinyin Matcher)      |             | (Radical Index) | |
|   +-----------+-----------+             +--------+--------+ |
|               |                                  |          |
|               +----------------+-----------------+          |
|                                v                            |
|             +-------------------------------------+         |
|             | 候选词排序与加权引擎 (Candidate Ranker) |         |
|             | - 词频权重 + 用户频次 + 部首匹配度     |         |
|             +------------------+------------------+         |
|                                |                            |
+--------------------------------+----------------------------+
                                 | 候选列表: [{"text": "河", "comment": "氵部"}]
                                 v
                     [ 外壳层渲染候选并等待选择 ]
```

---

## 3. 核心子系统设计

### 3.1 部首与汉字结构引擎 (Radical & IDS Engine)
- **数据源**：Unicode 汉字表意描述字符集（IDS, Ideographic Description Sequences）与常用 214 康熙部首/现代常用部首表。
- **倒排索引（Inverted Index）**：
  - 结构：`部首拼音 / 标识符 -> 构件集合 -> 汉字集合`
  - 示例：
    - `shui` 或 `氵` $\rightarrow$ `[江, 河, 湖, 海, 涸, 渴, ...]`
    - `mu` 或 `木` $\rightarrow$ `[林, 森, 树, 栋, 梁, ...]`
- **双向检索能力**：
  1. **辅码过滤**：给定已匹配的同音候选集 $C$，执行 $C \cap S_{\text{radical}}$ 求交集，毫秒级缩减候选。
  2. **部件拼装**：输入部件（如 `kou kou kou`）直接定位 `品`。

### 3.2 分级词库体系 (Lexicon System)
- **Layer 1: 系统基础词库 (SysDict)**
  - 只读二进制格式（Double-Array Trie 或 LMDB）。
  - 按拼音前缀索引，包含现代汉语常用词频（约 10 万~30 万词条）。
- **Layer 2: 用户自学习词库 (UserDict)**
  - 采用轻量嵌入式 SQLite 数据库存储在 `~/.local/share/yanmo/user.db`。
  - 结构：`(word, pinyin, frequency, last_used_timestamp)`。
  - 支持动态词频自增，输入即学习。

### 3.3 离线语音引擎 (Voice ASR Subsystem)
- **引擎架构**：Sherpa-ONNX C/C++ 动态链接库绑定。
- **模型规格**：SenseVoice-Small INT8 量化模型（~110MB）。
- **生命周期**：
  - 待机状态：仅保留模型句柄，不占用音频设备，CPU 使用率为 0%。
  - 录音状态：通过 PortAudio 或 ALSA/PulseAudio 捕获 16kHz 16bit 单声道音频流。
  - 结束状态：VAD（静音检测）或按键释放后，触发推理，即刻发送文本上屏并关闭音频通道。

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
