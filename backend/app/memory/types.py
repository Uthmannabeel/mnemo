"""Core data model for Mnemo's memory tiers.

The architecture mirrors human memory:

  WORKING     transient scratchpad for the current session (not persisted long-term)
  EPISODIC    raw, timestamped events ("what happened") — the source of truth
  SEMANTIC    distilled facts & user preferences ("what is generally true")
  PROCEDURAL  learned decision rules ("how to act in situation X")

Episodic memories are written continuously. The Dreaming consolidation loop reads
recent episodes and promotes durable knowledge upward into the semantic and
procedural tiers, where it is cheap to retrieve and steers future decisions.
"""
from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


class Tier(str, enum.Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uid() -> str:
    return uuid.uuid4().hex


@dataclass
class MemoryRecord:
    """A single memory in any tier."""

    content: str
    tier: Tier
    id: str = field(default_factory=_uid)
    user_id: str = "default"
    embedding: list[float] | None = None

    # Metadata used by retrieval scoring, decay, and conflict resolution.
    created_at: datetime = field(default_factory=_now)
    last_used_at: datetime = field(default_factory=_now)
    use_count: int = 0
    confidence: float = 0.6          # 0..1 — how much we trust this memory
    importance: float = 0.5          # 0..1 — salience, boosts retrieval + slows decay
    active: bool = True              # set False when superseded by conflict resolution

    # Provenance: which episode ids a distilled memory was derived from.
    source_ids: list[str] = field(default_factory=list)
    # Arbitrary structured payload (e.g. {"category": "billing"} for a rule).
    attrs: dict = field(default_factory=dict)

    def touch(self) -> None:
        self.last_used_at = _now()
        self.use_count += 1

    def to_public(self) -> dict:
        return {
            "id": self.id,
            "tier": self.tier.value,
            "content": self.content,
            "confidence": round(self.confidence, 3),
            "importance": round(self.importance, 3),
            "use_count": self.use_count,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "source_ids": self.source_ids,
            "attrs": self.attrs,
        }


@dataclass
class ScoredMemory:
    record: MemoryRecord
    score: float          # final retrieval score
    similarity: float     # raw cosine similarity component


@dataclass
class Decision:
    """A decision the agent made, with the memories that justified it (provenance)."""

    query: str
    prediction: dict
    used_memory_ids: list[str]       # everything retrieved (provenance / "what I looked at")
    rationale: str
    fired_memory_ids: list[str] = field(default_factory=list)  # rules that actually drove the call
    id: str = field(default_factory=_uid)
    created_at: datetime = field(default_factory=_now)
