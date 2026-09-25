"""
High-performance Prefix Tree (Trie) for Pinyin search in YanMo IME.
"""

from typing import Dict, List, Optional
from .models import Candidate


class TrieNode:
    __slots__ = ("children", "candidates", "is_end")

    def __init__(self):
        self.children: Dict[str, "TrieNode"] = {}
        self.candidates: List[Candidate] = []
        self.is_end: bool = False


class PinyinTrie:
    def __init__(self):
        self.root = TrieNode()
        self._total_entries = 0

    def insert(self, pinyin: str, candidate: Candidate):
        """Insert a candidate into the Trie indexed by its pinyin."""
        node = self.root
        for char in pinyin.lower():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]

        node.is_end = True
        node.candidates.append(candidate)
        self._total_entries += 1

    def search_exact(self, pinyin: str) -> List[Candidate]:
        """Search exact pinyin match."""
        node = self.root
        for char in pinyin.lower():
            if char not in node.children:
                return []
            node = node.children[char]

        if node.is_end:
            return list(node.candidates)
        return []

    def search_prefix(self, prefix: str, limit: int = 25) -> List[Candidate]:
        """
        Search all candidates whose pinyin starts with the given prefix.
        Sorted by candidate frequency descending.
        """
        node = self.root
        for char in prefix.lower():
            if char not in node.children:
                return []
            node = node.children[char]

        # Collect all candidates in the subtree using BFS/DFS
        collected: List[Candidate] = []
        queue = [node]

        while queue:
            curr = queue.pop(0)
            if curr.is_end:
                collected.extend(curr.candidates)
            for child in curr.children.values():
                queue.append(child)

        # Sort and deduplicate by word text
        collected.sort(key=lambda c: c.freq, reverse=True)
        seen = set()
        deduped = []
        for c in collected:
            if c.text not in seen:
                seen.add(c.text)
                deduped.append(c)
                if len(deduped) >= limit:
                    break

        return deduped

    def count(self) -> int:
        return self._total_entries
