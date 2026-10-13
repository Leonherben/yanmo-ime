#include "yanmo/engine.h"
#include <cctype>
#include <algorithm>

namespace yanmo {

bool YanMoEngine::feed_key(std::string_view key, [[maybe_unused]] bool is_shift) {
    status_.committed_text.clear();
    if (key == "Escape") {
        if (status_.mode != InputMode::IDLE) { reset(); return true; }
        return false;
    }

    if (key == "Tab") {
        if (status_.mode == InputMode::COMPOSING || status_.mode == InputMode::IDLE) {
            status_.mode = InputMode::RADICAL;
            status_.radical_buffer.clear();
            status_.page_offset = status_.active_row = 0;
            update_candidates();
            return true;
        } else if (status_.mode == InputMode::RADICAL) {
            status_.mode = status_.pinyin_buffer.empty() ? InputMode::IDLE : InputMode::COMPOSING;
            status_.radical_buffer.clear();
            status_.page_offset = status_.active_row = 0;
            update_candidates();
            return true;
        }
    }

    if (key == "ArrowDown" && status_.mode != InputMode::IDLE && !current_candidates_.empty()) {
        size_t total_rows = (current_candidates_.size() + config_.row_size - 1) / config_.row_size;
        if (!status_.is_expanded) {
            status_.is_expanded = true;
            status_.active_row = std::min<size_t>(1, total_rows > 1 ? 1 : 0);
        } else if (status_.active_row + 1 < std::min(config_.max_rows, total_rows - status_.page_offset)) {
            status_.active_row++;
        } else if (status_.page_offset + config_.max_rows < total_rows) {
            status_.page_offset += config_.max_rows;
            status_.active_row = 0;
        }
        return true;
    }

    if (key == "ArrowUp" && status_.mode != InputMode::IDLE && status_.is_expanded) {
        if (status_.active_row > 0) {
            status_.active_row--;
        } else if (status_.page_offset >= config_.max_rows) {
            status_.page_offset -= config_.max_rows;
            status_.active_row = config_.max_rows - 1;
        } else {
            status_.is_expanded = false;
        }
        return true;
    }

    if (key == "=" || key == "]" || key == "PageDown") {
        if (status_.mode != InputMode::IDLE && !current_candidates_.empty()) {
            size_t total_rows = (current_candidates_.size() + config_.row_size - 1) / config_.row_size;
            size_t step = status_.is_expanded ? config_.max_rows : 1;
            if (status_.page_offset + step < total_rows) {
                status_.page_offset += step;
                status_.active_row = 0;
            }
            return true;
        }
    }
    if (key == "-" || key == "[" || key == "PageUp") {
        if (status_.mode != InputMode::IDLE && !current_candidates_.empty()) {
            size_t step = status_.is_expanded ? config_.max_rows : 1;
            if (status_.page_offset > 0) {
                status_.page_offset = (status_.page_offset >= step) ? (status_.page_offset - step) : 0;
                status_.active_row = 0;
            }
            return true;
        }
    }

    if (status_.mode != InputMode::IDLE && config_.auto_punct_commit) {
        if (key == "," || key == "." || key == "?" || key == "!" ||
            key == ";" || key == ":" || key == "\"" || key == "<" ||
            key == ">" || key == "(" || key == ")" || key == "\\" || key == "^") {
            std::string punct = map_punctuation(key);
            commit_top(punct);
            return true;
        }
    }

    if (status_.mode == InputMode::IDLE) {
        if (key == " " && config_.full_width_char) {
            status_.committed_text = "\xe3\x80\x80";
            return true;
        }
        if (key == "," || key == "." || key == "?" || key == "!" ||
            key == ";" || key == ":" || key == "\"" || key == "<" ||
            key == ">" || key == "(" || key == ")" || key == "\\" || key == "^") {
            if (config_.full_width_punct) {
                status_.committed_text = map_punctuation(key);
                return true;
            }
        }
    }

    if (key == "Backspace") {
        if (status_.mode == InputMode::RADICAL) {
            if (!status_.radical_buffer.empty()) {
                while (!status_.radical_buffer.empty()) {
                    char c = status_.radical_buffer.back();
                    status_.radical_buffer.pop_back();
                    if ((static_cast<unsigned char>(c) & 0xC0) != 0x80) {
                        break;
                    }
                }
            } else {
                status_.mode = status_.pinyin_buffer.empty() ? InputMode::IDLE : InputMode::COMPOSING;
            }
            status_.page_offset = status_.active_row = 0;
            update_candidates();
            return true;
        } else if (status_.mode == InputMode::COMPOSING && !status_.pinyin_buffer.empty()) {
            status_.pinyin_buffer.pop_back();
            if (status_.pinyin_buffer.empty()) reset();
            else { status_.page_offset = status_.active_row = 0; update_candidates(); }
            return true;
        }
        return false;
    }

    if (key.size() == 1 && std::isdigit(key[0]) && key[0] != '0') {
        size_t idx = key[0] - '1';
        if (idx < config_.row_size) {
            std::string committed = commit_candidate(idx);
            return !committed.empty();
        }
    }

    if (key == " " || key == "Space") {
        std::string committed = commit_candidate(0);
        return !committed.empty();
    }

    if (key == "Enter") {
        if (!status_.pinyin_buffer.empty()) { commit_raw_buffer(); return true; }
        return false;
    }

    bool is_alpha = (key.size() == 1 && std::isalpha(static_cast<unsigned char>(key[0])));
    bool is_delim = (key == "'" && status_.mode == InputMode::COMPOSING && !status_.pinyin_buffer.empty() && status_.pinyin_buffer.back() != '\'');

    if (is_alpha || is_delim) {
        char ch = is_delim ? '\'' : static_cast<char>(std::tolower(static_cast<unsigned char>(key[0])));
        if (status_.mode == InputMode::IDLE) {
            status_.mode = InputMode::COMPOSING;
            status_.pinyin_buffer = ch;
            status_.page_offset = status_.active_row = 0;
            status_.is_expanded = false;
        } else if (status_.mode == InputMode::COMPOSING) {
            status_.pinyin_buffer += ch;
            status_.page_offset = status_.active_row = 0;
        } else if (status_.mode == InputMode::RADICAL && is_alpha) {
            status_.radical_buffer += ch;
            status_.page_offset = status_.active_row = 0;
        }
        update_candidates();
        return true;
    }

    if (status_.mode == InputMode::RADICAL && !key.empty() && static_cast<unsigned char>(key[0]) >= 0x80) {
        status_.radical_buffer += key;
        status_.page_offset = status_.active_row = 0;
        update_candidates();
        return true;
    }

    return false;
}

} // namespace yanmo
