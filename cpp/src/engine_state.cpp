#include "yanmo/engine.h"
#include <algorithm>
#include <unordered_set>

namespace yanmo {

YanMoEngine::YanMoEngine() {
    reset();
}

bool YanMoEngine::init(const std::string& lexicon_path, const std::string& radicals_path) {
    bool ok1 = pinyin_matcher_.load_from_tsv(lexicon_path);
    bool ok2 = radical_matcher_.load_from_tsv(radicals_path);

    // 自动寻找并加载同目录下的 core_bigram.tsv
    std::string bigram_path;
    auto slash_pos = lexicon_path.rfind('/');
    if (slash_pos != std::string::npos) {
        bigram_path = lexicon_path.substr(0, slash_pos + 1) + "core_bigram.tsv";
    } else {
        bigram_path = "core_bigram.tsv";
    }
    pinyin_matcher_.load_bigram(bigram_path);

    return ok1 && ok2;
}

bool YanMoEngine::load_user_dict(const std::string& filepath) {
    return pinyin_matcher_.load_user_dict(filepath);
}

void YanMoEngine::reset() {
    status_ = EngineStatus{};
    current_candidates_.clear();
}

static std::string to_full_width_utf8(std::string_view input) {
    std::string out;
    for (size_t i = 0; i < input.size(); ++i) {
        unsigned char c = static_cast<unsigned char>(input[i]);
        if (c == ' ') {
            out += "\xe3\x80\x80";
        } else if (c >= 0x21 && c <= 0x7E) {
            uint32_t codepoint = 0xFF01 + (c - 0x21);
            out.push_back(static_cast<char>(0xE0 | ((codepoint >> 12) & 0x0F)));
            out.push_back(static_cast<char>(0x80 | ((codepoint >> 6) & 0x3F)));
            out.push_back(static_cast<char>(0x80 | (codepoint & 0x3F)));
        } else {
            out.push_back(c);
        }
    }
    return out;
}

std::string YanMoEngine::map_punctuation(std::string_view key) const {
    if (!config_.full_width_punct) {
        return std::string(key);
    }
    if (key == ",") return "，";
    if (key == ".") return "。";
    if (key == "?") return "？";
    if (key == "!") return "！";
    if (key == ";") return "；";
    if (key == ":") return "：";
    if (key == "\"") {
        double_quote_open_ = !double_quote_open_;
        return double_quote_open_ ? "“" : "”";
    }
    if (key == "<") return "《";
    if (key == ">") return "》";
    if (key == "(") return "（";
    if (key == ")") return "）";
    if (key == "\\") return "、";
    if (key == "^") return "……";
    return std::string(key);
}

void YanMoEngine::update_candidates() {
    status_.radical_hint.clear();
    std::vector<Candidate> list;

    if (!status_.pinyin_buffer.empty()) {
        list = pinyin_matcher_.query(status_.pinyin_buffer);
    } else if (status_.mode == InputMode::RADICAL) {
        list = pinyin_matcher_.get_all();
    }

    if (status_.mode == InputMode::RADICAL && !status_.radical_buffer.empty()) {
        std::vector<Candidate> filtered;
        std::unordered_set<std::string> seen_words;
        for (const auto& cand : list) {
            std::string hint;
            if (radical_matcher_.match_candidate(cand, status_.radical_buffer, hint)) {
                if (seen_words.insert(cand.word).second) {
                    if (status_.radical_hint.empty()) status_.radical_hint = hint;
                    filtered.push_back(cand);
                }
            }
        }
        list = std::move(filtered);
    }

    current_candidates_ = std::move(list);
    status_.total_candidates = current_candidates_.size();
}

std::vector<Candidate> YanMoEngine::get_row_candidates(size_t row_idx) const {
    size_t start = row_idx * config_.row_size;
    if (start >= current_candidates_.size()) return {};
    size_t count = std::min(config_.row_size, current_candidates_.size() - start);
    return {current_candidates_.begin() + start, current_candidates_.begin() + start + count};
}

std::string YanMoEngine::commit_candidate(size_t index_in_active_row) {
    size_t actual_row = status_.page_offset + status_.active_row;
    auto row_cands = get_row_candidates(actual_row);
    if (index_in_active_row < row_cands.size()) {
        std::string committed = row_cands[index_in_active_row].word;
        std::string py = status_.pinyin_buffer;
        reset();
        if (config_.full_width_char) {
            committed = to_full_width_utf8(committed);
        }
        status_.committed_text = committed;

        // 搜狗式自适应动态学习与 2-Gram 转移强化
        pinyin_matcher_.record_selection(committed, py);
        if (!last_committed_word_.empty()) {
            pinyin_matcher_.get_bigram().record_transition(last_committed_word_, committed);
        }
        last_committed_word_ = committed;
        return committed;
    }
    return "";
}

std::string YanMoEngine::commit_top(std::string_view trailing_punct) {
    size_t actual_row = status_.page_offset + status_.active_row;
    auto row_cands = get_row_candidates(actual_row);
    std::string word = !row_cands.empty() ? row_cands[0].word : status_.pinyin_buffer;
    std::string py = status_.pinyin_buffer;
    std::string text = word + std::string(trailing_punct);
    reset();
    if (config_.full_width_char) {
        text = to_full_width_utf8(text);
    }
    status_.committed_text = text;

    pinyin_matcher_.record_selection(word, py);
    if (!last_committed_word_.empty()) {
        pinyin_matcher_.get_bigram().record_transition(last_committed_word_, word);
    }
    last_committed_word_ = word;
    return text;
}

std::string YanMoEngine::commit_raw_buffer() {
    std::string text = status_.pinyin_buffer;
    reset();
    if (config_.full_width_char) {
        text = to_full_width_utf8(text);
    }
    status_.committed_text = text;
    return text;
}

std::vector<Candidate> YanMoEngine::get_current_candidates() const {
    return current_candidates_;
}

void YanMoEngine::enter_radical_mode() {
    status_.mode = InputMode::RADICAL;
    status_.radical_buffer.clear();
    status_.page_offset = status_.active_row = 0;
    update_candidates();
}

void YanMoEngine::set_radical_glyph(std::string_view glyph) {
    status_.mode = InputMode::RADICAL;
    status_.radical_buffer = glyph;
    status_.page_offset = status_.active_row = 0;
    update_candidates();
}

} // namespace yanmo
