#pragma once

#include "yanmo/types.h"
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace yanmo {

struct RadicalInfo {
    std::string radical;
    std::string name;
    char first_stroke = ' '; // h, s, p, d, z
    std::vector<std::string> pinyins;
};

class RadicalMatcher {
public:
    RadicalMatcher() = default;

    bool load_from_tsv(const std::string& filepath);
    bool load_char_strokes(const std::string& filepath);

    bool match_candidate(const Candidate& cand,
                         std::string_view query,
                         std::string& out_hint) const;

    bool match_radical(std::string_view target_radical, 
                       std::string_view query, 
                       std::string& out_hint) const;

    std::vector<std::string> get_radicals_by_stroke(char stroke) const;
    std::string get_stroke_name(char stroke) const;

private:
    std::vector<RadicalInfo> radicals_;
    std::unordered_map<std::string, std::vector<std::string>> pinyin_to_radicals_;
    std::unordered_map<char, std::vector<std::string>> stroke_to_radicals_;
    std::unordered_map<std::string, std::string> char_strokes_;
};

} // namespace yanmo

