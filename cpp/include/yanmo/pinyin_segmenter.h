#pragma once

#include "types.h"
#include "speller.h"
#include <string>
#include <string_view>
#include <vector>

namespace yanmo {

// 兼容旧接口的轻量切分包装器，底层委托给 Speller
class PinyinSegmenter {
public:
    PinyinSegmenter();
    ~PinyinSegmenter() = default;

    std::vector<std::string> segment(std::string_view text) const;
    std::vector<std::string> segment_with_prefix(std::string_view text, std::string& out_tail) const;
    const std::vector<std::string>& get_syllables() const;

private:
    Speller speller_;
};

} // namespace yanmo
