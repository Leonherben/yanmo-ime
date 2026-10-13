#include "yanmo/engine.h"
#include <iostream>
#include <cassert>
#include <chrono>

using namespace yanmo;

void test_initialization(YanMoEngine& engine) {
    std::cout << "[Test 1] Initialization & TSV loading... ";
    bool ok = engine.init("data/dict/core_lexicon.tsv", "data/radicals/radicals.tsv");
    if (!ok) {
        ok = engine.init("../data/dict/core_lexicon.tsv", "../data/radicals/radicals.tsv");
    }
    if (!ok) {
        ok = engine.init("../../data/dict/core_lexicon.tsv", "../../data/radicals/radicals.tsv");
    }
    assert(ok && "Failed to load TSV files");
    std::cout << "PASSED\n";
}

void test_basic_typing(YanMoEngine& engine) {
    std::cout << "[Test 2] Basic Pinyin composing... ";
    engine.reset();
    for (char c : std::string("nihao")) engine.feed_key(std::string(1, c), false);

    assert(engine.get_status().mode == InputMode::COMPOSING);
    assert(!engine.get_current_candidates().empty());
    assert(engine.get_current_candidates()[0].word == "你好");

    std::string committed = engine.commit_candidate(0);
    assert(committed == "你好");
    assert(engine.get_status().mode == InputMode::IDLE);
    std::cout << "PASSED (Got: " << committed << ")\n";
}

void test_matrix_navigation(YanMoEngine& engine) {
    std::cout << "[Test 3] Matrix navigation (ArrowDown & 1-5)... ";
    engine.reset();
    for (char c : std::string("he")) engine.feed_key(std::string(1, c), false);

    assert(engine.get_status().total_candidates >= 10);
    // Press ArrowDown
    engine.feed_key("ArrowDown", false);
    assert(engine.get_status().is_expanded);
    assert(engine.get_status().active_row == 1);

    // Pick 2nd word from row 1
    auto row1 = engine.get_row_candidates(1);
    std::string expected = row1[1].word;
    std::string committed = engine.commit_candidate(1);
    assert(committed == expected);
    std::cout << "PASSED (Row 1 Col 2 -> " << committed << ")\n";
}

void test_radical_filtering(YanMoEngine& engine) {
    std::cout << "[Test 4] Tab radical filtering... ";
    engine.reset();
    for (char c : std::string("he")) engine.feed_key(std::string(1, c), false);

    engine.feed_key("Tab", false);
    assert(engine.get_status().mode == InputMode::RADICAL);

    for (char c : std::string("kou")) engine.feed_key(std::string(1, c), false);
    assert(engine.get_status().radical_buffer == "kou");
    assert(!engine.get_current_candidates().empty());

    for (const auto& cand : engine.get_current_candidates()) {
        assert(cand.radical == "口");
    }
    std::string committed = engine.commit_candidate(0);
    std::cout << "PASSED (Filtered: " << committed << ")\n";
}

void test_punctuation_commit(YanMoEngine& engine) {
    std::cout << "[Test 5] Punctuation direct commit... ";
    engine.reset();
    for (char c : std::string("nihao")) engine.feed_key(std::string(1, c), false);

    std::string committed = engine.commit_top("，");
    assert(committed == "你好，");
    assert(engine.get_status().mode == InputMode::IDLE);
    std::cout << "PASSED (" << committed << ")\n";
}

void test_benchmark(YanMoEngine& engine) {
    std::cout << "[Test 6] Benchmark (1,000 typing sequences = 5,000 queries)... ";
    auto start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < 1000; ++i) {
        engine.reset();
        engine.feed_key("n", false);
        engine.feed_key("i", false);
        engine.feed_key("h", false);
        engine.feed_key("a", false);
        engine.feed_key("o", false);
    }
    auto end = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(end - start).count();
    double per_key = ms / 5000.0;
    std::cout << "5,000 queries in " << ms << " ms (" << per_key << " ms/keystroke)\n";
    assert(per_key < 2.0 && "Performance regression: average keystroke latency exceeds 2.0 ms threshold!");
}

void test_prefix_composition(YanMoEngine& engine) {
    std::cout << "[Test 7] Prefix sentence composition... ";
    engine.reset();
    for (char c : std::string("zenmeshuon")) engine.feed_key(std::string(1, c), false);
    auto cands = engine.get_row_candidates(0);
    for (size_t i = 0; i < cands.size(); ++i) {
        std::cout << "\n  Cand " << i << ": " << cands[i].word;
    }
    std::cout << "\n";
}

