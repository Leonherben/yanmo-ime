#include "yanmo/bigram.h"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <charconv>
#include <iostream>

namespace yanmo {

bool BigramModel::load_from_tsv(const std::string& filepath) {
    std::ifstream file(filepath);
    if (!file.is_open()) return false;

    std::string line;
    size_t skipped_lines = 0;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::stringstream ss(line);
        std::string w1, w2, freq_str;
        if (!std::getline(ss, w1, '\t') || !std::getline(ss, w2, '\t') || w1.empty() || w2.empty()) {
            skipped_lines++;
            continue;
        }
        std::getline(ss, freq_str, '\t');
        int freq = 1000;
        if (!freq_str.empty()) {
            auto [ptr, ec] = std::from_chars(freq_str.data(), freq_str.data() + freq_str.size(), freq);
            if (ec != std::errc() || ptr != freq_str.data() + freq_str.size()) {
                skipped_lines++;
                continue;
            }
        }

        transitions_[make_key(w1, w2)] = freq;
    }
    if (skipped_lines > 0) {
        std::cerr << "[BigramModel] Warning: skipped " << skipped_lines << " malformed lines in " << filepath << "\n";
    }
    return true;
}

bool BigramModel::save_to_tsv(const std::string& filepath) const {
    std::ofstream file(filepath);
    if (!file.is_open()) return false;

    for (const auto& [key, freq] : transitions_) {
        file << key << '\t' << freq << '\n';
    }
    return file.good();
}

int BigramModel::get_transition_score(std::string_view w1, std::string_view w2) const {
    if (w1.empty() || w2.empty()) return 0;
    auto it = transitions_.find(make_key(w1, w2));
    if (it != transitions_.end()) {
        return it->second;
    }
    return 0;
}

void BigramModel::record_transition(std::string_view w1, std::string_view w2, int boost) {
    if (w1.empty() || w2.empty()) return;
    std::string key = make_key(w1, w2);
    auto it = transitions_.find(key);
    if (it != transitions_.end()) {
        it->second = std::min(it->second + boost, 100000);
    } else {
        transitions_[key] = boost;
    }
}

} // namespace yanmo
