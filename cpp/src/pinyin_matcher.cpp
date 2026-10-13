#include "yanmo/pinyin_matcher.h"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <ctime>
#include <charconv>
#include <iostream>

namespace yanmo {

static bool is_single_char(std::string_view str) {
    size_t count = 0;
    for (unsigned char c : str) {
        if ((c & 0xC0) != 0x80) count++;
        if (count > 1) return false;
    }
    return count == 1;
}

bool PinyinMatcher::load_from_tsv(const std::string& filepath) {
    std::ifstream file(filepath);
    if (!file.is_open()) return false;
    lexicon_.clear(); trie_.clear(); abbrev_trie_.clear();
    lexicon_.reserve(150000);

    std::string line;
    size_t skipped_lines = 0;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::stringstream ss(line);
        std::string word, py, rad, freq_str;
        if (!std::getline(ss, word, '\t') || !std::getline(ss, py, '\t') || word.empty() || py.empty()) {
            skipped_lines++;
            continue;
        }
        std::getline(ss, rad, '\t');
        std::getline(ss, freq_str, '\t');
        int freq = 0;
        if (!freq_str.empty()) {
            auto [ptr, ec] = std::from_chars(freq_str.data(), freq_str.data() + freq_str.size(), freq);
            if (ec != std::errc() || ptr != freq_str.data() + freq_str.size()) {
                skipped_lines++;
                continue;
            }
        }

        uint32_t index = static_cast<uint32_t>(lexicon_.size());
        lexicon_.push_back(Candidate{word, py, rad, freq});
        trie_.insert(py, index);
        if (!is_single_char(word)) {
            auto syllables = speller_.segment_simple(py);
            if (!syllables.empty()) {
                std::string abbrev;
                for (const auto& s : syllables) abbrev += s[0];
                abbrev_trie_.insert(abbrev, index);
            }
        }
    }
    if (skipped_lines > 0) {
        std::cerr << "[PinyinMatcher] Warning: skipped " << skipped_lines << " malformed lines in " << filepath << "\n";
    }
    build_initial_indices();
    return true;
}

void PinyinMatcher::build_initial_indices() {
    initial_single_chars_.clear();
    for (size_t i = 0; i < lexicon_.size(); ++i) {
        const auto& c = lexicon_[i];
        if (is_single_char(c.word) && !c.pinyin.empty()) {
            if (c.pinyin.size() >= 2 && (c.pinyin.substr(0, 2) == "zh" || c.pinyin.substr(0, 2) == "ch" || c.pinyin.substr(0, 2) == "sh")) {
                initial_single_chars_[c.pinyin.substr(0, 2)].push_back(static_cast<uint32_t>(i));
                initial_single_chars_[c.pinyin.substr(0, 1)].push_back(static_cast<uint32_t>(i));
            } else {
                initial_single_chars_[c.pinyin.substr(0, 1)].push_back(static_cast<uint32_t>(i));
            }
        }
    }
    for (auto& [init, indices] : initial_single_chars_) {
        std::sort(indices.begin(), indices.end(), [this](uint32_t a, uint32_t b) {
            return lexicon_[a].freq > lexicon_[b].freq;
        });
        std::unordered_set<std::string> seen_words;
        std::vector<uint32_t> deduped;
        for (uint32_t idx : indices) {
            if (seen_words.insert(lexicon_[idx].word).second) {
                deduped.push_back(idx);
            }
        }
        indices = std::move(deduped);
    }
}

bool PinyinMatcher::load_user_dict(const std::string& filepath) {
    std::ifstream file(filepath);
    if (!file.is_open()) return false;
    std::string line;
    size_t skipped_lines = 0;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::stringstream ss(line);
        std::string word, py, rad, freq_str;
        if (!std::getline(ss, word, '\t') || !std::getline(ss, py, '\t') || word.empty() || py.empty()) {
            skipped_lines++;
            continue;
        }
        std::getline(ss, rad, '\t');
        std::getline(ss, freq_str, '\t');
        int freq = 10000;
        if (!freq_str.empty()) {
            auto [ptr, ec] = std::from_chars(freq_str.data(), freq_str.data() + freq_str.size(), freq);
            if (ec != std::errc() || ptr != freq_str.data() + freq_str.size()) {
                skipped_lines++;
                continue;
            }
        }

        bool found = false;
        if (const auto* indices = trie_.search_exact(py)) {
            for (uint32_t idx : *indices) {
                if (idx < lexicon_.size() && lexicon_[idx].word == word && lexicon_[idx].pinyin == py) {
                    lexicon_[idx].freq = std::max(lexicon_[idx].freq, freq + 20000);
                    found = true;
                    break;
                }
            }
        }
        if (!found) {
            uint32_t index = static_cast<uint32_t>(lexicon_.size());
            lexicon_.push_back(Candidate{word, py, rad, freq + 20000});
            trie_.insert(py, index);
            if (!is_single_char(word)) {
                auto syllables = speller_.segment_simple(py);
                if (!syllables.empty()) {
                    std::string abbrev;
                    for (const auto& s : syllables) abbrev += s[0];
                    abbrev_trie_.insert(abbrev, index);
                }
            }
        }
    }
    if (skipped_lines > 0) {
        std::cerr << "[PinyinMatcher] Warning: skipped " << skipped_lines << " malformed lines in " << filepath << "\n";
    }
    build_initial_indices();
    return true;
}

int PinyinMatcher::get_effective_frequency(const Candidate& c) const {
    int freq = c.freq;
    auto it = user_learned_.find(c.word);
    if (it != user_learned_.end()) {
        freq += 35000 + it->second.select_count * 2000;
    }
    return freq;
}

void PinyinMatcher::record_selection(std::string_view word, std::string_view pinyin) {
    if (word.empty()) return;
    std::string w(word);
    auto& state = user_learned_[w];
    state.select_count++;
    state.last_used_sec = static_cast<uint64_t>(std::time(nullptr));

    // 如果词库中没有这个词（如用户自定义短语），动态自造成新词入库
    bool found = false;
    if (const auto* indices = trie_.search_exact(pinyin)) {
        for (uint32_t idx : *indices) {
            if (idx < lexicon_.size() && lexicon_[idx].word == word && lexicon_[idx].pinyin == pinyin) {
                found = true;
                break;
            }
        }
    }
    if (!found && !pinyin.empty()) {
        uint32_t index = static_cast<uint32_t>(lexicon_.size());
        lexicon_.push_back(Candidate{std::string(word), std::string(pinyin), "", 25000});
        trie_.insert(pinyin, index);
        auto parse = speller_.parse(pinyin);
        if (!parse.primary_syllables.empty()) {
            std::string abbrev;
            for (const auto& s : parse.primary_syllables) abbrev += s[0];
            abbrev_trie_.insert(abbrev, index);
        }
        build_initial_indices();
    }
}

std::pair<std::string, int> PinyinMatcher::get_best_exact(std::string_view pinyin) const {
    const auto* indices = trie_.search_exact(pinyin);
    if (!indices) return {"", -1};
    std::string best_w;
    int best_freq = -1;
    for (uint32_t idx : *indices) {
        if (idx < lexicon_.size() && lexicon_[idx].pinyin == pinyin) {
            int eff = get_effective_frequency(lexicon_[idx]);
            if (eff > best_freq) {
                best_freq = eff;
                best_w = lexicon_[idx].word;
            }
        }
    }
    return {best_w, best_freq};
}

} // namespace yanmo
