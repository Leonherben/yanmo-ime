#include "yanmo/decoder.h"
#include <algorithm>

namespace yanmo {

std::pair<std::string, int> SentenceDecoder::decode(
    const std::vector<std::string>& syllables,
    const std::function<std::pair<std::string, int>(std::string_view)>& exact_lookup,
    const BigramModel* bigram
) const {
    if (syllables.empty()) return {"", -1};
    size_t n = syllables.size();
    
    struct DPNode {
        int score = -1;
        int prev_idx = -1;
        std::string word;
    };
    
    std::vector<DPNode> dp(n + 1);
    dp[0] = {0, -1, ""};

    for (size_t i = 0; i < n; ++i) {
        if (dp[i].score == -1) continue;
        std::string sub_py;
        for (size_t l = 1; l <= 6 && i + l <= n; ++l) {
            sub_py += syllables[i + l - 1];
            auto [w, freq] = exact_lookup(sub_py);
            if (!w.empty()) {
                // 1. Unigram 词频与长度奖励 (优先成词长词)
                int word_score = freq + static_cast<int>(l - 1) * 35000;

                // 2. 2-Gram 转移奖励：如果上一个词与当前词搭配度高，获得高额语言模型加分
                int bigram_score = 0;
                if (bigram && dp[i].prev_idx != -1) {
                    bigram_score = bigram->get_transition_score(dp[i].word, w);
                }

                int new_score = dp[i].score + word_score + bigram_score;
                if (new_score > dp[i + l].score) {
                    dp[i + l] = {new_score, static_cast<int>(i), w};
                }
            }
        }
    }

    if (dp[n].score == -1) return {"", -1};
    std::vector<std::string> words;
    int curr = static_cast<int>(n);
    while (curr > 0 && dp[curr].prev_idx != -1) {
        words.push_back(dp[curr].word);
        curr = dp[curr].prev_idx;
    }
    std::string res;
    for (auto it = words.rbegin(); it != words.rend(); ++it) {
        res += *it;
    }
    return {res, dp[n].score};
}

std::pair<std::string, int> SentenceDecoder::decode_with_prefix(
    const std::vector<std::string>& prefix_syllables,
    std::string_view tail,
    const std::vector<std::string>& candidate_syllables,
    const std::function<std::pair<std::string, int>(std::string_view)>& exact_lookup,
    const BigramModel* bigram
) const {
    if (prefix_syllables.empty() || tail.empty()) return {"", -1};
    size_t k = prefix_syllables.size();

    // 1. Precompute prefix DP once
    struct DPNode {
        int score = -1;
        int prev_idx = -1;
        std::string word;
    };

    std::vector<DPNode> prefix_dp(k + 1);
    prefix_dp[0] = {0, -1, ""};

    for (size_t i = 0; i < k; ++i) {
        if (prefix_dp[i].score == -1) continue;
        std::string sub_py;
        for (size_t l = 1; l <= 6 && i + l <= k; ++l) {
            sub_py += prefix_syllables[i + l - 1];
            auto [w, freq] = exact_lookup(sub_py);
            if (!w.empty()) {
                int word_score = freq + static_cast<int>(l - 1) * 35000;
                int bigram_score = 0;
                if (bigram && prefix_dp[i].prev_idx != -1) {
                    bigram_score = bigram->get_transition_score(prefix_dp[i].word, w);
                }
                int new_score = prefix_dp[i].score + word_score + bigram_score;
                if (new_score > prefix_dp[i + l].score) {
                    prefix_dp[i + l] = {new_score, static_cast<int>(i), w};
                }
            }
        }
    }

    std::string best_res;
    int best_score = -1;

    // 2. Only test transitions for the trailing syllable matching prefix
    for (const auto& syl : candidate_syllables) {
        if (syl.rfind(tail, 0) != 0) continue;

        int syl_best_score = -1;
        int syl_best_prev = -1;
        std::string syl_best_word;

        // Word length 1: just syl
        auto [w1, freq1] = exact_lookup(syl);
        if (!w1.empty() && prefix_dp[k].score != -1) {
            int word_score = freq1;
            int bigram_score = 0;
            if (bigram && prefix_dp[k].prev_idx != -1) {
                bigram_score = bigram->get_transition_score(prefix_dp[k].word, w1);
            }
            int score = prefix_dp[k].score + word_score + bigram_score;
            if (score > syl_best_score) {
                syl_best_score = score;
                syl_best_prev = static_cast<int>(k);
                syl_best_word = w1;
            }
        }

        // Word length >= 2: combine previous syllables ending in syl
        for (size_t l = 2; l <= 6 && l <= k + 1; ++l) {
            size_t start_idx = (k + 1) - l;
            if (prefix_dp[start_idx].score == -1) continue;

            std::string comb_py;
            for (size_t m = start_idx; m < k; ++m) comb_py += prefix_syllables[m];
            comb_py += syl;

            auto [w, freq] = exact_lookup(comb_py);
            if (!w.empty()) {
                int word_score = freq + static_cast<int>(l - 1) * 35000;
                int bigram_score = 0;
                if (bigram && prefix_dp[start_idx].prev_idx != -1) {
                    bigram_score = bigram->get_transition_score(prefix_dp[start_idx].word, w);
                }
                int score = prefix_dp[start_idx].score + word_score + bigram_score;
                if (score > syl_best_score) {
                    syl_best_score = score;
                    syl_best_prev = static_cast<int>(start_idx);
                    syl_best_word = w;
                }
            }
        }

        if (syl_best_score > best_score) {
            best_score = syl_best_score;
            std::vector<std::string> words;
            words.push_back(syl_best_word);
            int curr = syl_best_prev;
            while (curr > 0 && prefix_dp[curr].prev_idx != -1) {
                words.push_back(prefix_dp[curr].word);
                curr = prefix_dp[curr].prev_idx;
            }
            std::string res;
            for (auto it = words.rbegin(); it != words.rend(); ++it) {
                res += *it;
            }
            best_res = std::move(res);
        }
    }

    return {best_res, best_score};
}

} // namespace yanmo
