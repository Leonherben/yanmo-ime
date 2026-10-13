#include "yanmo/speller.h"
#include <sstream>
#include <algorithm>
#include <cctype>

namespace yanmo {

static const char* const RAW_PINYIN_SYLLABLES = 
"a ai an ang ao ba bai ban bang bao bei ben beng bi bian biao bie bin bing bo bu "
"ca cai can cang cao ce cen ceng cha chai chan chang chao che chen cheng chi chong "
"chou chu chua chuai chuan chuang chui chun chuo ci cong cou cu cuan cui cun cuo "
"da dai dan dang dao de dei den deng di dia dian diao die ding diu dong dou du "
"duan dui dun duo e ei en eng er fa fan fang fei fen feng fo fou fu "
"ga gai gan gang gao ge gei gen geng gong gou gu gua guai guan guang gui gun guo "
"ha hai han hang hao he hei hen heng hong hou hu hua huai huan huang hui hun huo "
"ji jia jian jiang jiao jie jin jing jiong jiu ju juan jue jun "
"ka kai kan kang kao ke kei ken keng kong kou ku kua kuai kuan kuang kui kun kuo "
"la lai lan lang lao le lei leng li lia lian liang liao lie lin ling liu lo long "
"lou lu luan lun luo lv lve ma mai man mang mao me mei men meng mi mian miao mie "
"min ming miu mo mou mu na nai nan nang nao ne nei nen neng ni nian niang niao "
"nie nin ning niu nong nou nu nuan nun nuo nv nve o ou "
"pa pai pan pang pao pei pen peng pi pian piao pie pin ping po pou pu "
"qi qia qian qiang qiao qie qin qing qiong qiu qu quan que qun "
"ran rang rao re ren reng ri rong rou ru ruan rui run ruo "
"sa sai san sang sao se sen seng sha shai shan shang shao she shei shen sheng "
"shi shou shu shua shuai shuan shuang shui shun shuo si song sou su suan sui sun suo "
"ta tai tan tang tao te teng ti tian tiao tie ting tong tou tu tuan tui tun tuo "
"wa wai wan wang wei wen weng wo wu xi xia xian xiang xiao xie xin xing xiong xiu "
"xu xuan xue xun ya yan yang yao ye yi yin ying yo yong you yu yuan yue yun "
"za zai zan zang zao ze zei zen zeng zha zhai zhan zhang zhao zhe zhei zhen zheng "
"zhi zhong zhou zhu zhua zhuai zhuan zhuang zhui zhun zhuo zi zong zou zu zuan zui zun zuo";

Speller::Speller() {
    init_syllables();
}

Speller::Speller(const SpellingConfig& config) : config_(config) {
    init_syllables();
}

void Speller::init_syllables() {
    syllable_set_.clear();
    sorted_syllables_.clear();
    prefix_set_.clear();

    std::stringstream ss(RAW_PINYIN_SYLLABLES);
    std::string syl;
    while (ss >> syl) {
        syllable_set_.insert(syl);
        sorted_syllables_.push_back(syl);
        for (size_t i = 1; i <= syl.size(); ++i) {
            prefix_set_.insert(syl.substr(0, i));
        }
    }

    // Sort by length descending, then alphabetical
    std::sort(sorted_syllables_.begin(), sorted_syllables_.end(), [](const std::string& a, const std::string& b) {
        if (a.size() != b.size()) return a.size() > b.size();
        return a < b;
    });
}

bool Speller::is_valid_syllable(std::string_view syl) const {
    return syllable_set_.find(std::string(syl)) != syllable_set_.end();
}

bool Speller::is_valid_prefix(std::string_view prefix) const {
    return prefix_set_.find(std::string(prefix)) != prefix_set_.end();
}

std::string Speller::get_initial(std::string_view syl) const {
    if (syl.empty()) return "";
    if (syl.size() >= 2) {
        std::string_view d = syl.substr(0, 2);
        if (d == "zh" || d == "ch" || d == "sh") return std::string(d);
    }
    char c = syl[0];
    if (c == 'a' || c == 'e' || c == 'o') return ""; // 零声母
    return std::string(1, c);
}

std::string Speller::get_final(std::string_view syl) const {
    std::string init = get_initial(syl);
    return std::string(syl.substr(init.size()));
}

std::string Speller::normalize(std::string_view raw) const {
    std::string s;
    s.reserve(raw.size());
    for (char c : raw) {
        s.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(c))));
    }

    // 1. 经典正字法映射
    // lue -> lve, nue -> nve
    size_t pos = 0;
    while ((pos = s.find("lue", pos)) != std::string::npos) {
        s.replace(pos, 3, "lve");
        pos += 3;
    }
    pos = 0;
    while ((pos = s.find("nue", pos)) != std::string::npos) {
        s.replace(pos, 3, "nve");
        pos += 3;
    }

    // jv/qv/xv/yv -> ju/qu/xu/yu
    for (size_t i = 0; i + 1 < s.size(); ++i) {
        char c = s[i];
        if ((c == 'j' || c == 'q' || c == 'x' || c == 'y') && s[i + 1] == 'v') {
            s[i + 1] = 'u';
        }
    }

    // 2. 常见打字手误自动纠错 (搜狗式 Typo Correction)
    if (config_.enable_typo_correction) {
        // 倒装: "gn" -> "ng" (例如 zhaogn -> zhaong -> zhang, dign -> ding)
        // 只有当前面是元音或已不是合法拼音时替换
        for (size_t i = 1; i + 1 < s.size(); ++i) {
            if (s[i] == 'g' && s[i + 1] == 'n') {
                char prev = s[i - 1];
                if (prev == 'a' || prev == 'e' || prev == 'i' || prev == 'o' || prev == 'u') {
                    s[i] = 'n';
                    s[i + 1] = 'g';
                }
            }
        }
        // 结尾 "gn" -> "ng"
        if (s.size() >= 3 && s.substr(s.size() - 2) == "gn") {
            char prev = s[s.size() - 3];
            if (prev == 'a' || prev == 'e' || prev == 'i' || prev == 'o' || prev == 'u') {
                s[s.size() - 2] = 'n';
                s[s.size() - 1] = 'g';
            }
        }

        // 纠正 "zhaong" -> "zhang", "chaong" -> "chang", "shaong" -> "shang"
        pos = 0;
        while ((pos = s.find("aong", pos)) != std::string::npos) {
            s.erase(pos + 1, 1); // 变为 "ang"
        }

        // 纠正 "uen" -> "un" (声母后面)
        pos = 0;
        while ((pos = s.find("uen", pos)) != std::string::npos) {
            if (pos > 0 && s[pos - 1] != '\'' && s[pos - 1] != 'a' && s[pos - 1] != 'e' && s[pos - 1] != 'o') {
                s.erase(pos + 1, 1); // 变为 "un"
            } else {
                pos += 3;
            }
        }

        // 纠正 "iou" -> "iu" (声母后面)
        pos = 0;
        while ((pos = s.find("iou", pos)) != std::string::npos) {
            if (pos > 0 && s[pos - 1] != '\'' && s[pos - 1] != 'a' && s[pos - 1] != 'e' && s[pos - 1] != 'o') {
                s.erase(pos + 1, 1); // 删除 'o'，变为 "iu"
                pos += 2;
            } else {
                pos += 3;
            }
        }
    }

    return s;
}

