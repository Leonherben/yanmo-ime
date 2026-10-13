#include "yanmo/lattice.h"
#include <iostream>
#include <cassert>

using namespace yanmo;

int main() {
    std::cout << "=== YanMo IME Syllable Lattice Unit Tests ===\n";

    std::unordered_set<std::string> valid_syllables = {
        "shuo", "shen", "me", "ne", "guo", "ji", "bei", "jing", "da", "xue",
        "xi", "an", "xian", "ni", "hao", "zen", "hua", "fang", "zhong", "tian"
    };

    std::unordered_set<std::string> valid_prefixes = {
        "s", "sh", "shu", "g", "gu", "j", "b", "d", "x", "z", "zh", "n", "m", "h", "t"
    };

    std::vector<std::string> sorted_syllables(valid_syllables.begin(), valid_syllables.end());
    SyllableLattice lattice;

    // Test 1: 简拼 + 全拼: zgguoji -> [zg(简), guoji(全)]
    {
        std::cout << "[Test 1] Abbrev + Full: zgguoji... ";
        auto paths = lattice.search_top_k("zgguoji", valid_syllables, valid_prefixes, sorted_syllables, 3);
        assert(!paths.empty());
        const auto& chunks = paths[0].chunks;
        assert(chunks.size() == 2);
        assert(chunks[0].text == "zg" && chunks[0].is_abbrev);
        assert(chunks[1].text == "guoji" && !chunks[1].is_abbrev);
        std::cout << "PASSED (" << chunks[0].text << "[简] + " << chunks[1].text << "[全])\n";
    }

    // Test 2: 全拼 + 简拼: shuosmn -> [shuo(全), smn(简)]
    {
        std::cout << "[Test 2] Full + Abbrev: shuosmn... ";
        auto paths = lattice.search_top_k("shuosmn", valid_syllables, valid_prefixes, sorted_syllables, 3);
        assert(!paths.empty());
        const auto& chunks = paths[0].chunks;
        assert(chunks.size() == 2);
        assert(chunks[0].text == "shuo" && !chunks[0].is_abbrev);
        assert(chunks[1].text == "smn" && chunks[1].is_abbrev);
        std::cout << "PASSED (" << chunks[0].text << "[全] + " << chunks[1].text << "[简])\n";
    }

    // Test 3: 全 + 简 + 全: beijdxue -> [bei(全), jd(简), xue(全)]
    {
        std::cout << "[Test 3] Full + Abbrev + Full: beijdxue... ";
        auto paths = lattice.search_top_k("beijdxue", valid_syllables, valid_prefixes, sorted_syllables, 3);
        assert(!paths.empty());
        const auto& chunks = paths[0].chunks;
        assert(chunks.size() == 3);
        assert(chunks[0].text == "bei" && !chunks[0].is_abbrev);
        assert(chunks[1].text == "jd" && chunks[1].is_abbrev);
        assert(chunks[2].text == "xue" && !chunks[2].is_abbrev);
        std::cout << "PASSED (" << chunks[0].text << "[全] + " << chunks[1].text << "[简] + " << chunks[2].text << "[全])\n";
    }

    // Test 4: 简 + 全 + 简: nshuosm -> [n(简), shuo(全), sm(简)]
    {
        std::cout << "[Test 4] Abbrev + Full + Abbrev: nshuosm... ";
        auto paths = lattice.search_top_k("nshuosm", valid_syllables, valid_prefixes, sorted_syllables, 3);
        assert(!paths.empty());
        const auto& chunks = paths[0].chunks;
        assert(chunks.size() == 3);
        assert(chunks[0].text == "n" && chunks[0].is_abbrev);
        assert(chunks[1].text == "shuo" && !chunks[1].is_abbrev);
        assert(chunks[2].text == "sm" && chunks[2].is_abbrev);
        std::cout << "PASSED (" << chunks[0].text << "[简] + " << chunks[1].text << "[全] + " << chunks[2].text << "[简])\n";
    }

    // Test 5: 歧义音节: xian -> 同时产生 xian 与 xi + an
    {
        std::cout << "[Test 5] Ambiguity: xian... ";
        auto paths = lattice.search_top_k("xian", valid_syllables, valid_prefixes, sorted_syllables, 5);
        assert(paths.size() >= 2);
        bool found_single = false, found_dual = false;
        for (const auto& p : paths) {
            if (p.edges.size() == 1 && p.edges[0].text == "xian") found_single = true;
            if (p.edges.size() == 2 && p.edges[0].text == "xi" && p.edges[1].text == "an") found_dual = true;
        }
        assert(found_single && found_dual);
        std::cout << "PASSED (Found both [xian] and [xi, an])\n";
    }

    // Test 6: 隔音符切分: xi'an
    {
        std::cout << "[Test 6] Delimiter: xi'an... ";
        auto paths = lattice.search_top_k("xi'an", valid_syllables, valid_prefixes, sorted_syllables, 3);
        assert(!paths.empty());
        assert(paths[0].edges.size() == 2);
        assert(paths[0].edges[0].text == "xi" && paths[0].edges[1].text == "an");
        std::cout << "PASSED ([xi, an])\n";
    }

    // Test 7: 键盘空间邻键容错与倒装 (tain -> tian, nnihao -> nihao)
    {
        std::cout << "[Test 7] Typo correction & Spatial key: tain, nnihao... ";
        auto paths1 = lattice.search_top_k("tain", valid_syllables, valid_prefixes, sorted_syllables, 3);
        assert(!paths1.empty());
        bool found_tian = false;
        for (const auto& p : paths1) {
            if (p.edges.size() == 1 && p.edges[0].text == "tian") { found_tian = true; break; }
        }
        assert(found_tian && "Should correct transposed tain -> tian");

        auto paths2 = lattice.search_top_k("nnihao", valid_syllables, valid_prefixes, sorted_syllables, 3);
        assert(!paths2.empty());
        bool found_nihao = false;
        for (const auto& p : paths2) {
            if (p.edges.size() == 2 && p.edges[0].text == "ni" && p.edges[1].text == "hao") {
                found_nihao = true; break;
            }
        }
        assert(found_nihao && "Should correct stutter nnihao -> nihao");
        std::cout << "PASSED (Corrected tain -> tian, nnihao -> nihao)\n";
    }

    std::cout << "=== ALL LATTICE TESTS COMPLETED SUCCESSFULLY ===\n";
    return 0;
}