void test_delimiter_and_typo(YanMoEngine& engine) {
    std::cout << "[Test 8] Delimiter (') and Typo correction in Engine... ";
    
    // 1. 显式隔音符: xi'an
    engine.reset();
    for (char c : std::string("xi'an")) engine.feed_key(std::string(1, c), false);
    auto cands = engine.get_current_candidates();
    assert(!cands.empty());
    bool found_xian = false;
    for (size_t i = 0; i < std::min<size_t>(5, cands.size()); ++i) {
        if (cands[i].word == "西安") { found_xian = true; break; }
    }
    assert(found_xian && "Failed to find '西安' with delimiter input xi'an");

    // 2. 搜狗式倒装手误: zhaogn -> zhang
    engine.reset();
    for (char c : std::string("zhaogn")) engine.feed_key(std::string(1, c), false);
    auto typo_cands = engine.get_current_candidates();
    assert(!typo_cands.empty());
    bool found_zhang = false;
    for (size_t i = 0; i < std::min<size_t>(5, typo_cands.size()); ++i) {
        if (typo_cands[i].word == "张" || typo_cands[i].word == "长") { found_zhang = true; break; }
    }
    assert(found_zhang && "Failed to find candidate for typo zhaogn");

    std::cout << "PASSED\n";
}

void test_fuzzy_toggle(YanMoEngine& engine) {
    std::cout << "[Test 9] Fuzzy pinyin toggle in Engine... ";
    SpellingConfig cfg;
    cfg.fuzzy_zh_z = true;
    engine.set_spelling_config(cfg);

    engine.reset();
    // 输入 "zong"，开启 fuzzy_zh_z 后，"中" (zhong) 应被派生检索出
    for (char c : std::string("zong")) engine.feed_key(std::string(1, c), false);
    auto cands = engine.get_current_candidates();
    bool found_zhong = false;
    for (const auto& c : cands) {
        if (c.word == "中") { found_zhong = true; break; }
    }
    assert(found_zhong && "Failed to find '中' when fuzzy_zh_z is enabled");

    // 还原默认配置
    engine.set_spelling_config(SpellingConfig{});
    std::cout << "PASSED\n";
}

void test_bigram_engine(YanMoEngine& engine) {
    std::cout << "[Test 10] Bigram collocation sentence in Engine... ";
    engine.reset();
    for (char c : std::string("jintiantianqi")) engine.feed_key(std::string(1, c), false);
    auto cands = engine.get_current_candidates();
    assert(!cands.empty());
    assert(cands[0].word == "今天天气");
    std::cout << "PASSED (Got: " << cands[0].word << ")\n";
}

void test_adaptive_user_learning(YanMoEngine& engine) {
    std::cout << "[Test 11] Adaptive user learning & frequency boosting... ";
    engine.reset();
    for (char c : std::string("bai")) engine.feed_key(std::string(1, c), false);

    auto cands = engine.get_current_candidates();
    assert(cands.size() >= 5);

    size_t target_idx = 0;
    for (size_t i = 0; i < cands.size(); ++i) {
        if (cands[i].word == "柏") { target_idx = i; break; }
    }
    assert(target_idx > 0 && "'柏' should not be top candidate initially");

    // 用户通过翻页导航定位并提交 "柏"
    size_t row = target_idx / 5;
    size_t col = target_idx % 5;
    for (size_t r = 0; r < row; ++r) {
        engine.feed_key("ArrowDown", false);
    }
    std::string committed = engine.commit_candidate(col);
    assert(committed == "柏");

    // 再次键入 "bai"：由于动态学习自增加权，"柏" 自动跃升为首选候选字 (candidate 0)
    engine.reset();
    for (char c : std::string("bai")) engine.feed_key(std::string(1, c), false);
    auto cands_after = engine.get_current_candidates();
    assert(cands_after[0].word == "柏" && "Failed to boost '柏' to top candidate");

    std::cout << "PASSED ('柏' boosted from idx " << target_idx << " to top)\n";
}

