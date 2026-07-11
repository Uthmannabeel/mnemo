"""MemoryManager — the orchestration layer over the tiered stores.

Responsibilities:
  * write episodic events (with embeddings)
  * retrieve a blended, decayed, provenance-tracked working set for a decision
  * apply recency decay when scoring
  * expose promotion + conflict-resolution primitives used by the Dreaming loop
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..config import get_settings
from ..qwen_client import QwenClient, get_qwen
from .store import MemoryStore, make_store
from .types import MemoryRecord, ScoredMemory, Tier

# Retrieval weights: how much each signal contributes to a memory's final score.
_W_SIM = 0.60      # semantic similarity to the query
_W_RECENCY = 0.15  # how recently the memory was created/used (decays by half-life)
_W_IMPORTANCE = 0.15
_W_CONFIDENCE = 0.10


class MemoryManager:
    def __init__(self, store: MemoryStore | None = None, qwen: QwenClient | None = None) -> None:
        self.s = get_settings()
        # Injectable so e.g. the benchmark can force the deterministic offline client.
        self.qwen = qwen or get_qwen()
        self.store = store or make_store(self.s.mnemo_store, self.s.database_url, self.s.qwen_embed_dim)

    # ------------------------------------------------------------- writing
    def remember(
        self,
        content: str,
        tier: Tier = Tier.EPISODIC,
        user_id: str = "default",
        confidence: float = 0.6,
        importance: float = 0.5,
        source_ids: list[str] | None = None,
        attrs: dict | None = None,
    ) -> MemoryRecord:
        rec = MemoryRecord(
            content=content,
            tier=tier,
            user_id=user_id,
            embedding=self.qwen.embed_one(content),
            confidence=confidence,
            importance=importance,
            source_ids=source_ids or [],
            attrs=attrs or {},
        )
        self.store.add(rec)
        return rec

    # ----------------------------------------------------------- retrieval
    def _recency_weight(self, ts: datetime) -> float:
        age_days = (datetime.now(timezone.utc) - ts).total_seconds() / 86400.0
        half_life = max(self.s.memory_half_life_days, 0.5)
        return 0.5 ** (age_days / half_life)

    def _score(self, rec: MemoryRecord, similarity: float) -> float:
        recency = self._recency_weight(rec.last_used_at)
        return (
            _W_SIM * similarity
            + _W_RECENCY * recency
            + _W_IMPORTANCE * rec.importance
            + _W_CONFIDENCE * rec.confidence
        )

    def retrieve(
        self,
        query: str,
        user_id: str = "default",
        k_per_tier: dict[Tier, int] | None = None,
    ) -> list[ScoredMemory]:
        """Retrieve a blended working set across tiers, re-ranked with decay.

        Procedural + semantic memories are cheap, high-signal knowledge; we pull a
        few of each plus the most similar raw episodes for grounding.
        """
        k_per_tier = k_per_tier or {
            Tier.PROCEDURAL: 4,
            Tier.SEMANTIC: 4,
            Tier.EPISODIC: 6,
        }
        q_emb = self.qwen.embed_one(query)
        out: list[ScoredMemory] = []
        for tier, k in k_per_tier.items():
            for rec, sim in self.store.search(user_id, q_emb, tier, k):
                out.append(ScoredMemory(record=rec, score=self._score(rec, sim), similarity=sim))
        out.sort(key=lambda sm: sm.score, reverse=True)
        # Mark retrieved memories as used (strengthens them against decay) —
        # one batched store write, not a round-trip per record.
        self.store.mark_used([sm.record.id for sm in out])
        return out

    # -------------------------------------------------- promotion / conflict
    def promote(
        self,
        content: str,
        tier: Tier,
        source_ids: list[str],
        confidence: float,
        importance: float,
        user_id: str = "default",
        attrs: dict | None = None,
    ) -> MemoryRecord:
        """Create a distilled semantic/procedural memory derived from episodes."""
        return self.remember(
            content=content,
            tier=tier,
            user_id=user_id,
            confidence=confidence,
            importance=importance,
            source_ids=source_ids,
            attrs=attrs,
        )

    def reinforce(self, record: MemoryRecord, delta: float) -> None:
        """Nudge a memory's confidence up (positive delta) or down, then persist."""
        record.confidence = max(0.0, min(1.0, record.confidence + delta))
        if record.confidence < 0.15:
            record.active = False  # decayed into irrelevance
        self.store.update(record)

    def supersede(self, old: MemoryRecord, new_content: str, attrs: dict | None = None) -> MemoryRecord:
        """Conflict resolution: retire an outdated memory, replace with a corrected one."""
        old.active = False
        self.store.update(old)
        return self.promote(
            content=new_content,
            tier=old.tier,
            source_ids=old.source_ids + [old.id],
            confidence=min(1.0, old.confidence + 0.1),
            importance=old.importance,
            user_id=old.user_id,
            attrs=attrs or old.attrs,
        )

    # ------------------------------------------------------------- reporting
    def snapshot(self, user_id: str = "default") -> dict:
        """Full tier snapshot for the dashboard."""
        return {
            tier.value: [r.to_public() for r in self.store.all(user_id, tier)]
            for tier in (Tier.EPISODIC, Tier.SEMANTIC, Tier.PROCEDURAL)
        }
