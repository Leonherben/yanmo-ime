#pragma once

#include "types.h"
#include <string>
#include <string_view>
#include <vector>
#include <future>
#include <memory>

namespace yanmo {

// 大模型返回的智能预测与辅助结果
struct AIAssistResult {
    enum class Type {
        NextWordsPrediction,  // 下文补全与联想预测 (豆包式打字预测)
        RewriteText,          // 语法纠错与润色 (口语转书面语)
        SmartCompletion,      // 长句/诗词/代码补全
        EmojiSuggestion       // 语义 Emoji / 符号推荐
    };

    Type type = Type::NextWordsPrediction;
    std::string text;           // 建议的文本内容
    std::string prompt_summary; // 提示标签 (如 "豆包AI已润色" / "联想预测")
    float confidence = 1.0f;    // 置信度 (0.0 ~ 1.0)
};

// 预留的大模型抽象接口 (纯虚基类)
// 保证主输入法主干道 (<5ms) 与 AI 异步通道安全解耦
class ILLMProvider {
public:
    virtual ~ILLMProvider() = default;

    // 模型是否就绪（本地小模型如 1.5B 已加载或云端 API Key 有效）
    virtual bool is_ready() const = 0;

    // 异步联想预测：根据最近已提交的上屏上下文与当前正在输入的拼音进行预测
    virtual std::future<std::vector<AIAssistResult>> predict_async(
        std::string_view committed_context,
        std::string_view current_pinyin
    ) = 0;

    // 异步文本润色/语法纠错：选中文本或语音转写后按需触发
    virtual std::future<std::string> rewrite_async(
        std::string_view raw_text,
        std::string_view instruction
    ) = 0;
};

} // namespace yanmo