void test_smart_punctuation(YanMoEngine& engine) {
    std::cout << "[Test 12] Smart punctuation auto-pairing... ";
    engine.reset();
    for (char c : std::string("nihao")) engine.feed_key(std::string(1, c), false);

    // 输入引号: 第一次自动映射为左引号 “ 并提交
    engine.feed_key("\"", false);
    std::string text1 = engine.get_status().committed_text;
    assert(text1 == "你好“");

    // 输入下一个词与引号: 第二次自动轮转为右引号 ” 并提交
    for (char c : std::string("shijie")) engine.feed_key(std::string(1, c), false);
    engine.feed_key("\"", false);
    std::string text2 = engine.get_status().committed_text;
    assert(text2 == "世界”");

    std::cout << "PASSED (Quotes paired: " << text1 << " ... " << text2 << ")\n";
}

void test_hybrid_pinyin_input(YanMoEngine& engine) {
    std::cout << "[Test 13] Hybrid Pinyin input & Prefix fallback (shuosmn -> 说什么呢)... ";
    engine.reset();
    for (char c : std::string("shuosmn")) engine.feed_key(std::string(1, c), false);
    auto cands = engine.get_current_candidates();
    assert(!cands.empty() && "Candidate list must not be empty for shuosmn!");
    assert(cands[0].word == "说什么呢" && "Top candidate for shuosmn should be '说什么呢'!");

    // Also test prefix fallback for nonsense continuation: shuosmnxyz
    engine.reset();
    for (char c : std::string("shuosmnxyz")) engine.feed_key(std::string(1, c), false);
    auto fb_cands = engine.get_current_candidates();
    assert(!fb_cands.empty() && "Candidate list must not be empty even for unknown suffix!");
    bool found_shuo = false;
    for (const auto& c : fb_cands) {
        if (c.word == "说" || c.word == "说话" || c.word == "说明") { found_shuo = true; break; }
    }
    assert(found_shuo && "Should fall back to prefix 'shuo' candidates!");
    std::cout << "PASSED (Top: " << cands[0].word << ", Fallback count: " << fb_cands.size() << ")\n";
}

void test_any_position_hybrid(YanMoEngine& engine) {
    std::cout << "[Test 14] Any-position hybrid (zgguoji -> 中国国际, nshuosm -> 你说什么)... ";

    // 1. 简 + 全: zgguoji -> 中国国际
    engine.reset();
    for (char c : std::string("zgguoji")) engine.feed_key(std::string(1, c), false);
    auto cands1 = engine.get_current_candidates();
    assert(!cands1.empty());
    bool found_zg_guoji = false;
    for (size_t i = 0; i < std::min<size_t>(3, cands1.size()); ++i) {
        if (cands1[i].word == "中国国际") { found_zg_guoji = true; break; }
    }
    assert(found_zg_guoji && "Top candidate for zgguoji should be '中国国际'!");

    // 2. 简 + 全 + 简: nshuosm -> 你说什么
    engine.reset();
    for (char c : std::string("nshuosm")) engine.feed_key(std::string(1, c), false);
    auto cands2 = engine.get_current_candidates();
    assert(!cands2.empty());
    bool found_nshuosm = false;
    for (size_t i = 0; i < std::min<size_t>(3, cands2.size()); ++i) {
        if (cands2[i].word == "你说什么") { found_nshuosm = true; break; }
    }
    assert(found_nshuosm && "Top candidate for nshuosm should be '你说什么'!");

    std::cout << "PASSED (" << cands1[0].word << ", " << cands2[0].word << ")\n";
}

void test_keyboard_typo_engine(YanMoEngine& engine) {
    std::cout << "[Test 15] Keyboard spatial & typo correction (tain -> 天, nnihao -> 你好)... ";

    // 1. 相邻字母倒装: tain -> 天 / 填
    engine.reset();
    for (char c : std::string("tain")) engine.feed_key(std::string(1, c), false);
    auto cands1 = engine.get_current_candidates();
    assert(!cands1.empty());
    bool found_tian = false;
    for (size_t i = 0; i < std::min<size_t>(5, cands1.size()); ++i) {
        if (cands1[i].word == "天" || cands1[i].word == "田" || cands1[i].word == "填") {
            found_tian = true;
            break;
        }
    }
    assert(found_tian && "Candidate list for 'tain' should contain '天'/'田'/'填' via typo correction");

    // 2. 连击去重消抖: nnihao -> 你好
    engine.reset();
    for (char c : std::string("nnihao")) engine.feed_key(std::string(1, c), false);
    auto cands2 = engine.get_current_candidates();
    assert(!cands2.empty());
    bool found_nihao = false;
    for (size_t i = 0; i < std::min<size_t>(5, cands2.size()); ++i) {
        if (cands2[i].word == "你好") {
            found_nihao = true;
            break;
        }
    }
    assert(found_nihao && "Candidate list for 'nnihao' should contain '你好' via stutter deduplication");

    std::cout << "PASSED (" << cands1[0].word << ", " << cands2[0].word << ")\n";
}

