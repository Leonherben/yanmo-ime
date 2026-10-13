#include "yanmo/speller.h"
#include <iostream>
#include <cassert>
#include <chrono>

using namespace yanmo;

void test_normalization_and_typo(Speller& speller) {
    std::cout << "[Test 1] Normalization & Typo correction... ";

    // Orthography
    assert(speller.normalize("LUE") == "lve");
    assert(speller.normalize("nue") == "nve");
    assert(speller.normalize("jv") == "ju");
    assert(speller.normalize("qv") == "qu");
    assert(speller.normalize("xv") == "xu");

    // Typo: gn -> ng
    assert(speller.normalize("zhaogn") == "zhang");
    assert(speller.normalize("chaogn") == "chang");
    assert(speller.normalize("dign") == "ding");
    assert(speller.normalize("shuen") == "shun");
    assert(speller.normalize("liou") == "liu");

    std::cout << "PASSED\n";
}

void test_delimiters(Speller& speller) {
    std::cout << "[Test 2] Delimiters (')... ";

    auto parse = speller.parse("xi'an");
    assert(parse.primary_syllables.size() == 2);
    assert(parse.primary_syllables[0] == "xi");
    assert(parse.primary_syllables[1] == "an");
    assert(parse.trailing_incomplete.empty());

    auto parse2 = speller.parse("fang'an");
    assert(parse2.primary_syllables.size() == 2);
    assert(parse2.primary_syllables[0] == "fang");
    assert(parse2.primary_syllables[1] == "an");

    std::cout << "PASSED\n";
}

void test_ambiguous_and_alternatives(Speller& speller) {
    std::cout << "[Test 3] Ambiguous segmentation & alternatives... ";

    auto parse = speller.parse("xian");
    // "xian" is a single valid syllable, primary should be ["xian"]
    assert(parse.primary_syllables.size() == 1);
    assert(parse.primary_syllables[0] == "xian");

    // But it should offer alternative ["xi", "an"]
    bool found_alt = false;
    for (const auto& alt : parse.alt_segmentations) {
        if (alt.size() == 2 && alt[0] == "xi" && alt[1] == "an") {
            found_alt = true;
            break;
        }
    }
    assert(found_alt && "Failed to find alternative segmentation for 'xian'");

    std::cout << "PASSED\n";
}

void test_incomplete_trailing(Speller& speller) {
    std::cout << "[Test 4] Incomplete trailing prefix... ";

    auto parse = speller.parse("nih");
    assert(parse.primary_syllables.size() == 1);
    assert(parse.primary_syllables[0] == "ni");
    assert(parse.trailing_incomplete == "h");

    auto parse2 = speller.parse("zenmeshuon");
    assert(parse2.primary_syllables.size() == 3);
    assert(parse2.primary_syllables[0] == "zen");
    assert(parse2.primary_syllables[1] == "me");
    assert(parse2.primary_syllables[2] == "shuo");
    assert(parse2.trailing_incomplete == "n");

    std::cout << "PASSED (ni + h, zenmeshuo + n)\n";
}

void test_abbreviations(Speller& speller) {
    std::cout << "[Test 5] Abbreviation & Initials... ";

    auto parse1 = speller.parse("zg");
    assert(parse1.is_abbreviation);
    assert(parse1.initials.size() == 2);
    assert(parse1.initials[0] == "z" && parse1.initials[1] == "g");

    auto parse2 = speller.parse("shz");
    assert(parse2.is_abbreviation);
    assert(parse2.initials.size() == 2);
    assert(parse2.initials[0] == "sh" && parse2.initials[1] == "z");

    std::cout << "PASSED\n";
}

void test_fuzzy_matrix() {
    std::cout << "[Test 6] Fuzzy matrix variations... ";

    SpellingConfig cfg;
    cfg.fuzzy_zh_z = true;
    cfg.fuzzy_an_ang = true;
    cfg.fuzzy_l_n = true;
    Speller speller(cfg);

    auto parse_zh = speller.parse("zhong");
    // With fuzzy_zh_z, "zhong" can derive "zong"
    bool found_zong = false;
    for (const auto& var : parse_zh.fuzzy_variations) {
        if (!var.empty() && var[0] == "zong") {
            found_zong = true;
            break;
        }
    }
    assert(found_zong && "Failed to derive 'zong' from 'zhong'");

    auto parse_an = speller.parse("tian");
    // With fuzzy_an_ang, "tian" can derive "tiang" (if valid) or "an" <-> "ang"
    auto parse_san = speller.parse("san");
    bool found_sang = false;
    for (const auto& var : parse_san.fuzzy_variations) {
        if (!var.empty() && var[0] == "sang") {
            found_sang = true;
            break;
        }
    }
    assert(found_sang && "Failed to derive 'sang' from 'san'");

    std::cout << "PASSED\n";
}

