#pragma once

#include "types.h"
#include "lattice.h"
#include <string>
#include <string_view>
#include <vector>
#include <unordered_set>
#include <unordered_map>

namespace yanmo {

// 拼写配置（模糊音、自动手误纠错等）
struct SpellingConfig {
    bool enable_typo_correction = true; // 自动纠正常见击键倒装与手误（如 gn -> ng）
    bool fuzzy_zh_z = false;           // zh <-> z
    bool fuzzy_ch_c = false;           // ch <-> c
    bool fuzzy_sh_s = false;           // sh <-> s
    bool fuzzy_an_ang = false;         // an <-> ang
    bool fuzzy_en_eng = false;         // en <-> eng
    bool fuzzy_in_ing = false;         // in <-> ing
    bool fuzzy_l_n = false;            // l <-> n
    bool fuzzy_f_h = false;            // f <-> h
    bool fuzzy_r_l = false;            // r <-> l
};

// 拼写解析结果（纯音素/字符层面的切分与派生）
struct SpellingParse {
    std::string raw_input;                                       // 原始输入 (如 "xi'an", "zhaogn")
    std::string normalized;                                      // 规范化与纠错后的拼写 (如 "xi'an", "zhang")
    std::vector<std::string> primary_syllables;                  // 首选音节切分 (如 ["xi", "an"])
    std::string trailing_incomplete;                             // 未闭合的前缀音节 (如 "niha" -> ["ni"] + "ha")
    std::vector<std::vector<std::string>> alt_segmentations;     // 备选切分 (如 ["xian"])
    std::vector<std::vector<std::string>> fuzzy_variations;      // 模糊音派生变体 (如 [["zi", "an"], ...])
    bool is_abbreviation = false;                                // 是否为纯简拼/缩写 (如 "zg", "bj")
    bool is_hybrid = false;                                      // 是否为全简拼混合 (如 "zgguoji", "shuosmn")
    std::vector<std::string> initials;                           // 提取的声母序列
    std::vector<SegmentPath> lattice_paths;                      // 网格图 Top-K 加权切分路径
    std::vector<SegmentChunk> primary_chunks;                    // 首选路径切分出的连续全简块
};

class Speller {
public:
    Speller();
    explicit Speller(const SpellingConfig& config);
    ~Speller() = default;

    // 配置管理
    void set_config(const SpellingConfig& config) { config_ = config; }
    const SpellingConfig& get_config() const { return config_; }

    // 核心解析入口
    SpellingParse parse(std::string_view raw_pinyin) const;

    // 轻量级音节快速切分（跳过全网格图构建与模糊音笛卡尔积，用于高频检索与词库初始化）
    std::vector<std::string> segment_simple(std::string_view text) const;

    // 规范化与手误纠错
    std::string normalize(std::string_view raw) const;

    // 音节与前缀合法性校验
    bool is_valid_syllable(std::string_view syl) const;
    bool is_valid_prefix(std::string_view prefix) const;

    // 声母与韵母拆解
    std::string get_initial(std::string_view syl) const;
    std::string get_final(std::string_view syl) const;

    // 音节库全集引用
    const std::vector<std::string>& get_all_syllables() const { return sorted_syllables_; }

private:
    void init_syllables();

    // 内部切分核心（支持隔音符）
    std::vector<std::string> segment_tokens(std::string_view text, std::string& out_tail) const;
    std::vector<std::vector<std::string>> segment_all_paths(std::string_view text) const;

    // 模糊音派生
    std::vector<std::vector<std::string>> generate_fuzzy_variations(const std::vector<std::string>& syllables) const;

    SpellingConfig config_;
    std::unordered_set<std::string> syllable_set_;
    std::vector<std::string> sorted_syllables_; // 按长度降序排列
    std::unordered_set<std::string> prefix_set_;
};

} // namespace yanmo
