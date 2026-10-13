#include "yanmo/c_api.h"
#include "yanmo/engine.h"
#include <cstring>
#include <sstream>
#include <algorithm>
#include <cstdio>

struct yanmo_engine_t {
    yanmo::YanMoEngine engine;
};

static void escape_json_string(std::string_view str, std::ostringstream& oss) {
    oss << "\"";
    for (char c : str) {
        switch (c) {
            case '"': oss << "\\\""; break;
            case '\\': oss << "\\\\"; break;
            case '\b': oss << "\\b"; break;
            case '\f': oss << "\\f"; break;
            case '\n': oss << "\\n"; break;
            case '\r': oss << "\\r"; break;
            case '\t': oss << "\\t"; break;
            default:
                if (static_cast<unsigned char>(c) < 0x20) {
                    char buf[8];
                    std::snprintf(buf, sizeof(buf), "\\u%04x", static_cast<unsigned char>(c));
                    oss << buf;
                } else {
                    oss << c;
                }
                break;
        }
    }
    oss << "\"";
}

yanmo_engine_t* yanmo_create(void) {
    try {
        return new yanmo_engine_t();
    } catch (...) {
        return nullptr;
    }
}

void yanmo_destroy(yanmo_engine_t* engine) {
    try {
        delete engine;
    } catch (...) {}
}

int yanmo_init(yanmo_engine_t* engine, const char* lexicon_path, const char* radicals_path) {
    if (!engine || !lexicon_path || !radicals_path) return 0;
    try {
        return engine->engine.init(lexicon_path, radicals_path) ? 1 : 0;
    } catch (...) {
        return 0;
    }
}

int yanmo_load_user_dict(yanmo_engine_t* engine, const char* user_dict_path) {
    if (!engine || !user_dict_path) return 0;
    try {
        return engine->engine.load_user_dict(user_dict_path) ? 1 : 0;
    } catch (...) {
        return 0;
    }
}

int yanmo_load_bigram(yanmo_engine_t* engine, const char* bigram_path) {
    if (!engine || !bigram_path) return 0;
    try {
        return engine->engine.load_bigram(bigram_path) ? 1 : 0;
    } catch (...) {
        return 0;
    }
}

void yanmo_reset(yanmo_engine_t* engine) {
    if (!engine) return;
    try {
        engine->engine.reset();
    } catch (...) {}
}

int yanmo_feed_key(yanmo_engine_t* engine, const char* key, int is_shift, char* out_commit, int max_commit_len) {
    if (!engine || !key) return 0;
    if (out_commit && max_commit_len > 0) out_commit[0] = '\0';

    try {
        bool consumed = engine->engine.feed_key(key, is_shift != 0);

        const auto& status = engine->engine.get_status();
        if (!status.committed_text.empty() && out_commit && max_commit_len > 0) {
            std::strncpy(out_commit, status.committed_text.c_str(), max_commit_len - 1);
            out_commit[max_commit_len - 1] = '\0';
        }
        return consumed ? 1 : 0;
    } catch (...) {
        return 0;
    }
}

int yanmo_get_buffer(yanmo_engine_t* engine, char* out_buf, int max_len) {
    if (!engine || !out_buf || max_len <= 0) return 0;
    try {
        const auto& status = engine->engine.get_status();
        std::strncpy(out_buf, status.pinyin_buffer.c_str(), max_len - 1);
        out_buf[max_len - 1] = '\0';
        return static_cast<int>(status.pinyin_buffer.size());
    } catch (...) {
        out_buf[0] = '\0';
        return 0;
    }
}

int yanmo_get_radical_hint(yanmo_engine_t* engine, char* out_buf, int max_len) {
    if (!engine || !out_buf || max_len <= 0) return 0;
    try {
        const auto& status = engine->engine.get_status();
        std::string hint = status.radical_buffer;
        if (!status.radical_hint.empty()) {
            hint += " [" + status.radical_hint + "]";
        }
        std::strncpy(out_buf, hint.c_str(), max_len - 1);
        out_buf[max_len - 1] = '\0';
        return static_cast<int>(hint.size());
    } catch (...) {
        out_buf[0] = '\0';
        return 0;
    }
}

int yanmo_get_radical_buffer(yanmo_engine_t* engine, char* out_buf, int max_len) {
    if (!engine || !out_buf || max_len <= 0) return 0;
    try {
        const auto& status = engine->engine.get_status();
        std::strncpy(out_buf, status.radical_buffer.c_str(), max_len - 1);
        out_buf[max_len - 1] = '\0';
        return static_cast<int>(status.radical_buffer.size());
    } catch (...) {
        out_buf[0] = '\0';
        return 0;
    }
}

int yanmo_get_status(yanmo_engine_t* engine, 
                     int* out_mode, 
                     int* out_total_cands, 
                     int* out_page_offset, 
                     int* out_active_row, 
                     int* out_is_expanded) {
    if (!engine) return 0;
    try {
        const auto& s = engine->engine.get_status();
        if (out_mode) *out_mode = static_cast<int>(s.mode);
        if (out_total_cands) *out_total_cands = static_cast<int>(s.total_candidates);
        if (out_page_offset) *out_page_offset = static_cast<int>(s.page_offset);
        if (out_active_row) *out_active_row = static_cast<int>(s.active_row);
        if (out_is_expanded) *out_is_expanded = s.is_expanded ? 1 : 0;
        return 1;
    } catch (...) {
        return 0;
    }
}

