#include "yanmo/lattice.h"
#include "yanmo/keyboard_model.h"
#include <algorithm>
#include <unordered_set>

namespace yanmo {

bool SyllableLattice::is_single_initial(char c) {
    switch (c) {
        case 'b': case 'p': case 'm': case 'f':
        case 'd': case 't': case 'n': case 'l':
        case 'g': case 'k': case 'h':
        case 'j': case 'q': case 'x':
        case 'r': case 'z': case 'c': case 's':
        case 'y': case 'w':
            return true;
        default:
            return false;
    }
}

bool SyllableLattice::is_initial(std::string_view s) {
    if (s.size() == 1) {
        return is_single_initial(s[0]);
    }
    if (s.size() == 2) {
        return (s == "zh" || s == "ch" || s == "sh");
    }
    return false;
}

static bool is_edge_abbrev(const LatticeEdge& edge) {
    if (edge.type == EdgeType::ABBREV_INITIAL) return true;
    if (edge.type == EdgeType::INCOMPLETE_PREFIX && SyllableLattice::is_initial(edge.text)) return true;
    return false;
}

std::vector<SegmentChunk> SyllableLattice::edges_to_chunks(const std::vector<LatticeEdge>& edges) {
    std::vector<SegmentChunk> chunks;
    if (edges.empty()) return chunks;

    SegmentChunk current;
    current.is_abbrev = is_edge_abbrev(edges[0]);
    current.text = edges[0].text;
    current.tokens.push_back(edges[0].text);

    for (size_t i = 1; i < edges.size(); ++i) {
        const auto& edge = edges[i];
        bool edge_is_abbrev = is_edge_abbrev(edge);

        if (edge_is_abbrev == current.is_abbrev) {
            current.text += edge.text;
            current.tokens.push_back(edge.text);
        } else {
            chunks.push_back(std::move(current));
            current.is_abbrev = edge_is_abbrev;
            current.text = edge.text;
            current.tokens = { edge.text };
        }
    }
    chunks.push_back(std::move(current));
    return chunks;
}

std::vector<SegmentPath> SyllableLattice::search_top_k(
    std::string_view input,
    const std::unordered_set<std::string>& valid_syllables,
    const std::unordered_set<std::string>& valid_prefixes,
    const std::vector<std::string>& sorted_syllables,
    size_t k
) const {
    if (input.empty()) return {};

    (void)sorted_syllables;
    size_t n = input.size();

    // 1. 构建邻接表
    std::vector<std::vector<LatticeEdge>> adj(n + 1);

    for (size_t i = 0; i < n; ++i) {
        if (input[i] == '\'') continue; // 隔音符跳过

        // A. 匹配全拼音节 (长度 1 到 6)
        for (size_t l = 1; l <= 6 && i + l <= n; ++l) {
            std::string_view sub = input.substr(i, l);
            if (sub.find('\'') != std::string_view::npos) break;

            std::string sub_str(sub);
            if (valid_syllables.find(sub_str) != valid_syllables.end()) {
                adj[i].push_back(LatticeEdge{
                    i, i + l, sub_str, EdgeType::EXACT_SYLLABLE, 0.0
                });
            }
        }

        // B. 匹配声母简拼 (双字母声母 zh, ch, sh 或单字母辅音)
        if (i + 2 <= n) {
            std::string_view pair = input.substr(i, 2);
            if (pair == "zh" || pair == "ch" || pair == "sh") {
                adj[i].push_back(LatticeEdge{
                    i, i + 2, std::string(pair), EdgeType::ABBREV_INITIAL, 0.9
                });
            }
        }
        if (is_single_initial(input[i])) {
            adj[i].push_back(LatticeEdge{
                i, i + 1, std::string(1, input[i]), EdgeType::ABBREV_INITIAL, 1.0
            });
        }

        // C. 末尾未闭合前缀检测 (必须延伸至字符串末尾 n)
        if (i < n) {
            std::string_view tail = input.substr(i);
            if (tail.find('\'') == std::string_view::npos) {
                std::string tail_str(tail);
                if (valid_prefixes.find(tail_str) != valid_prefixes.end() &&
                    valid_syllables.find(tail_str) == valid_syllables.end()) {
                    adj[i].push_back(LatticeEdge{
                        i, n, tail_str, EdgeType::INCOMPLETE_PREFIX, 0.5
                    });
                }
            }
        }

        // D. 物理键盘空间邻键与手误容错 (Typo Correction: 邻键/漏g/倒装/消抖)
        for (size_t l = 2; l <= 6 && i + l <= n; ++l) {
            std::string_view sub = input.substr(i, l);
            if (sub.find('\'') != std::string_view::npos) break;
            auto corrections = KeyboardModel::generate_corrections(sub, valid_syllables);
            for (const auto& corr : corrections) {
                adj[i].push_back(LatticeEdge{
                    i, i + l, corr.corrected, EdgeType::FUZZY_SYLLABLE, corr.cost
                });
            }
        }
    }

    // 2. Viterbi / DP 求解 Top-K 路径
    struct PathState {
        std::vector<LatticeEdge> edges;
        double cost = 0.0;
    };

    std::vector<std::vector<PathState>> dp(n + 1);
    dp[0].push_back({ {}, 0.0 });

    for (size_t i = 0; i < n; ++i) {
        if (dp[i].empty()) continue;

        // 如果当前字符是隔音符，允许直接无缝跳过到 i+1
        if (input[i] == '\'') {
            for (const auto& path : dp[i]) {
                dp[i + 1].push_back(path);
            }
        }

        for (const auto& path : dp[i]) {
            for (const auto& edge : adj[i]) {
                size_t next_pos = edge.to;
                double next_cost = path.cost + edge.cost;

                auto next_edges = path.edges;
                next_edges.push_back(edge);

                dp[next_pos].push_back(PathState{ std::move(next_edges), next_cost });
            }
        }

        // 剪枝：每个节点只保留代价最小的前 12 条路径
        if (dp[i + 1].size() > 12) {
            std::sort(dp[i + 1].begin(), dp[i + 1].end(), [](const PathState& a, const PathState& b) {
                if (std::abs(a.cost - b.cost) > 1e-4) return a.cost < b.cost;
                size_t fa = 0, fb = 0;
                for (const auto& e : a.edges) if (e.type == EdgeType::FUZZY_SYLLABLE) ++fa;
                for (const auto& e : b.edges) if (e.type == EdgeType::FUZZY_SYLLABLE) ++fb;
                if (fa != fb) return fa < fb;
                return a.edges.size() < b.edges.size();
            });
            dp[i + 1].resize(12);
        }
    }

    // 3. 兜底回退：如果无法完整到达 n，寻找最长能到达的节点
    size_t final_node = n;
    if (dp[n].empty()) {
        for (int p = static_cast<int>(n) - 1; p >= 0; --p) {
            if (!dp[p].empty()) {
                final_node = static_cast<size_t>(p);
                break;
            }
        }
    }

    if (dp[final_node].empty()) return {};

    // 4. 按总代价升序排序（同等代价下优先非纠错边、再优先更少切分边数）
    std::sort(dp[final_node].begin(), dp[final_node].end(), [](const PathState& a, const PathState& b) {
        if (std::abs(a.cost - b.cost) > 1e-4) return a.cost < b.cost;
        size_t fa = 0, fb = 0;
        for (const auto& e : a.edges) if (e.type == EdgeType::FUZZY_SYLLABLE) ++fa;
        for (const auto& e : b.edges) if (e.type == EdgeType::FUZZY_SYLLABLE) ++fb;
        if (fa != fb) return fa < fb;
        return a.edges.size() < b.edges.size();
    });

    std::vector<SegmentPath> results;
    std::unordered_set<std::string> seen_signatures;

    for (const auto& state : dp[final_node]) {
        // 生成签名以过滤重复切分结构
        std::string sig;
        for (const auto& edge : state.edges) {
            sig += (is_edge_abbrev(edge) ? "A:" : "F:") + edge.text + "|";
        }

        if (seen_signatures.insert(sig).second) {
            auto chunks = edges_to_chunks(state.edges);
            results.push_back(SegmentPath{
                state.edges,
                std::move(chunks),
                state.cost
            });
            if (results.size() >= k) break;
        }
    }

    return results;
}

} // namespace yanmo