static bool is_consonant_sequence(std::string_view s) {
    if (s.empty()) return false;
    for (char c : s) {
        if (c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u' || c == 'v' || c == '\'') {
            return false;
        }
        if (c < 'a' || c > 'z') return false;
    }
    return true;
}

std::vector<std::string> Speller::segment_tokens(std::string_view text, std::string& out_tail) const {
    out_tail.clear();
    if (text.empty()) return {};

    size_t n = text.size();
    std::vector<int> prev(n + 1, -1);
    prev[0] = 0;

    for (size_t i = 0; i < n; ++i) {
        if (prev[i] == -1) continue;
        for (const auto& syl : sorted_syllables_) {
            size_t l = syl.size();
            if (i + l <= n && text.substr(i, l) == syl) {
                if (prev[i + l] == -1) prev[i + l] = static_cast<int>(i);
            }
        }
    }

    if (prev[n] != -1) {
        std::vector<std::string> res;
        size_t curr = n;
        while (curr > 0) {
            size_t p = prev[curr];
            res.push_back(std::string(text.substr(p, curr - p)));
            curr = p;
        }
        std::reverse(res.begin(), res.end());
        return res;
    }

    // 检查末尾是否是不完整前缀或辅音简拼序列
    for (size_t i = n - 1; i > 0; --i) {
        if (prev[i] != -1) {
            std::string_view tail = text.substr(i);
            if (is_valid_prefix(tail) || is_consonant_sequence(tail)) {
                out_tail = std::string(tail);
                std::vector<std::string> res;
                size_t curr = i;
                while (curr > 0) {
                    size_t p = prev[curr];
                    res.push_back(std::string(text.substr(p, curr - p)));
                    curr = p;
                }
                std::reverse(res.begin(), res.end());
                return res;
            }
        }
    }

    return {};
}

