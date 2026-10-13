#include "yanmo/rule_llm_provider.h"
#include <chrono>
#include <thread>

namespace yanmo {

std::future<std::vector<AIAssistResult>> RuleLLMProvider::predict_async(
    std::string_view committed_context,
    [[maybe_unused]] std::string_view current_pinyin
) {
    std::string ctx(committed_context);
    return std::async(std::launch::async, [ctx]() -> std::vector<AIAssistResult> {
        // 模拟后台异步轻量耗时 (如 5ms)
        std::this_thread::sleep_for(std::chrono::milliseconds(5));

        std::vector<AIAssistResult> res;
        if (ctx.ends_with("今天")) {
            res.push_back({AIAssistResult::Type::NextWordsPrediction, "天气真好", "豆包AI联想", 0.95f});
            res.push_back({AIAssistResult::Type::NextWordsPrediction, "是个好日子", "豆包AI联想", 0.90f});
        } else if (ctx.ends_with("人工智能")) {
            res.push_back({AIAssistResult::Type::NextWordsPrediction, "技术应用", "豆包AI联想", 0.98f});
            res.push_back({AIAssistResult::Type::NextWordsPrediction, "深度学习", "豆包AI联想", 0.92f});
        } else if (ctx.ends_with("言墨")) {
            res.push_back({AIAssistResult::Type::NextWordsPrediction, "输入法", "豆包AI联想", 0.99f});
            res.push_back({AIAssistResult::Type::NextWordsPrediction, "轻巧自如", "豆包AI联想", 0.93f});
        } else if (!ctx.empty()) {
            res.push_back({AIAssistResult::Type::NextWordsPrediction, "顺利", "AI补全", 0.85f});
        }
        return res;
    });
}

std::future<std::string> RuleLLMProvider::rewrite_async(
    std::string_view raw_text,
    [[maybe_unused]] std::string_view instruction
) {
    std::string text(raw_text);
    return std::async(std::launch::async, [text]() -> std::string {
        // 模拟后台异步润色 (如 10ms)
        std::this_thread::sleep_for(std::chrono::milliseconds(10));

        std::string s = text;
        // 去除口语助词: "呃", "啊", "那个"
        auto strip_word = [&](const std::string& pattern) {
            size_t pos = 0;
            while ((pos = s.find(pattern, pos)) != std::string::npos) {
                s.erase(pos, pattern.size());
            }
        };
        strip_word("呃");
        strip_word("那个");
        strip_word("就是说");

        if (!s.empty() && !s.ends_with("。") && !s.ends_with("！") && !s.ends_with("？")) {
            s += "。";
        }
        return s;
    });
}

} // namespace yanmo