void test_p0_regressions(YanMoEngine& engine) {
    std::cout << "[Test 16] P0 Bug Regressions (UTF-8 backspace, bounds commit, direct radical)... ";

    // P0-4: UTF-8 character boundary pop
    engine.reset();
    engine.feed_key("Tab", false);
    engine.set_radical_glyph("氵");
    assert(engine.get_status().radical_buffer == "氵");
    engine.feed_key("Backspace", false);
    assert(engine.get_status().radical_buffer.empty());

    // P0-6: Digit selection beyond row candidates does not commit raw pinyin
    engine.reset();
    for (char c : std::string("bangmang")) engine.feed_key(std::string(1, c), false);
    auto row_cands = engine.get_row_candidates(0);
    assert(row_cands.size() < 5);
    bool consumed = engine.feed_key("5", false);
    assert(!consumed);
    assert(engine.get_status().committed_text.empty());
    assert(engine.get_status().pinyin_buffer == "bangmang");

    // P0-7: Direct radical mode setting from IDLE
    engine.reset();
    assert(engine.get_status().mode == InputMode::IDLE);
    engine.set_radical_glyph("氵");
    assert(engine.get_status().mode == InputMode::RADICAL);
    assert(engine.get_status().radical_buffer == "氵");
    assert(!engine.get_current_candidates().empty());
    std::unordered_set<std::string> seen_radical_words;
    for (const auto& c : engine.get_current_candidates()) {
        assert(c.radical == "氵");
        assert(seen_radical_words.insert(c.word).second && "Duplicate candidate found in radical candidates!");
    }

    std::cout << "PASSED\n";
}

void test_keystroke_p99_regression(YanMoEngine& engine) {
    std::cout << "[Test 17] Keystroke Latency P99 Regression Test (womenzaiyanmo)... ";
    std::vector<double> latencies;
    latencies.reserve(1300);
    const std::string text = "womenzaiyanmo";
    for (int iter = 0; iter < 100; ++iter) {
        engine.reset();
        for (char c : text) {
            auto t0 = std::chrono::high_resolution_clock::now();
            engine.feed_key(std::string(1, c), false);
            auto t1 = std::chrono::high_resolution_clock::now();
            latencies.push_back(std::chrono::duration<double, std::milli>(t1 - t0).count());
        }
    }
    std::sort(latencies.begin(), latencies.end());
    double median = latencies[latencies.size() / 2];
    double p99 = latencies[static_cast<size_t>(latencies.size() * 0.99)];
    double max_lat = latencies.back();
    std::cout << "(Median: " << median << " ms, P99: " << p99 << " ms, Max: " << max_lat << " ms)... PASSED\n";
    assert(median < 1.0 && "Performance regression: median latency exceeds 1.0 ms threshold!");
    assert(p99 < 5.0 && "Performance regression: P99 latency exceeds 5.0 ms threshold!");
    assert(max_lat < 15.0 && "Performance regression: single-key spike exceeds 15.0 ms threshold!");
}

int main() {
    std::cout << "=== YanMo IME C++20 Core Unit Tests ===\n";
    YanMoEngine engine;
    test_initialization(engine);
    test_basic_typing(engine);
    test_matrix_navigation(engine);
    test_radical_filtering(engine);
    test_punctuation_commit(engine);
    test_benchmark(engine);
    test_prefix_composition(engine);
    test_delimiter_and_typo(engine);
    test_fuzzy_toggle(engine);
    test_bigram_engine(engine);
    test_adaptive_user_learning(engine);
    test_smart_punctuation(engine);
    test_hybrid_pinyin_input(engine);
    test_any_position_hybrid(engine);
    test_keyboard_typo_engine(engine);
    test_p0_regressions(engine);
    test_keystroke_p99_regression(engine);
    std::cout << "=== ALL TESTS COMPLETED SUCCESSFULLY ===\n";
    return 0;
}