std::vector<std::string> Speller::segment_simple(std::string_view text) const {
    std::string tail;
    return segment_tokens(text, tail);
}

std::vector<std::vector<std::string>> Speller::segment_all_paths(std::string_view text) const {
    if (text.empty()) return {};
    size_t n = text.size();

    // DAG 搜索所有有效切分
    std::vector<std::vector<std::vector<std::string>>> dp(n + 1);
    dp[0] = {{}};

    for (size_t i = 0; i < n; ++i) {
        if (dp[i].empty()) continue;
        for (const auto& syl : sorted_syllables_) {
            size_t l = syl.size();
            if (i + l <= n && text.substr(i, l) == syl) {
                for (const auto& path : dp[i]) {
                    if (dp[i + l].size() < 10) { // 限制备选路径上限
                        auto new_path = path;
                        new_path.push_back(syl);
                        dp[i + l].push_back(std::move(new_path));
                    }
                }
            }
        }
    }

    return dp[n];
}

std::vector<std::vector<std::string>> Speller::generate_fuzzy_variations(
    const std::vector<std::string>& syllables
) const {
    if (syllables.empty()) return {};

    // 针对每个音节派生可能的模糊音变体
    std::vector<std::vector<std::string>> candidates_per_slot;
    for (const auto& syl : syllables) {
        std::vector<std::string> slot_variants;
        slot_variants.push_back(syl);

        std::string init = get_initial(syl);
        std::string fin = get_final(syl);

        // 1. 声母模糊
        std::string new_init = init;
        if (config_.fuzzy_zh_z) {
            if (init == "zh") new_init = "z";
            else if (init == "z") new_init = "zh";
        }
        if (config_.fuzzy_ch_c) {
            if (init == "ch") new_init = "c";
            else if (init == "c") new_init = "ch";
        }
        if (config_.fuzzy_sh_s) {
            if (init == "sh") new_init = "s";
            else if (init == "s") new_init = "sh";
        }
        if (config_.fuzzy_l_n) {
            if (init == "l") new_init = "n";
            else if (init == "n") new_init = "l";
        }
        if (config_.fuzzy_f_h) {
            if (init == "f") new_init = "h";
            else if (init == "h") new_init = "f";
        }
        if (config_.fuzzy_r_l) {
            if (init == "r") new_init = "l";
            else if (init == "l") new_init = "r";
        }

        if (new_init != init) {
            std::string derived = new_init + fin;
            if (is_valid_syllable(derived)) slot_variants.push_back(derived);
        }

        // 2. 韵母模糊
        std::string new_fin = fin;
        if (config_.fuzzy_an_ang) {
            if (fin == "an") new_fin = "ang";
            else if (fin == "ang") new_fin = "an";
            else if (fin == "ian") new_fin = "iang";
            else if (fin == "iang") new_fin = "ian";
            else if (fin == "uan") new_fin = "uang";
            else if (fin == "uang") new_fin = "uan";
        }
        if (config_.fuzzy_en_eng) {
            if (fin == "en") new_fin = "eng";
            else if (fin == "eng") new_fin = "en";
        }
        if (config_.fuzzy_in_ing) {
            if (fin == "in") new_fin = "ing";
            else if (fin == "ing") new_fin = "in";
        }

        if (new_fin != fin) {
            std::string derived = init + new_fin;
            if (is_valid_syllable(derived)) slot_variants.push_back(derived);
        }

        candidates_per_slot.push_back(slot_variants);
    }

    // 笛卡尔积展开派生序列（排除完全等于原序列的方案，限制最多 10 个变体）
    std::vector<std::vector<std::string>> variations;
    std::vector<std::string> current_path;

    auto dfs = [&](auto& self, size_t depth) -> void {
        if (depth == candidates_per_slot.size()) {
            if (current_path != syllables && variations.size() < 8) {
                variations.push_back(current_path);
            }
            return;
        }
        for (const auto& variant : candidates_per_slot[depth]) {
            current_path.push_back(variant);
            self(self, depth + 1);
            current_path.pop_back();
            if (variations.size() >= 8) break;
        }
    };

    dfs(dfs, 0);
    return variations;
}

