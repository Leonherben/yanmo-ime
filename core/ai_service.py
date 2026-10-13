"""
AI Assistant & Large Language Model Subsystem for YanMo IME (言墨输入法).
Provides asynchronous next-words prediction and smart text rewriting (Doubao-style).
Supports:
  1. Offline rule-based smart filtering (zero-network oral filler removal & punctuation correction)
  2. Local Ollama (e.g. qwen2.5-coder:1.5b)
  3. OpenAI-compatible Cloud APIs (Doubao, DeepSeek, etc.)
"""

import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, List, Optional
import urllib.request
import urllib.error


class AIService:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or (Path.home() / ".config" / "yanmo" / "config.json")
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="YanMo-AI")
        self.config = self._load_config()

        # Common oral fillers to strip in voice transcript polishing
        self.filler_pattern = re.compile(r"^(呃|啊|那个|就是说|然后就是|嗯)+|[，, ]*(呃|啊|那个|就是说|然后就是|嗯)+")

    def _load_config(self) -> dict:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "ai_enabled": True,
            "ai_backend": "rule", # "rule", "ollama", "openai_compatible"
            "ai_model": "qwen2.5-coder:1.5b",
            "ai_api_base": "http://localhost:11434/v1",
            "ai_api_key": ""
        }

    def predict_next_words_async(
        self,
        committed_context: str,
        current_pinyin: str,
        callback: Callable[[List[str]], None]
    ):
        """Asynchronously predict 1-3 candidate phrases based on context (non-blocking)."""
        def _worker():
            results = self.predict_next_words(committed_context, current_pinyin)
            callback(results)

        self.executor.submit(_worker)

    def rewrite_text_async(
        self,
        raw_text: str,
        instruction: str,
        callback: Callable[[str], None]
    ):
        """Asynchronously polish/rewrite text (e.g. oral speech cleanup or formatting)."""
        def _worker():
            polished = self.rewrite_text(raw_text, instruction)
            callback(polished)

        self.executor.submit(_worker)

    def predict_next_words(self, context: str, pinyin: str = "") -> List[str]:
        """Synchronous implementation of next-words prediction."""
        if not context:
            return []

        backend = self.config.get("ai_backend", "rule")

        # 1. Ollama or OpenAI compatible backend
        if backend in ("ollama", "openai_compatible") and self.config.get("ai_api_base"):
            try:
                prompt = (
                    f"你是一个输入法智能联想助手。根据用户输入的上下文：'{context}'，"
                    f"给出接下来最可能输入的 3 个简短后续词或短语（每个不超过 6 个字）。"
                    f"只输出一个纯 JSON 字符串数组，例如 [\"词语1\", \"词语2\", \"词语3\"]，不要包含任何其他文字。"
                )
                res_text = self._call_llm_api(prompt)
                match = re.search(r"\[.*?\]", res_text, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed[:3]]
            except Exception:
                pass

        # 2. Local rule-based fallback predictions
        rule_map = {
            "今天": ["天气真好", "是个好日子", "工作顺利"],
            "人工智能": ["技术应用", "深度学习", "大模型发展"],
            "言墨": ["输入法", "轻巧自如", "核心引擎"],
            "开源": ["软件生态", "社区贡献", "项目代码"],
            "开发": ["软件系统", "效率提升", "跨平台应用"],
            "系统": ["架构设计", "运行正常", "性能优化"],
        }

        for k, v in rule_map.items():
            if context.endswith(k):
                return v

        return []

    def rewrite_text(self, text: str, instruction: str = "口语润色") -> str:
        """Synchronous implementation of text rewrite / speech polishing."""
        if not text:
            return ""

        backend = self.config.get("ai_backend", "rule")

        # 1. Ollama or OpenAI compatible backend
        if backend in ("ollama", "openai_compatible") and self.config.get("ai_api_base"):
            try:
                prompt = (
                    f"请对以下用户输入的文本进行{instruction}：去除多余的语气助词、修正错别字并规范标点。"
                    f"只输出修改后的最终文本，严禁包含任何多余解释。\n文本：{text}"
                )
                res = self._call_llm_api(prompt)
                if res:
                    return res.strip()
            except Exception:
                pass

        # 2. Local offline smart rule cleaner
        # Clean oral fillers: "呃", "那个", "就是说"
        cleaned = self.filler_pattern.sub("", text)
        cleaned = re.sub(r"[，, ]{2,}", "，", cleaned)
        cleaned = cleaned.strip()

        # Punctuation normalization
        if cleaned and cleaned[-1] not in ("。", "！", "？", "，", ".", "!", "?"):
            cleaned += "。"

        return cleaned

    def _call_llm_api(self, prompt: str, timeout: float = 2.5) -> str:
        """Helper to invoke OpenAI-compatible /v1/chat/completions endpoint."""
        api_base = self.config.get("ai_api_base", "http://localhost:11434/v1").rstrip("/")
        url = f"{api_base}/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        api_key = self.config.get("ai_api_key", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": self.config.get("ai_model", "qwen2.5-coder:1.5b"),
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 128
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
