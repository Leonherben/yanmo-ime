#include "yanmo/keyboard_model.h"
#include <algorithm>

namespace yanmo {

static const std::vector<char> EMPTY_VEC;

// QWERTY 键盘 2D 物理拓扑邻接表
static const std::vector<char> ADJ_A = {'q', 'w', 's', 'z'};
static const std::vector<char> ADJ_B = {'v', 'g', 'h', 'n'};
static const std::vector<char> ADJ_C = {'x', 'd', 'f', 'v'};
static const std::vector<char> ADJ_D = {'s', 'e', 'r', 'f', 'c', 'x'};
static const std::vector<char> ADJ_E = {'w', 's', 'd', 'r'};
static const std::vector<char> ADJ_F = {'d', 'r', 't', 'g', 'v', 'c'};
static const std::vector<char> ADJ_G = {'f', 't', 'y', 'h', 'b', 'v'};
static const std::vector<char> ADJ_H = {'g', 'y', 'u', 'j', 'n', 'b'};
static const std::vector<char> ADJ_I = {'u', 'j', 'k', 'o'};
static const std::vector<char> ADJ_J = {'h', 'u', 'i', 'k', 'm', 'n'};
static const std::vector<char> ADJ_K = {'j', 'i', 'o', 'l', 'm'};
static const std::vector<char> ADJ_L = {'k', 'o', 'p'};
static const std::vector<char> ADJ_M = {'n', 'j', 'k'};
static const std::vector<char> ADJ_N = {'b', 'h', 'j', 'm'};
static const std::vector<char> ADJ_O = {'i', 'k', 'l', 'p'};
static const std::vector<char> ADJ_P = {'o', 'l'};
static const std::vector<char> ADJ_Q = {'w', 'a'};
static const std::vector<char> ADJ_R = {'e', 'd', 'f', 't'};
static const std::vector<char> ADJ_S = {'a', 'w', 'e', 'd', 'x', 'z'};
static const std::vector<char> ADJ_T = {'r', 'f', 'g', 'y'};
static const std::vector<char> ADJ_U = {'y', 'h', 'j', 'i'};
static const std::vector<char> ADJ_V = {'c', 'f', 'g', 'b'};
static const std::vector<char> ADJ_W = {'q', 'a', 's', 'e'};
static const std::vector<char> ADJ_X = {'z', 's', 'd', 'c'};
static const std::vector<char> ADJ_Y = {'t', 'g', 'h', 'u'};
static const std::vector<char> ADJ_Z = {'a', 's', 'x'};

const std::vector<char>& KeyboardModel::get_adjacent_keys(char c) {
    if (c >= 'A' && c <= 'Z') c = static_cast<char>(c + 32);
    switch (c) {
        case 'a': return ADJ_A;
        case 'b': return ADJ_B;
        case 'c': return ADJ_C;
        case 'd': return ADJ_D;
        case 'e': return ADJ_E;
        case 'f': return ADJ_F;
        case 'g': return ADJ_G;
        case 'h': return ADJ_H;
        case 'i': return ADJ_I;
        case 'j': return ADJ_J;
        case 'k': return ADJ_K;
        case 'l': return ADJ_L;
        case 'm': return ADJ_M;
        case 'n': return ADJ_N;
        case 'o': return ADJ_O;
        case 'p': return ADJ_P;
        case 'q': return ADJ_Q;
        case 'r': return ADJ_R;
        case 's': return ADJ_S;
        case 't': return ADJ_T;
        case 'u': return ADJ_U;
        case 'v': return ADJ_V;
        case 'w': return ADJ_W;
        case 'x': return ADJ_X;
        case 'y': return ADJ_Y;
        case 'z': return ADJ_Z;
        default: return EMPTY_VEC;
    }
}

bool KeyboardModel::is_adjacent(char a, char b) {
    const auto& adjs = get_adjacent_keys(a);
    return std::find(adjs.begin(), adjs.end(), b) != adjs.end();
}

std::vector<TypoVariant> KeyboardModel::generate_corrections(
    std::string_view token,
    const std::unordered_set<std::string>& valid_syllables
) {
    if (token.empty() || token.size() > 7) return {};

    std::vector<TypoVariant> results;
    std::unordered_set<std::string> seen;

    auto try_add = [&](const std::string& cand, double cost) {
        if (cand != token && valid_syllables.find(cand) != valid_syllables.end()) {
            if (seen.insert(cand).second) {
                results.push_back({ cand, cost });
            }
        }
    };

    // 1. 韵尾 g 漏打容错 (zhan -> zhang, pen -> peng, min -> ming, son -> song)
    if (token.size() >= 2) {
        std::string with_g = std::string(token) + "g";
        try_add(with_g, 1.8);
    }

    // 2. 连续字母连击去重消抖 (nni -> ni, shuu -> shu, hhao -> hao)
    for (size_t i = 0; i + 1 < token.size(); ++i) {
        if (token[i] == token[i + 1]) {
            std::string dedup_str = std::string(token.substr(0, i)) + std::string(token.substr(i + 1));
            try_add(dedup_str, 1.6);
        }
    }

    // 3. 相邻字母倒装纠错 (tain -> tian, zhaogn -> zhang 等)
    for (size_t i = 0; i + 1 < token.size(); ++i) {
        std::string swapped(token);
        std::swap(swapped[i], swapped[i + 1]);
        try_add(swapped, 1.8);
    }

    // 4. 单字符邻键替换 (例如打偏隔壁键: sji -> shi)
    for (size_t i = 0; i < token.size(); ++i) {
        char orig = token[i];
        for (char adj : get_adjacent_keys(orig)) {
            std::string modded(token);
            modded[i] = adj;
            try_add(modded, 2.2);
        }
    }

    return results;
}

} // namespace yanmo
