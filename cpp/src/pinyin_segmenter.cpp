#include "yanmo/pinyin_segmenter.h"

namespace yanmo {

PinyinSegmenter::PinyinSegmenter() = default;

std::vector<std::string> PinyinSegmenter::segment(std::string_view text) const {
    auto parse = speller_.parse(text);
    if (parse.trailing_incomplete.empty()) {
        return parse.primary_syllables;
    }
    return {};
}

std::vector<std::string> PinyinSegmenter::segment_with_prefix(std::string_view text, std::string& out_tail) const {
    auto parse = speller_.parse(text);
    out_tail = parse.trailing_incomplete;
    return parse.primary_syllables;
}

const std::vector<std::string>& PinyinSegmenter::get_syllables() const {
    return speller_.get_all_syllables();
}

} // namespace yanmo
