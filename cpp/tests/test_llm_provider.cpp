#include "yanmo/rule_llm_provider.h"
#include <iostream>
#include <cassert>
#include <chrono>

using namespace yanmo;

void test_llm_provider_async() {
    std::cout << "[Test 1] ILLMProvider Async Prediction... ";
    RuleLLMProvider provider;
    assert(provider.is_ready());

    // 1. 发起异步联想预测
    auto start = std::chrono::high_resolution_clock::now();
    std::future<std::vector<AIAssistResult>> fut = provider.predict_async("我们今天", "");
    auto launch_end = std::chrono::high_resolution_clock::now();

    // 验证调用立刻返回（非阻塞，时间 < 2ms）
    double launch_ms = std::chrono::duration<double, std::milli>(launch_end - start).count();
    assert(launch_ms < 2.0 && "predict_async call blocked the main thread!");

    // 等待异步结果就绪
    auto results = fut.get();
    assert(!results.empty());
    assert(results[0].text == "天气真好");
    assert(results[0].prompt_summary == "豆包AI联想");

    std::cout << "PASSED (Returned: " << results[0].text << " in background)\n";
}

void test_llm_provider_rewrite() {
    std::cout << "[Test 2] ILLMProvider Async Rewrite... ";
    RuleLLMProvider provider;

    std::string raw = "呃言墨输入法那个非常好用就是说";
    auto fut = provider.rewrite_async(raw, "口语润色");

    std::string polished = fut.get();
    assert(polished.find("呃") == std::string::npos);
    assert(polished.find("那个") == std::string::npos);
    assert(polished.find("就是说") == std::string::npos);
    assert(polished.ends_with("。"));

    std::cout << "PASSED (Polished to: " << polished << ")\n";
}

int main() {
    std::cout << "=== YanMo IME ILLMProvider Unit Tests ===\n";
    test_llm_provider_async();
    test_llm_provider_rewrite();
    std::cout << "=== ALL LLM PROVIDER TESTS COMPLETED SUCCESSFULLY ===\n";
    return 0;
}
