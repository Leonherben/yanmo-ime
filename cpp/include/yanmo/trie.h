#pragma once

#include <array>
#include <memory>
#include <string_view>
#include <vector>

namespace yanmo {

class TrieNode {
public:
    std::array<std::unique_ptr<TrieNode>, 26> children{};
    std::vector<uint32_t> indices;

    TrieNode() = default;
};

class Trie {
public:
    Trie();
    ~Trie();

    void insert(std::string_view pinyin, uint32_t item_index);
    void search_prefix(std::string_view prefix, std::vector<uint32_t>& out_indices) const;
    const std::vector<uint32_t>* search_exact(std::string_view pinyin) const;
    void clear();

private:
    std::unique_ptr<TrieNode> root_;
    void collect_all(const TrieNode* node, std::vector<uint32_t>& out_indices) const;
};

} // namespace yanmo
