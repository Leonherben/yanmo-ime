#pragma once

#include "types.h"
#include "bigram.h"
#include <string>
#include <string_view>
#include <vector>
#include <utility>
#include <functional>

namespace yanmo {

class PinyinMatcher;

// 语言解码器 (Sentence Decoder)
// 借鉴搜狗与现代 ASR 解码架构：结合 1-Gram 词频与 2-Gram 词间搭配，通过 Viterbi 动态规划寻找全局最高分长句
class SentenceDecoder {
public:
    SentenceDecoder() = default;
    ~SentenceDecoder() = default;

    // 核心解码：根据音节序列与 Bigram 语言模型计算最优长句与综合得分
    std::pair<std::string, int> decode(
        const std::vector<std::string>& syllables,
        const std::function<std::pair<std::string, int>(std::string_view)>& exact_lookup,
        const BigramModel* bigram = nullptr
    ) const;

    // 前缀尾巴补全解码（处理如 ["ni"] + "ha" 自动补全为 "你好" 或 "你好吗"）
    std::pair<std::string, int> decode_with_prefix(
        const std::vector<std::string>& prefix_syllables,
        std::string_view tail,
        const std::vector<std::string>& candidate_syllables,
        const std::function<std::pair<std::string, int>(std::string_view)>& exact_lookup,
        const BigramModel* bigram = nullptr
    ) const;
};

} // namespace yanmo
