#pragma once

#include "types.h"
#include "pinyin_matcher.h"
#include "radical_matcher.h"
#include "speller.h"
#include "llm_provider.h"
#include <string>
#include <string_view>
#include <vector>
#include <memory>

namespace yanmo {

class YanMoEngine {
public:
    YanMoEngine();
    ~YanMoEngine() = default;

    bool init(const std::string& lexicon_path, const std::string& radicals_path);
    bool load_user_dict(const std::string& filepath);
    bool load_bigram(const std::string& filepath) { return pinyin_matcher_.load_bigram(filepath); }
    bool save_bigram(const std::string& filepath) const { return pinyin_matcher_.save_bigram(filepath); }
    void reset();

    // Returns true if the key event was consumed by the engine
    bool feed_key(std::string_view key, bool is_shift);

    // Commit actions (returns text to be emitted to target application)
    std::string commit_candidate(size_t index_in_active_row);
    std::string commit_top(std::string_view trailing_punct = "");
    std::string commit_raw_buffer();

    // Radical mode explicit controls
    void enter_radical_mode();
    void set_radical_glyph(std::string_view glyph);

    // Status queries
    const EngineStatus& get_status() const { return status_; }
    void clear_committed_text() { status_.committed_text.clear(); }
    const EngineConfig& get_config() const { return config_; }
    void set_config(const EngineConfig& cfg) { config_ = cfg; }
    void set_row_size(size_t size) { if (size >= 3 && size <= 10) config_.row_size = size; }
    void set_full_width_punct(bool enabled) { config_.full_width_punct = enabled; }
    bool is_full_width_punct() const { return config_.full_width_punct; }
    void set_full_width_char(bool enabled) { config_.full_width_char = enabled; }
    bool is_full_width_char() const { return config_.full_width_char; }

    // 拼写配置设置与查询
    void set_spelling_config(const SpellingConfig& cfg) { pinyin_matcher_.set_spelling_config(cfg); }
    const SpellingConfig& get_spelling_config() const { return pinyin_matcher_.get_spelling_config(); }

    // 异步大模型提供者管理 (预留豆包式 AI 扩展能力)
    void set_llm_provider(std::shared_ptr<ILLMProvider> provider) { llm_provider_ = std::move(provider); }
    std::shared_ptr<ILLMProvider> get_llm_provider() const { return llm_provider_; }

    std::vector<Candidate> get_current_candidates() const;
    std::vector<Candidate> get_row_candidates(size_t row_idx) const;

private:
    void update_candidates();
    std::string map_punctuation(std::string_view key) const;

    EngineConfig config_;
    EngineStatus status_;

    PinyinMatcher pinyin_matcher_;
    RadicalMatcher radical_matcher_;
    std::vector<Candidate> current_candidates_;
    std::shared_ptr<ILLMProvider> llm_provider_{nullptr};

    std::string last_committed_word_;
    mutable bool double_quote_open_ = false;
};

} // namespace yanmo
