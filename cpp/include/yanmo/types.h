#pragma once

#include <string>
#include <string_view>
#include <vector>

namespace yanmo {

enum class InputMode {
    IDLE,
    COMPOSING,
    RADICAL
};

struct Candidate {
    std::string word;
    std::string pinyin;
    std::string radical;
    int freq = 0;
};

struct EngineConfig {
    size_t row_size = 5;
    size_t max_rows = 4;
    bool auto_punct_commit = true;
    bool matrix_expand_enabled = true;
    bool full_width_punct = true;
    bool full_width_char = false;
};

struct EngineStatus {
    InputMode mode = InputMode::IDLE;
    std::string pinyin_buffer;
    std::string radical_buffer;
    std::string radical_hint;
    std::string committed_text;
    size_t total_candidates = 0;
    size_t page_offset = 0;
    size_t active_row = 0;
    bool is_expanded = false;
};

} // namespace yanmo