void test_benchmark(Speller& speller) {
    std::cout << "[Test 7] Performance Benchmark (10,000 parses)... ";

    std::vector<std::string> inputs = {
        "nihao", "xian", "xi'an", "zhaogn", "shanghai", "beijing", "zhongguo", "wzx", "dign"
    };

    auto start = std::chrono::high_resolution_clock::now();
    size_t count = 10000;
    for (size_t i = 0; i < count; ++i) {
        const auto& in = inputs[i % inputs.size()];
        auto res = speller.parse(in);
        (void)res;
    }
    auto end = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(end - start).count();
    double per_parse_us = (ms * 1000.0) / count;

    std::cout << count << " parses in " << ms << " ms (" << per_parse_us << " us/parse)\n";
    assert(per_parse_us < 1000.0 && "Speller parse exceeds 1ms safety threshold!");
}

void test_hybrid_segmentation(Speller& speller) {
    std::cout << "[Test 7] Hybrid segmentation (shuosmn -> shuo + smn)... ";
    auto parse = speller.parse("shuosmn");
    assert(parse.primary_syllables.size() == 1);
    assert(parse.primary_syllables[0] == "shuo");
    assert(parse.trailing_incomplete == "smn");

    auto parse2 = speller.parse("womends");
    assert(parse2.primary_syllables.size() == 2);
    assert(parse2.primary_syllables[0] == "wo");
    assert(parse2.primary_syllables[1] == "men");
    assert(parse2.trailing_incomplete == "ds");
    std::cout << "PASSED\n";
}

void test_mang_syllable(Speller& speller) {
    std::cout << "[Test 8] Syllable table completeness & mang coverage... ";
    const auto& syls = speller.get_all_syllables();
    assert(syls.size() == 410);
    std::unordered_set<std::string> unique_syls(syls.begin(), syls.end());
    assert(unique_syls.size() == 410);
    assert(speller.is_valid_syllable("mang"));
    assert(speller.is_valid_syllable("bang"));

    auto seg_mang = speller.segment_simple("mang");
    assert(seg_mang.size() == 1 && seg_mang[0] == "mang");

    auto seg_manglu = speller.segment_simple("manglu");
    assert(seg_manglu.size() == 2 && seg_manglu[0] == "mang" && seg_manglu[1] == "lu");

    auto seg_bangmang = speller.segment_simple("bangmang");
    assert(seg_bangmang.size() == 2 && seg_bangmang[0] == "bang" && seg_bangmang[1] == "mang");

    auto seg_mangzhe = speller.segment_simple("mangzhe");
    assert(seg_mangzhe.size() == 2 && seg_mangzhe[0] == "mang" && seg_mangzhe[1] == "zhe");

    auto seg_womang = speller.segment_simple("womang");
    assert(seg_womang.size() == 2 && seg_womang[0] == "wo" && seg_womang[1] == "mang");

    std::cout << "PASSED\n";
}

void test_short_and_boundary_inputs(Speller& speller) {
    std::cout << "[Test 9] Short and boundary inputs without bounds overflow... ";
    std::vector<std::string> edge_cases = {"gn", "ng", "n", "g", "", "a", "agn", "bgn", "zhaogn"};
    for (const auto& s : edge_cases) {
        std::string norm = speller.normalize(s);
        (void)norm;
        auto parse = speller.parse(s);
        (void)parse;
    }
    assert(speller.normalize("gn") == "gn");
    assert(speller.normalize("agn") == "ang");
    std::cout << "PASSED\n";
}

int main() {
    std::cout << "=== YanMo IME Speller Unit Tests ===\n";
    Speller speller;
    test_normalization_and_typo(speller);
    test_delimiters(speller);
    test_ambiguous_and_alternatives(speller);
    test_incomplete_trailing(speller);
    test_abbreviations(speller);
    test_hybrid_segmentation(speller);
    test_fuzzy_matrix();
    test_mang_syllable(speller);
    test_short_and_boundary_inputs(speller);
    test_benchmark(speller);
    std::cout << "=== ALL SPELLER TESTS COMPLETED SUCCESSFULLY ===\n";
    return 0;
}

