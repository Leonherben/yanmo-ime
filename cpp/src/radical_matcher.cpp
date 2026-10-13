#include "yanmo/radical_matcher.h"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <cctype>

namespace yanmo {

bool RadicalMatcher::load_char_strokes(const std::string& filepath) {
    std::ifstream file(filepath);
    if (!file.is_open()) return false;

    char_strokes_.clear();
    std::string line;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::stringstream ss(line);
        std::string ch, first_stroke, strokes;
        if (!std::getline(ss, ch, '\t') ||
            !std::getline(ss, first_stroke, '\t') ||
            !std::getline(ss, strokes, '\t')) continue;
        char_strokes_[ch] = strokes;
    }
    return true;
}

bool RadicalMatcher::load_from_tsv(const std::string& filepath) {
    std::ifstream file(filepath);
    if (!file.is_open()) return false;

    radicals_.clear();
    pinyin_to_radicals_.clear();
    stroke_to_radicals_.clear();

    std::string line;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::stringstream ss(line);
        std::string rad, name, stroke_str, pys_str;
        if (!std::getline(ss, rad, '\t') ||
            !std::getline(ss, name, '\t') ||
            !std::getline(ss, stroke_str, '\t') ||
            !std::getline(ss, pys_str, '\t')) continue;

        char stroke = stroke_str.empty() ? ' ' : stroke_str[0];
        RadicalInfo info{rad, name, stroke, {}};

        std::stringstream py_ss(pys_str);
        std::string py;
        while (std::getline(py_ss, py, ',')) {
            if (!py.empty()) {
                info.pinyins.push_back(py);
                pinyin_to_radicals_[py].push_back(rad);
            }
        }
        if (stroke != ' ') {
            stroke_to_radicals_[stroke].push_back(rad);
        }
        radicals_.push_back(std::move(info));
    }

    // Attempt to load char_strokes.tsv from the same directory if available
    size_t last_slash = filepath.find_last_of("/\\");
    std::string dir = (last_slash != std::string::npos) ? filepath.substr(0, last_slash) : ".";
    load_char_strokes(dir + "/char_strokes.tsv");

    return true;
}

std::string RadicalMatcher::get_stroke_name(char stroke) const {
    switch (stroke) {
        case 'h': return "横 (h)";
        case 's': return "竖 (s)";
        case 'p': return "撇 (p)";
        case 'd': return "点 (d)";
        case 'z': return "折 (z)";
        default:  return "";
    }
}

std::vector<std::string> RadicalMatcher::get_radicals_by_stroke(char stroke) const {
    auto it = stroke_to_radicals_.find(stroke);
    if (it != stroke_to_radicals_.end()) return it->second;
    return {};
}

bool RadicalMatcher::match_radical(std::string_view target_radical, 
                                   std::string_view query, 
                                   std::string& out_hint) const {
    if (target_radical.empty() || query.empty()) return false;

    std::string q(query);
    for (char& c : q) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));

    // Literal radical match
    if (target_radical == q) {
        out_hint = std::string(target_radical) + "部";
        return true;
    }

    // Pinyin prefix match
    for (const auto& [py, rads] : pinyin_to_radicals_) {
        if (py.rfind(q, 0) == 0) { // py starts with q
            if (std::find(rads.begin(), rads.end(), target_radical) != rads.end()) {
                out_hint = std::string(target_radical) + "部";
                return true;
            }
        }
    }
    return false;
}

bool RadicalMatcher::match_candidate(const Candidate& cand,
                                     std::string_view query,
                                     std::string& out_hint) const {
    if (query.empty()) return true;

    std::string q(query);
    for (char& c : q) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));

    // 1. Check if query is a stroke sequence (composed purely of h, s, p, d, z)
    bool is_stroke_seq = true;
    for (char c : q) {
        if (c != 'h' && c != 's' && c != 'p' && c != 'd' && c != 'z') {
            is_stroke_seq = false;
            break;
        }
    }

    if (is_stroke_seq) {
        // Strictly match character stroke order (汉字笔顺)，不按部首起笔
        std::string first_ch;
        if (!cand.word.empty()) {
            size_t len = 1;
            unsigned char lead = static_cast<unsigned char>(cand.word[0]);
            if ((lead & 0xE0) == 0xC0) len = 2;
            else if ((lead & 0xF0) == 0xE0) len = 3;
            else if ((lead & 0xF8) == 0xF0) len = 4;
            if (len <= cand.word.size()) {
                first_ch = cand.word.substr(0, len);
            }
        }

        if (!first_ch.empty()) {
            auto it = char_strokes_.find(first_ch);
            if (it != char_strokes_.end()) {
                if (it->second.rfind(q, 0) == 0) {
                    out_hint = get_stroke_name(q[0]);
                    return true;
                }
            }
        }
        return false;
    }

    // 2. Radical matching (glyph or pinyin prefix)
    return match_radical(cand.radical, q, out_hint);
}

} // namespace yanmo

