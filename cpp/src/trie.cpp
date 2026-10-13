#include "yanmo/trie.h"
#include <cctype>

namespace yanmo {

Trie::Trie() : root_(std::make_unique<TrieNode>()) {}
Trie::~Trie() = default;

void Trie::insert(std::string_view pinyin, uint32_t item_index) {
    if (pinyin.empty()) return;
    TrieNode* curr = root_.get();

    for (char c : pinyin) {
        if (!std::isalpha(static_cast<unsigned char>(c))) continue;
        int idx = std::tolower(static_cast<unsigned char>(c)) - 'a';
        if (idx < 0 || idx >= 26) continue;

        if (!curr->children[idx]) {
            curr->children[idx] = std::make_unique<TrieNode>();
        }
        curr = curr->children[idx].get();
    }
    curr->indices.push_back(item_index);
}

void Trie::search_prefix(std::string_view prefix, std::vector<uint32_t>& out_indices) const {
    out_indices.clear();
    if (prefix.empty()) return;

    const TrieNode* curr = root_.get();
    for (char c : prefix) {
        if (!std::isalpha(static_cast<unsigned char>(c))) return;
        int idx = std::tolower(static_cast<unsigned char>(c)) - 'a';
        if (idx < 0 || idx >= 26 || !curr->children[idx]) return;
        curr = curr->children[idx].get();
    }

    collect_all(curr, out_indices);
}

const std::vector<uint32_t>* Trie::search_exact(std::string_view pinyin) const {
    if (pinyin.empty()) return nullptr;

    const TrieNode* curr = root_.get();
    for (char c : pinyin) {
        if (!std::isalpha(static_cast<unsigned char>(c))) return nullptr;
        int idx = std::tolower(static_cast<unsigned char>(c)) - 'a';
        if (idx < 0 || idx >= 26 || !curr->children[idx]) return nullptr;
        curr = curr->children[idx].get();
    }

    return curr->indices.empty() ? nullptr : &curr->indices;
}

void Trie::collect_all(const TrieNode* node, std::vector<uint32_t>& out_indices) const {
    if (!node) return;
    for (uint32_t idx : node->indices) {
        out_indices.push_back(idx);
    }
    for (const auto& child : node->children) {
        if (child) {
            collect_all(child.get(), out_indices);
        }
    }
}

void Trie::clear() {
    root_ = std::make_unique<TrieNode>();
}

} // namespace yanmo
