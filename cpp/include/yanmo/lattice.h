#pragma once

#include <string>
#include <string_view>
#include <vector>
#include <unordered_set>
#include <cstddef>

namespace yanmo {

enum class EdgeType {
    EXACT_SYLLABLE,    // 413 全拼标准音节 (如 "shuo", "guo", "ji")
    ABBREV_INITIAL,    // 声母简拼 (如 "zh", "ch", "sh", "b", "p", "m", ...)
    FUZZY_SYLLABLE,    // 模糊音音节 (平翘舌、前后鼻音)
    INCOMPLETE_PREFIX  // 输入末尾未闭合音节前缀 (如 "d", "xi")
};

struct LatticeEdge {
    size_t from = 0;
    size_t to = 0;
    std::string text;
    EdgeType type = EdgeType::EXACT_SYLLABLE;
    double cost = 0.0;
};

// 混合块：由相邻同类型（全拼或简拼）的音节合并而成，用于分段多粒度词典检索
struct SegmentChunk {
    std::string text;                 // 块对应的拼音序列 (如 "zg", "guoji", "shuo", "smn")
    bool is_abbrev = false;           // 是否为简拼块
    std::vector<std::string> tokens;  // 组成该块的单个音节或声母 (如 ["z", "g"] 或 ["guo", "ji"])
};

// 一条完整的加权切分路径
struct SegmentPath {
    std::vector<LatticeEdge> edges;
    std::vector<SegmentChunk> chunks;
    double total_cost = 0.0;
};

class SyllableLattice {
public:
    SyllableLattice() = default;

    // 基于全量音节库与声母表构建有向无环图，并利用 Viterbi 求解 Top-K 最优路径
    std::vector<SegmentPath> search_top_k(
        std::string_view input,
        const std::unordered_set<std::string>& valid_syllables,
        const std::unordered_set<std::string>& valid_prefixes,
        const std::vector<std::string>& sorted_syllables,
        size_t k = 5
    ) const;

    // 辅助校验：判断子串是否为有效声母（单字母或 zh/ch/sh）
    static bool is_initial(std::string_view s);

    // 辅助校验：获取单字符辅音
    static bool is_single_initial(char c);

    // 将边序列归并为连续的全拼块与简拼块
    static std::vector<SegmentChunk> edges_to_chunks(const std::vector<LatticeEdge>& edges);
};

} // namespace yanmo
