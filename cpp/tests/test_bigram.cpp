#include "yanmo/bigram.h"
#include "yanmo/decoder.h"
#include <iostream>
#include <cassert>

using namespace yanmo;

void test_bigram_loading() {
    std::cout << "[Test 1] Bigram TSV Loading... ";
    BigramModel model;
    bool ok = model.load_from_tsv("data/dict/core_bigram.tsv");
    if (!ok) ok = model.load_from_tsv("../data/dict/core_bigram.tsv");
    if (!ok) ok = model.load_from_tsv("../../data/dict/core_bigram.tsv");
    assert(ok && "Failed to load core_bigram.tsv");
    assert(model.size() > 20);

    int s1 = model.get_transition_score("今天", "天气");
    assert(s1 > 10000);

    int s2 = model.get_transition_score("人工", "智能");
    assert(s2 > 10000);

    int s_none = model.get_transition_score("今天", "火星");
    assert(s_none == 0);

    std::cout << "PASSED (Loaded " << model.size() << " bigrams)\n";
}

void test_dynamic_learning() {
    std::cout << "[Test 2] Dynamic transition learning... ";
    BigramModel model;
    assert(model.get_transition_score("言墨", "超快") == 0);

    model.record_transition("言墨", "超快", 12000);
    assert(model.get_transition_score("言墨", "超快") == 12000);

    model.record_transition("言墨", "超快", 5000);
    assert(model.get_transition_score("言墨", "超快") == 17000);

    std::cout << "PASSED\n";
}

void test_decoder_integration() {
    std::cout << "[Test 3] Sentence Decoder with Bigram... ";
    BigramModel model;
    model.record_transition("今天", "天气", 20000);

    SentenceDecoder decoder;
    std::vector<std::string> syllables = {"jin", "tian", "tian", "qi"};

    // Mock lookup function
    auto mock_lookup = [](std::string_view py) -> std::pair<std::string, int> {
        if (py == "jintian") return {"今天", 10000};
        if (py == "tianqi") return {"天气", 10000};
        if (py == "jin") return {"金", 8000};
        if (py == "tian") return {"天", 9000};
        if (py == "qi") return {"气", 8000};
        return {"", 0};
    };

    auto [res, score] = decoder.decode(syllables, mock_lookup, &model);
    assert(res == "今天天气");
    assert(score > 60000); // 包含 bigram +20000 奖励

    std::cout << "PASSED (Result: " << res << ", Score: " << score << ")\n";
}

int main() {
    std::cout << "=== YanMo IME 2-Gram & Decoder Unit Tests ===\n";
    test_bigram_loading();
    test_dynamic_learning();
    test_decoder_integration();
    std::cout << "=== ALL BIGRAM TESTS COMPLETED SUCCESSFULLY ===\n";
    return 0;
}
