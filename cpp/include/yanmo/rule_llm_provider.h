#pragma once

#include "llm_provider.h"

namespace yanmo {

// 本地规则型异步 AI 辅助提供者 (验证 ILLMProvider 异步接口与零时延解耦)
class RuleLLMProvider : public ILLMProvider {
public:
    RuleLLMProvider() = default;
    ~RuleLLMProvider() override = default;

    bool is_ready() const override { return true; }

    std::future<std::vector<AIAssistResult>> predict_async(
        std::string_view committed_context,
        std::string_view current_pinyin
    ) override;

    std::future<std::string> rewrite_async(
        std::string_view raw_text,
        std::string_view instruction
    ) override;
};

} // namespace yanmo
