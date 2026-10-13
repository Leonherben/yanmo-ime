#include "yanmo/pinyin_matcher.h"
#include <algorithm>
#include <unordered_set>
#include <cctype>

namespace yanmo {

static size_t utf8_length(std::string_view str) {
    size_t count = 0;
    for (unsigned char c : str) {
        if ((c & 0xC0) != 0x80) count++;
    }
    return count;
}

static bool is_single_char(std::string_view str) {
    return utf8_length(str) == 1;
}

static bool is_single_initial(std::string_view s) {
    if (s.size() != 1) return false;
    char c = static_cast<char>(std::tolower(static_cast<unsigned char>(s[0])));
    return c != 'a' && c != 'e' && c != 'i' && c != 'o' && c != 'u' && c != 'v' && std::isalpha(static_cast<unsigned char>(c));
}

static bool is_dual_initial(std::string_view s) {
    return s == "zh" || s == "ch" || s == "sh";
}

std::vector<Candidate> PinyinMatcher::query(std::string_view pinyin) const {
    if (pinyin.empty()) return {};

    // 1. 委托独立的 Speller 引擎进行规范化、手误纠错、隔音符切分与简拼分析
    SpellingParse parse = speller_.parse(pinyin);

    // 去除隔音符后的干净 key 用于 Trie 检索
    std::string lookup_key;
    lookup_key.reserve(parse.normalized.size());
    for (char c : parse.normalized) {
        if (c != '\'') lookup_key.push_back(c);
    }
    if (lookup_key.empty()) return {};

    std::vector<Candidate> results;
    auto comp = [this](const Candidate& a, const Candidate& b) {
        int fa = get_effective_frequency(a);
        int fb = get_effective_frequency(b);
        if (fa != fb) return fa > fb;
        return a.word.size() < b.word.size();
    };

    auto dedup = [](std::vector<Candidate>& vec) {
        std::unordered_set<std::string> seen_words;
        std::vector<Candidate> out;
        out.reserve(vec.size());
        for (auto& c : vec) {
            if (seen_words.insert(c.word).second) {
                out.push_back(std::move(c));
            }
        }
        vec = std::move(out);
    };

    // 2. 长句解码 (Sentence Decoder: 基于 2-Gram 语言模型 + Viterbi / DP 组句)
    std::string sentence_cand;
    if (lookup_key.size() >= 4 && !parse.primary_syllables.empty()) {
        auto lookup_fn = [this](std::string_view p) {
            return this->get_best_exact(p);
        };

        if (parse.trailing_incomplete.empty()) {
            if (parse.primary_syllables.size() >= 2) {
                sentence_cand = decoder_.decode(parse.primary_syllables, lookup_fn, &bigram_).first;
            }
        } else {
            sentence_cand = decoder_.decode_with_prefix(
                parse.primary_syllables,
                parse.trailing_incomplete,
                speller_.get_all_syllables(),
                lookup_fn,
                &bigram_
            ).first;
        }
    }

    // 2.5 工业级全简拼无缝混合解码 (学习 RIME 与搜狗多粒度 Chunk Composition)
    std::vector<Candidate> hybrid_cands;
    if (parse.is_hybrid && parse.primary_chunks.size() >= 2) {
        // 为每一个 chunk 获取候选词集合
        std::vector<std::vector<Candidate>> chunk_candidates;
        auto lookup_fn = [this](std::string_view p) {
            return this->get_best_exact(p);
        };

        for (const auto& chunk : parse.primary_chunks) {
            std::vector<Candidate> cands;
            if (chunk.is_abbrev) {
                if (chunk.text.size() >= 2) {
                    // 简拼块（长度>=2）：查 abbrev_trie_
                    std::vector<uint32_t> abbrev_indices;
                    abbrev_trie_.search_prefix(chunk.text, abbrev_indices);
                    size_t k_len = chunk.text.size();
                    for (uint32_t idx : abbrev_indices) {
                        if (idx < lexicon_.size()) {
                            const auto& c = lexicon_[idx];
                            if (utf8_length(c.word) == k_len) {
                                cands.push_back(c);
                            }
                        }
                    }
                } else if (chunk.text.size() == 1) {
                    // 单声母：直接取预索引的单字
                    auto it = initial_single_chars_.find(chunk.text);
                    if (it != initial_single_chars_.end()) {
                        for (size_t k = 0; k < std::min<size_t>(20, it->second.size()); ++k) {
                            cands.push_back(lexicon_[it->second[k]]);
                        }
                    }
                }
            } else {
                // 全拼块：先查是否有整词
                if (const auto* exact_indices = trie_.search_exact(chunk.text)) {
                    for (uint32_t idx : *exact_indices) {
                        if (idx < lexicon_.size() && lexicon_[idx].pinyin == chunk.text) {
                            cands.push_back(lexicon_[idx]);
                        }
                    }
                }
                // 若无整词且有多音节，用 SentenceDecoder 组词
                if (cands.empty() && chunk.tokens.size() > 1) {
                    auto [decoded_w, decoded_sc] = decoder_.decode(chunk.tokens, lookup_fn, &bigram_);
                    if (!decoded_w.empty()) {
                        cands.push_back(Candidate{decoded_w, chunk.text, "", decoded_sc});
                    }
                }
                // 若仍为空，逐个音节取最优单字
                if (cands.empty()) {
                    std::string word_seq;
                    int f_sum = 0;
                    for (const auto& tok : chunk.tokens) {
                        auto [w, f] = lookup_fn(tok);
                        word_seq += w;
                        f_sum += f;
                    }
                    if (!word_seq.empty()) {
                        cands.push_back(Candidate{word_seq, chunk.text, "", f_sum / static_cast<int>(chunk.tokens.size())});
                    }
                }
            }

            std::sort(cands.begin(), cands.end(), comp);
            dedup(cands);
            if (cands.size() > 6) cands.resize(6);
            chunk_candidates.push_back(std::move(cands));
        }

        // DP 拼接各个 chunk 的候选词，并计算 Bigram 转移概率
        bool all_non_empty = true;
        for (const auto& cc : chunk_candidates) {
            if (cc.empty()) { all_non_empty = false; break; }
        }

        if (all_non_empty) {
            struct Chain {
                std::string word;
                std::string last_word;
                int score = 0;
            };

            std::vector<Chain> chains;
            for (const auto& c : chunk_candidates[0]) {
                chains.push_back({ c.word, c.word, c.freq });
            }

            for (size_t i = 1; i < chunk_candidates.size(); ++i) {
                std::vector<Chain> next_chains;
                for (const auto& chain : chains) {
                    for (const auto& next_cand : chunk_candidates[i]) {
                        int trans = bigram_.get_transition_score(chain.last_word, next_cand.word);
                        int total = chain.score + next_cand.freq + 35000 + trans;
                        next_chains.push_back({ chain.word + next_cand.word, next_cand.word, total });
                    }
                }
                std::sort(next_chains.begin(), next_chains.end(), [](const Chain& a, const Chain& b) {
                    return a.score > b.score;
                });
                if (next_chains.size() > 8) next_chains.resize(8);
                chains = std::move(next_chains);
            }

            for (const auto& chain : chains) {
                hybrid_cands.push_back(Candidate{chain.word, lookup_key, "", chain.score + 50000});
            }
        }
    }

    // 次级兜底：全拼前缀 + 简拼后缀 (例如 "shuosmn" -> "shuo" + "smn")
    if (hybrid_cands.empty() && !parse.primary_syllables.empty() && parse.trailing_incomplete.size() >= 2) {
        std::string tail = parse.trailing_incomplete;
        std::vector<uint32_t> tail_abbrev_indices;
        abbrev_trie_.search_prefix(tail, tail_abbrev_indices);
        if (!tail_abbrev_indices.empty()) {
            auto lookup_fn = [this](std::string_view p) {
                return this->get_best_exact(p);
            };
            std::string head_text;
            if (parse.primary_syllables.size() == 1) {
                head_text = lookup_fn(parse.primary_syllables[0]).first;
            } else {
                head_text = decoder_.decode(parse.primary_syllables, lookup_fn, &bigram_).first;
            }

            if (!head_text.empty()) {
                std::unordered_set<std::string> seen_hybrid;
                for (uint32_t idx : tail_abbrev_indices) {
                    if (idx < lexicon_.size()) {
                        const auto& tail_cand = lexicon_[idx];
                        std::string hybrid_word = head_text + tail_cand.word;
                        if (seen_hybrid.insert(hybrid_word).second) {
                            int trans_score = bigram_.get_transition_score(head_text, tail_cand.word);
                            int hybrid_freq = tail_cand.freq + 40000 + trans_score;
                            hybrid_cands.push_back(Candidate{hybrid_word, lookup_key, "", hybrid_freq});
                        }
                    }
                }
                std::sort(hybrid_cands.begin(), hybrid_cands.end(), comp);
            }
        }
    }

    if (sentence_cand.empty() && !hybrid_cands.empty()) {
        sentence_cand = hybrid_cands[0].word;
    }

    // 3. 简拼/缩写快速通道 (Abbreviation Tiered Search)
    if (parse.is_abbreviation && !is_dual_initial(lookup_key)) {
        size_t K = lookup_key.size();
        std::unordered_set<std::string> seen_words;

        // Tier 1: 长度完全匹配当前缩写字数的词条 (例如 wzx -> 3字词)
        std::vector<uint32_t> abbrev_indices;
        abbrev_trie_.search_prefix(lookup_key, abbrev_indices);
        std::vector<Candidate> tier1;
        for (uint32_t idx : abbrev_indices) {
            if (idx < lexicon_.size()) {
                const auto& c = lexicon_[idx];
                size_t len = utf8_length(c.word);
                if (len <= K && len >= 2) {
                    if (seen_words.insert(c.word).second) {
                        tier1.push_back(c);
                    }
                }
            }
        }
        std::sort(tier1.begin(), tier1.end(), comp);
        for (auto& c : tier1) results.push_back(std::move(c));

        // Tier 2: 降级匹配 K-1 到 2 字符的缩写词
        for (size_t l = K - 1; l >= 2; --l) {
            std::string sub_pref = lookup_key.substr(0, l);
            std::vector<uint32_t> sub_indices;
            abbrev_trie_.search_prefix(sub_pref, sub_indices);
            std::vector<Candidate> tier2;
            for (uint32_t idx : sub_indices) {
                if (idx < lexicon_.size()) {
                    const auto& c = lexicon_[idx];
                    if (utf8_length(c.word) == l) {
                        if (seen_words.insert(c.word).second) {
                            tier2.push_back(c);
                        }
                    }
                }
            }
            std::sort(tier2.begin(), tier2.end(), comp);
            for (auto& c : tier2) results.push_back(std::move(c));
        }

        // Tier 3: 首字母单字
        std::string first_init = lookup_key.substr(0, 1);
        auto it = initial_single_chars_.find(first_init);
        if (it != initial_single_chars_.end()) {
            std::vector<Candidate> tier3;
            for (size_t k = 0; k < std::min<size_t>(50, it->second.size()); ++k) {
                const auto& c = lexicon_[it->second[k]];
                if (seen_words.insert(c.word).second) {
                    tier3.push_back(c);
                }
            }
            std::sort(tier3.begin(), tier3.end(), comp);
            for (auto& c : tier3) results.push_back(std::move(c));
        }

        if (results.size() > 500) results.resize(500);
        return results;
    }

    // 3.5 单声母快速通道 (Single initial fast-path)
    if (is_single_initial(lookup_key)) {
        auto it = initial_single_chars_.find(lookup_key);
        if (it != initial_single_chars_.end()) {
            for (uint32_t idx : it->second) {
                results.push_back(lexicon_[idx]);
                if (results.size() >= 500) break;
            }
            if (!user_learned_.empty()) {
                std::sort(results.begin(), results.end(), comp);
            }
        }
        return results;
    }

    // 4. 标准 Trie 前缀检索
    std::vector<uint32_t> indices;
    trie_.search_prefix(lookup_key, indices);
    std::unordered_set<uint32_t> seen;
    std::vector<Candidate> exact, prefix_multi, prefix_single;

    bool has_delimiter = (parse.raw_input.find('\'') != std::string::npos);

    for (uint32_t idx : indices) {
        if (idx < lexicon_.size() && seen.insert(idx).second) {
            const auto& c = lexicon_[idx];
            if (c.pinyin == lookup_key) {
                // 如果用户敲了显式隔音符 (如 xi'an)，单音节字 "先" 不算隔音匹配，多音节词优先
                if (has_delimiter && parse.primary_syllables.size() > 1 && is_single_char(c.word)) {
                    prefix_single.push_back(c);
                } else {
                    exact.push_back(c);
                }
            } else if (is_single_char(c.word)) {
                prefix_single.push_back(c);
            } else {
                prefix_multi.push_back(c);
            }
        }
    }

    // 4.1 容错纠错拼音检索 (Typo / Fuzzy Syllable from SyllableLattice)
    if (exact.empty() && !parse.lattice_paths.empty()) {
        for (const auto& path : parse.lattice_paths) {
            bool has_fuzzy = false;
            std::string corr_key;
            for (const auto& e : path.edges) {
                corr_key += e.text;
                if (e.type == EdgeType::FUZZY_SYLLABLE) has_fuzzy = true;
            }
            if (has_fuzzy && !corr_key.empty() && corr_key != lookup_key) {
                std::vector<uint32_t> corr_indices;
                trie_.search_prefix(corr_key, corr_indices);
                for (uint32_t idx : corr_indices) {
                    if (idx < lexicon_.size() && seen.insert(idx).second) {
                        const auto& c = lexicon_[idx];
                        if (c.pinyin == corr_key) {
                            exact.push_back(c);
                        } else if (is_single_char(c.word)) {
                            prefix_single.push_back(c);
                        } else {
                            prefix_multi.push_back(c);
                        }
                    }
                }
                if (!exact.empty()) break;
            }
        }
    }

    std::sort(exact.begin(), exact.end(), comp);
    std::sort(prefix_multi.begin(), prefix_multi.end(), comp);
    std::sort(prefix_single.begin(), prefix_single.end(), comp);

    dedup(exact);
    dedup(prefix_multi);
    dedup(prefix_single);

    // 双声母处理 (zh, ch, sh)
    if (is_dual_initial(lookup_key)) {
        size_t s_idx = 0;
        for (int k = 0; k < 10 && s_idx < prefix_single.size(); ++k) results.push_back(prefix_single[s_idx++]);
        for (const auto& m : prefix_multi) if (m.freq >= 7000) results.push_back(m);
        while (s_idx < prefix_single.size()) results.push_back(prefix_single[s_idx++]);
        for (const auto& m : prefix_multi) if (m.freq < 7000 && results.size() < 500) results.push_back(m);
        return results;
    }

    // 组合精确匹配与前缀匹配
    if (!exact.empty()) {
        size_t e_idx = 0, p_idx = 0;
        for (int r = 0; r < 3; ++r) {
            for (int k = 0; k < 2 && e_idx < exact.size(); ++k) results.push_back(exact[e_idx++]);
            if (p_idx < prefix_multi.size() && prefix_multi[p_idx].freq >= 7500) results.push_back(prefix_multi[p_idx++]);
        }
        while (e_idx < exact.size()) results.push_back(exact[e_idx++]);
        while (p_idx < prefix_multi.size() && results.size() < 500) results.push_back(prefix_multi[p_idx++]);
    } else {
        results = std::move(prefix_multi);
        results.insert(results.end(), prefix_single.begin(), prefix_single.end());
        std::sort(results.begin(), results.end(), comp);
    }

    // 4.5 混合拼音与前缀音节候选补充
    if (!hybrid_cands.empty()) {
        for (auto& hc : hybrid_cands) {
            results.push_back(std::move(hc));
        }
    }

    if (!parse.primary_syllables.empty() && !parse.trailing_incomplete.empty()) {
        std::string pref_key;
        for (const auto& syl : parse.primary_syllables) pref_key += syl;
        std::vector<uint32_t> pref_indices;
        trie_.search_prefix(pref_key, pref_indices);
        std::vector<Candidate> pref_cands;
        for (uint32_t idx : pref_indices) {
            if (idx < lexicon_.size()) {
                pref_cands.push_back(lexicon_[idx]);
            }
        }
        if (pref_cands.size() > 30) {
            std::partial_sort(pref_cands.begin(), pref_cands.begin() + 30, pref_cands.end(), comp);
            pref_cands.resize(30);
        } else {
            std::sort(pref_cands.begin(), pref_cands.end(), comp);
        }
        for (auto& pc : pref_cands) {
            pc.freq = std::max(1, pc.freq - 3000);
            results.push_back(std::move(pc));
        }
    }

    // 5. 模糊音候选词注入 (Fuzzy Variation Candidates)
    if (!parse.fuzzy_variations.empty()) {
        std::unordered_set<std::string> existing_words;
        for (const auto& c : results) existing_words.insert(c.word);

        for (const auto& var_path : parse.fuzzy_variations) {
            std::string var_key;
            for (const auto& s : var_path) var_key += s;
            if (const auto* var_indices = trie_.search_exact(var_key)) {
                for (uint32_t v_idx : *var_indices) {
                    if (v_idx < lexicon_.size()) {
                        const auto& c = lexicon_[v_idx];
                        if (c.pinyin == var_key && existing_words.insert(c.word).second) {
                            Candidate fuzzy_c = c;
                            // 稍微降权，排在标准拼音候选之后
                            fuzzy_c.freq = std::max(1, c.freq - 1500);
                            results.push_back(std::move(fuzzy_c));
                            if (results.size() >= 300) break;
                        }
                    }
                }
            }
        }
    }

    if (results.size() > 500) results.resize(500);

    // 6. 将长句候选插入第一位
    if (!sentence_cand.empty()) {
        auto it = std::find_if(results.begin(), results.end(), [&](const Candidate& c) {
            return c.word == sentence_cand;
        });
        if (it != results.end()) {
            results.erase(it);
        }
        results.insert(results.begin(), Candidate{sentence_cand, lookup_key, "", 99999});
    }

    // 7. 终极兜底保障：若结果仍为空，回退到最大前缀匹配，绝不返回空白
    if (results.empty()) {
        for (size_t l = lookup_key.size() - 1; l >= 1; --l) {
            std::string sub_key = lookup_key.substr(0, l);
            std::vector<uint32_t> sub_indices;
            trie_.search_prefix(sub_key, sub_indices);
            if (!sub_indices.empty()) {
                for (uint32_t idx : sub_indices) {
                    if (idx < lexicon_.size()) {
                        results.push_back(lexicon_[idx]);
                    }
                }
                std::sort(results.begin(), results.end(), comp);
                break;
            }
        }
    }

    dedup(results);
    if (results.size() > 500) results.resize(500);
    return results;
}

} // namespace yanmo
