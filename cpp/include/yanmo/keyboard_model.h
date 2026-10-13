#pragma once

#include <string>
#include <string_view>
#include <vector>
#include <unordered_set>

namespace yanmo {

struct TypoVariant {
    std::string corrected;
    double cost = 2.0;
};

class KeyboardModel {
public:
    KeyboardModel() = default;

    // 获取某个字符在 QWERTY 键盘上的物理邻接按键
    static const std::vector<char>& get_adjacent_keys(char c);

    // 判断两个按键是否为键盘上的空间邻键
    static bool is_adjacent(char a, char b);

    // 对音节生成符合人体工学的智能容错变体 (漏末尾g、字母倒装、重复消抖、邻键误触)
    static std::vector<TypoVariant> generate_corrections(
        std::string_view token,
        const std::unordered_set<std::string>& valid_syllables
    );
};

} // namespace yanmo
