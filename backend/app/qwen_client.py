"""Thin, well-typed wrapper around Qwen models on Alibaba Cloud Model Studio.

Uses the OpenAI-compatible DashScope endpoint so we get first-class tool calling,
structured output, and the `preserve_thinking` agent feature. Falls back to a
deterministic offline embedding so the memory pipeline and eval harness run in
CI / local dev without spending credits (chat reasoning still requires the API).
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import OrderedDict
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from .config import get_settings


class QwenClient:
    def __init__(self, force_offline: bool = False) -> None:
        self.s = get_settings()
        self.force_offline = force_offline  # e.g. the benchmark: deterministic + free by design
        self._embed_cache: "OrderedDict[str, list[float]]" = OrderedDict()
        self._client = None
        if not self.offline:
            # Imported lazily so offline/CI environments need no network stack configured.
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.s.dashscope_api_key,
                base_url=self.s.qwen_base_url,
            )

    @property
    def offline(self) -> bool:
        return self.force_offline or self.s.offline

    # ------------------------------------------------------------------ chat
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        temperature: float = 0.2,
        preserve_thinking: bool = True,
    ) -> Any:
        """Chat completion against Qwen.

        Default path streams and returns the aggregated *text content* — the Max tier
        (qwen3.7-max) is thinking-only and thinking models on DashScope require
        streaming, so this is the shape that works everywhere. When `tools` are passed,
        falls back to a non-streaming call and returns the full message object (tool
        calls need it).
        """
        if self._client is None:
            raise RuntimeError(
                "QwenClient.chat() called in offline mode. Set DASHSCOPE_API_KEY "
                "and MNEMO_OFFLINE=0, or use the agent's offline heuristic path."
            )
        extra_body: dict[str, Any] = {"preserve_thinking": preserve_thinking}
        if tools:
            resp = self._client.chat.completions.create(
                model=self.s.qwen_model,
                messages=messages,
                tools=tools,
                temperature=temperature,
                extra_body=extra_body,
            )
            return resp.choices[0].message
        stream = self._client.chat.completions.create(
            model=self.s.qwen_model,
            messages=messages,
            temperature=temperature,
            stream=True,
            extra_body=extra_body,
        )
        parts: list[str] = []
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                parts.append(chunk.choices[0].delta.content)  # reasoning_content deltas skipped
        return "".join(parts)

    def complete_json(self, system: str, user: str, temperature: float = 0.1) -> dict:
        """Ask Qwen for a JSON object and parse it. Used by the consolidation loop."""
        messages = [
            {"role": "system", "content": system + "\nRespond with a single valid JSON object and nothing else."},
            {"role": "user", "content": user},
        ]
        text = self.chat(messages, temperature=temperature, preserve_thinking=False)
        return _extract_json(text or "{}")

    # ------------------------------------------------------------- embeddings
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Deterministic hashing fallback when offline."""
        if self._client is None:
            return [_offline_embed(t, self.s.qwen_embed_dim) for t in texts]
        try:
            # Pin dimensions: the pgvector schema is created with QWEN_EMBED_DIM.
            resp = self._client.embeddings.create(
                model=self.s.qwen_embed_model, input=texts, dimensions=self.s.qwen_embed_dim
            )
        except Exception:
            resp = self._client.embeddings.create(model=self.s.qwen_embed_model, input=texts)
        # Sort by index so results align with `texts` regardless of server ordering.
        vecs = [d.embedding for d in sorted(resp.data, key=lambda d: d.index)]
        if vecs and len(vecs[0]) != self.s.qwen_embed_dim:
            raise RuntimeError(
                f"Embedding model returned dim {len(vecs[0])} but QWEN_EMBED_DIM="
                f"{self.s.qwen_embed_dim}; align .env with the model (pgvector schema depends on it)."
            )
        return vecs

    def embed_one(self, text: str) -> list[float]:
        # Small LRU: repeated queries (retrieval is called per decision) skip the
        # network round-trip — free offline, saves credits + latency online.
        hit = self._embed_cache.get(text)
        if hit is not None:
            self._embed_cache.move_to_end(text)
            return hit
        vec = self.embed([text])[0]
        self._embed_cache[text] = vec
        if len(self._embed_cache) > 4096:
            self._embed_cache.popitem(last=False)
        return vec


# ----------------------------------------------------------------- utilities
def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") : text.rfind("}") + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start : end + 1])
        raise


def _offline_embed(text: str, dim: int) -> list[float]:
    """Deterministic bag-of-token hashing embedding.

    Cosine similarity between two of these correlates with token overlap, which is
    enough for the memory-retrieval demo to behave sensibly without the API.
    """
    vec = [0.0] * dim
    for token in _tokenize(text):
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _tokenize(text: str) -> list[str]:
    return [t for t in "".join(c.lower() if c.isalnum() else " " for c in text).split() if len(t) > 1]


_client_singleton: QwenClient | None = None


def get_qwen() -> QwenClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = QwenClient()
    return _client_singleton