SpellingParse Speller::parse(std::string_view raw_pinyin) const {
    SpellingParse res;
    res.raw_input = std::string(raw_pinyin);
    if (raw_pinyin.empty()) return res;

    // 1. 规范化与纠错
    res.normalized = normalize(raw_pinyin);

    // 2. 检查是否为简拼/缩写（全是辅音且长度>=2，或单字符声母）
    bool all_consonants = true;
    for (char c : res.normalized) {
        if (c == '\'' || c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u' || c == 'v') {
            all_consonants = false;
            break;
        }
    }
    if (all_consonants && res.normalized.size() >= 2) {
        res.is_abbreviation = true;
        // 提取声母序列 (支持 zh, ch, sh)
        size_t idx = 0;
        while (idx < res.normalized.size()) {
            if (idx + 1 < res.normalized.size()) {
                std::string pair = res.normalized.substr(idx, 2);
                if (pair == "zh" || pair == "ch" || pair == "sh") {
                    res.initials.push_back(pair);
                    idx += 2;
                    continue;
                }
            }
            res.initials.push_back(std::string(1, res.normalized[idx]));
            idx++;
        }
        return res;
    }

    // 3. 处理隔音符 (Delimiter `'`)
    if (res.normalized.find('\'') != std::string::npos) {
        std::stringstream ss(res.normalized);
        std::string part;
        bool all_valid = true;
        std::string last_tail;

        while (std::getline(ss, part, '\'')) {
            if (part.empty()) continue;
            std::string sub_tail;
            auto sub_segs = segment_tokens(part, sub_tail);
            if (!sub_segs.empty()) {
                res.primary_syllables.insert(res.primary_syllables.end(), sub_segs.begin(), sub_segs.end());
                last_tail = sub_tail;
            } else {
                if (is_valid_prefix(part) || is_consonant_sequence(part)) {
                    last_tail = part;
                } else {
                    all_valid = false;
                    break;
                }
            }
        }
        if (all_valid) {
            res.trailing_incomplete = last_tail;
        }
    } else {
        // 无隔音符：执行动态规划切分
        res.primary_syllables = segment_tokens(res.normalized, res.trailing_incomplete);

        // 如果存在歧义切分（如 xian 既是 xian 也是 xi + an），生成备选切分
        auto all_paths = segment_all_paths(res.normalized);
        for (auto& path : all_paths) {
            if (path != res.primary_syllables) {
                res.alt_segmentations.push_back(std::move(path));
            }
        }
    }

    // 4. 提取声母
    for (const auto& syl : res.primary_syllables) {
        res.initials.push_back(get_initial(syl));
    }
    if (!res.trailing_incomplete.empty() && is_consonant_sequence(res.trailing_incomplete)) {
        size_t idx = 0;
        while (idx < res.trailing_incomplete.size()) {
            if (idx + 1 < res.trailing_incomplete.size()) {
                std::string pair = res.trailing_incomplete.substr(idx, 2);
                if (pair == "zh" || pair == "ch" || pair == "sh") {
                    res.initials.push_back(pair);
                    idx += 2;
                    continue;
                }
            }
            res.initials.push_back(std::string(1, res.trailing_incomplete[idx]));
            idx++;
        }
    }

    // 5. 生成模糊音派生
    if (!res.primary_syllables.empty()) {
        res.fuzzy_variations = generate_fuzzy_variations(res.primary_syllables);
    }

    // 6. 音节网格图（Syllable Lattice）全局多路径分析与全简分块
    SyllableLattice lattice;
    res.lattice_paths = lattice.search_top_k(
        res.normalized, syllable_set_, prefix_set_, sorted_syllables_, 5
    );

    if (!res.lattice_paths.empty()) {
        const auto& best_path = res.lattice_paths[0];
        res.primary_chunks = best_path.chunks;

        bool has_full = false, has_abbrev = false;
        for (const auto& ch : res.primary_chunks) {
            if (ch.is_abbrev) has_abbrev = true;
            else has_full = true;
        }

        if (has_abbrev && !has_full) {
            res.is_abbreviation = true;
        } else if (has_abbrev && has_full) {
            res.is_hybrid = true;
        } else if (!has_abbrev && res.primary_syllables.empty()) {
            for (const auto& e : best_path.edges) {
                if (e.type == EdgeType::EXACT_SYLLABLE || e.type == EdgeType::FUZZY_SYLLABLE) {
                    res.primary_syllables.push_back(e.text);
                    res.initials.push_back(get_initial(e.text));
                }
            }
        }
    }

    return res;
}

} // namespace yanmo