int yanmo_get_row_candidates_json(yanmo_engine_t* engine, int row_idx, char* out_buf, int max_len) {
    if (!engine) return -1;
    try {
        auto cands = engine->engine.get_row_candidates(row_idx >= 0 ? row_idx : 0);

        std::ostringstream oss;
        oss << "[";
        for (size_t i = 0; i < cands.size(); ++i) {
            if (i > 0) oss << ",";
            escape_json_string(cands[i].word, oss);
        }
        oss << "]";

        std::string json_str = oss.str();
        int needed_len = static_cast<int>(json_str.size() + 1);
        if (!out_buf || max_len < needed_len) {
            if (out_buf && max_len > 0) out_buf[0] = '\0';
            return -needed_len;
        }
        std::memcpy(out_buf, json_str.c_str(), needed_len);
        return static_cast<int>(cands.size());
    } catch (...) {
        if (out_buf && max_len > 0) out_buf[0] = '\0';
        return -1;
    }
}

int yanmo_get_candidates_json(yanmo_engine_t* engine, int max_cands, char* out_buf, int max_len) {
    if (!engine) return -1;
    try {
        auto cands = engine->engine.get_current_candidates();
        size_t limit = (max_cands > 0) ? std::min(cands.size(), static_cast<size_t>(max_cands)) : cands.size();

        std::ostringstream oss;
        oss << "[";
        for (size_t i = 0; i < limit; ++i) {
            if (i > 0) oss << ",";
            escape_json_string(cands[i].word, oss);
        }
        oss << "]";

        std::string json_str = oss.str();
        int needed_len = static_cast<int>(json_str.size() + 1);
        if (!out_buf || max_len < needed_len) {
            if (out_buf && max_len > 0) out_buf[0] = '\0';
            return -needed_len;
        }
        std::memcpy(out_buf, json_str.c_str(), needed_len);
        return static_cast<int>(limit);
    } catch (...) {
        if (out_buf && max_len > 0) out_buf[0] = '\0';
        return -1;
    }
}

int yanmo_save_user_bigram(yanmo_engine_t* engine, const char* filepath) {
    if (!engine || !filepath) return 0;
    try {
        return engine->engine.save_bigram(filepath) ? 1 : 0;
    } catch (...) {
        return 0;
    }
}

int yanmo_select_candidate(yanmo_engine_t* engine, int index, char* out_commit, int max_commit_len) {
    if (!engine) return 0;
    if (out_commit && max_commit_len > 0) out_commit[0] = '\0';
    try {
        std::string text = engine->engine.commit_candidate(index >= 0 ? index : 0);
        if (!text.empty() && out_commit && max_commit_len > 0) {
            std::strncpy(out_commit, text.c_str(), max_commit_len - 1);
            out_commit[max_commit_len - 1] = '\0';
        }
        return !text.empty() ? 1 : 0;
    } catch (...) {
        return 0;
    }
}

int yanmo_get_committed_text(yanmo_engine_t* engine, char* out_buf, int max_len) {
    if (!engine || !out_buf || max_len <= 0) return 0;
    try {
        const auto& status = engine->engine.get_status();
        std::strncpy(out_buf, status.committed_text.c_str(), max_len - 1);
        out_buf[max_len - 1] = '\0';
        return static_cast<int>(status.committed_text.size());
    } catch (...) {
        out_buf[0] = '\0';
        return 0;
    }
}

void yanmo_clear_committed_text(yanmo_engine_t* engine) {
    if (!engine) return;
    try {
        engine->engine.clear_committed_text();
    } catch (...) {}
}

int yanmo_set_row_size(yanmo_engine_t* engine, int row_size) {
    if (!engine || row_size < 3 || row_size > 10) return 0;
    try {
        engine->engine.set_row_size(static_cast<size_t>(row_size));
        return 1;
    } catch (...) {
        return 0;
    }
}

int yanmo_set_full_width_punct(yanmo_engine_t* engine, int enabled) {
    if (!engine) return 0;
    try {
        engine->engine.set_full_width_punct(enabled != 0);
        return 1;
    } catch (...) {
        return 0;
    }
}

int yanmo_get_full_width_punct(yanmo_engine_t* engine) {
    if (!engine) return 0;
    try {
        return engine->engine.is_full_width_punct() ? 1 : 0;
    } catch (...) {
        return 0;
    }
}

int yanmo_set_full_width_char(yanmo_engine_t* engine, int enabled) {
    if (!engine) return 0;
    try {
        engine->engine.set_full_width_char(enabled != 0);
        return 1;
    } catch (...) {
        return 0;
    }
}

int yanmo_get_full_width_char(yanmo_engine_t* engine) {
    if (!engine) return 0;
    try {
        return engine->engine.is_full_width_char() ? 1 : 0;
    } catch (...) {
        return 0;
    }
}

int yanmo_enter_radical_mode(yanmo_engine_t* engine) {
    if (!engine) return 0;
    try {
        engine->engine.enter_radical_mode();
        return 1;
    } catch (...) {
        return 0;
    }
}

int yanmo_set_radical_glyph(yanmo_engine_t* engine, const char* utf8_glyph) {
    if (!engine || !utf8_glyph) return 0;
    try {
        engine->engine.set_radical_glyph(utf8_glyph);
        return 1;
    } catch (...) {
        return 0;
    }
}
