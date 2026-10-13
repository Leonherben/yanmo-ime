#pragma once

#include <string>
#include <string_view>
#include <unordered_map>

namespace yanmo {

// 二元语言模型 (2-Gram / Bigram Model)
// 记录词与词之间的搭配转移概率，用于 Viterbi 组句最优路径加权与上下文打分
class BigramModel {
public:
    BigramModel() = default;
    ~BigramModel() = default;

    // 从 TSV 文件加载离线二元词频 (格式: word1\tword2\tfreq)
    bool load_from_tsv(const std::string& filepath);

    // 将二元词频 (包含动态学习) 保存至 TSV 文件
    bool save_to_tsv(const std::string& filepath) const;

    // 查询从 w1 转移到 w2 的搭配转移分值 (未命中返回 0)
    int get_transition_score(std::string_view w1, std::string_view w2) const;

    // 动态学习：强化 w1 -> w2 的词间搭配连接 (用户连选记忆)
    void record_transition(std::string_view w1, std::string_view w2, int boost = 10000);

    size_t size() const { return transitions_.size(); }
    void clear() { transitions_.clear(); }

private:
    static std::string make_key(std::string_view w1, std::string_view w2) {
        std::string key;
        key.reserve(w1.size() + 1 + w2.size());
        key.append(w1);
        key.push_back('\t');
        key.append(w2);
        return key;
    }

    std::unordered_map<std::string, int> transitions_;
};

} // namespace yanmo
