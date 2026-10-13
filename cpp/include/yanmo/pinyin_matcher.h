#pragma once

#include "types.h"
#include "trie.h"
#include "speller.h"
#include "decoder.h"
#include "bigram.h"
#include <string>
#include <string_view>
#include <vector>
#include <utility>
#include <unordered_map>
#include <cstdint>

namespace yanmo {

class PinyinMatcher {
public:
    PinyinMatcher() = default;

    bool load_from_tsv(const std::string& filepath);
    bool load_user_dict(const std::string& filepath);
    bool load_bigram(const std::string& filepath) { return bigram_.load_from_tsv(filepath); }
    bool save_bigram(const std::string& filepath) const { return bigram_.save_to_tsv(filepath); }

    std::vector<Candidate> query(std::string_view pinyin) const;
    std::pair<std::string, int> get_best_exact(std::string_view pinyin) const;

    // 拼写配置管理 (模糊音、自动纠错)
    void set_spelling_config(const SpellingConfig& config) { speller_.set_config(config); }
    const SpellingConfig& get_spelling_config() const { return speller_.get_config(); }
    const Speller& get_speller() const { return speller_; }

    // 2-Gram 语言模型
    BigramModel& get_bigram() { return bigram_; }
    const BigramModel& get_bigram() const { return bigram_; }

    // 自适应动态学习：记录用户选词与时间戳
    void record_selection(std::string_view word, std::string_view pinyin);
    int get_effective_frequency(const Candidate& c) const;

    size_t size() const { return lexicon_.size(); }
    const std::vector<Candidate>& get_all() const { return lexicon_; }

private:
    struct UserWordState {
        int select_count = 0;
        uint64_t last_used_sec = 0;
    };

    void build_initial_indices();

    std::vector<Candidate> lexicon_;
    Trie trie_;
    Trie abbrev_trie_;
    Speller speller_;
    SentenceDecoder decoder_;
    BigramModel bigram_;
    std::unordered_map<std::string, UserWordState> user_learned_;
    std::unordered_map<std::string, std::vector<uint32_t>> initial_single_chars_;
};

} // namespace yanmo
