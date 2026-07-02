"""The Dreaming loop — autonomous memory consolidation.

Periodically (or as a scheduled Alibaba Cloud Function Compute job) Mnemo "sleeps":
it reflects over recent, unconsolidated episodes and distills durable knowledge
into the higher tiers.

  episodes  ──reflect──▶  SEMANTIC facts     ("this user's refund requests are
                                               usually about duplicate charges")
            ──reflect──▶  PROCEDURAL rules   ("if ticket mentions 'charged twice'
                                               → category=billing, priority=high")

Two code paths:
  * online  — Qwen3.7-Max reads the episodes and returns structured insights.
  * offline — a deterministic statistical distiller (keyword→outcome association)
              so the pipeline + eval run without API access.

Every distilled memory records the episode ids it came from (provenance) and a
confidence derived from the strength of the evidence.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

from .manager import MemoryManager
from .types import MemoryRecord, Tier

_STOP = set(
    "the a an and or to of for in on is are was i you it my me we they them this that with "
    "have has had be been will can could should would about at as by".split()
)

_REFLECT_SYSTEM = """You are the memory-consolidation subsystem of a support-triage agent.
You are given recent EPISODES: each is a resolved ticket with its final category and
whether the agent's live prediction was correct. Distill *durable, reusable* knowledge.

Return JSON:
{
  "semantic": [ {"content": "...", "confidence": 0.0-1.0, "importance": 0.0-1.0, "source_ids": ["..."]} ],
  "procedural": [ {"content": "IF <signal> THEN category=<cat> (why)", "category": "<cat>",
                   "keywords": ["..."], "confidence": 0.0-1.0, "importance": 0.0-1.0, "source_ids": ["..."]} ]
}
Only assert rules the evidence supports. Prefer a few high-confidence rules over many weak ones."""


class Consolidator:
    def __init__(self, manager: MemoryManager) -> None:
        self.m = manager
        self.qwen = manager.qwen  # share the manager's client (may be force-offline)

    def _recent_unconsolidated(self, user_id: str) -> list[MemoryRecord]:
        # The "already consolidated" flag lives in the store, not in process memory,
        # so a separate Function Compute cron shares state with the API over RDS and
        # never re-processes the same episodes.
        eps = self.m.store.all(user_id, Tier.EPISODIC)
        return [e for e in eps if not e.attrs.get("consolidated")]

    def run(self, user_id: str = "default") -> dict:
        """One Dreaming pass. Returns a summary for logging/telemetry.

        New (unconsolidated) episodes *trigger* the pass, but reflection runs over the
        full episodic history: slow-recurring signals (e.g. an org convention seen once
        per session) accumulate evidence across passes instead of being lost to a
        too-small window, and spurious correlations that look strong in one window
        wash out against the whole record.
        """
        episodes = self._recent_unconsolidated(user_id)
        if not episodes:
            return {"episodes": 0, "semantic": 0, "procedural": 0}
        history = self.m.store.all(user_id, Tier.EPISODIC)

        if self.qwen.offline:
            result = self._reflect_offline(history)
        else:
            # Cap the reflection prompt; most-recent window still spans multiple passes.
            result = self._reflect_online(history[-60:])

        created = {"semantic": 0, "procedural": 0}
        for item in result.get("semantic", []):
            self._commit(user_id, item, Tier.SEMANTIC)
            created["semantic"] += 1
        for item in result.get("procedural", []):
            self._commit(user_id, item, Tier.PROCEDURAL)
            created["procedural"] += 1

        for e in episodes:
            e.attrs["consolidated"] = True
            self.m.store.update(e)
        return {"episodes": len(episodes), **created}

    # ----------------------------------------------------- commit w/ conflict
    def _commit(self, user_id: str, item: dict, tier: Tier) -> None:
        content = (item.get("content") or "").strip()
        if not content:
            return
        attrs = {k: item[k] for k in ("category", "keywords") if k in item}

        # Reconcile against existing rules that share a keyword (the discriminative
        # signal), NOT just the same category — otherwise every same-category rule
        # looks alike and we'd keep only one keyword per category, capping the ceiling.
        if tier is Tier.PROCEDURAL:
            new_kws = set(attrs.get("keywords", []))
            new_cat = attrs.get("category")
            for existing in self.m.store.all(user_id, Tier.PROCEDURAL):
                ex_kws = set(existing.attrs.get("keywords", []))
                if not (new_kws and ex_kws and (new_kws & ex_kws)):
                    continue  # different keyword → an unrelated, distinct rule
                if existing.attrs.get("category") == new_cat:
                    self.m.reinforce(existing, +0.08)          # same keyword & verdict: corroborate
                else:
                    self.m.supersede(existing, content, attrs)  # same keyword, NEW verdict: conflict → replace
                return
            # No overlapping-keyword rule exists → keep this as a new distinct rule.

        self.m.promote(
            content=content,
            tier=tier,
            source_ids=item.get("source_ids", []),
            confidence=float(item.get("confidence", 0.6)),
            importance=float(item.get("importance", 0.5)),
            user_id=user_id,
            attrs=attrs,
        )

    # ------------------------------------------------------------- online
    def _reflect_online(self, episodes: list[MemoryRecord]) -> dict:
        lines = []
        for e in episodes:
            lines.append(
                f"[{e.id}] text={e.content!r} category={e.attrs.get('category')} "
                f"predicted={e.attrs.get('predicted')} correct={e.attrs.get('correct')}"
            )
        user = "EPISODES:\n" + "\n".join(lines)
        try:
            return self.qwen.complete_json(_REFLECT_SYSTEM, user)
        except Exception:
            # Never let a bad LLM response stall the Dreaming loop.
            return self._reflect_offline(episodes)

    # ------------------------------------------------------------- offline
    # Evidence weighting: recent experience outweighs stale experience (gamma decay
    # over episode order), and episodes where the agent was WRONG count double —
    # mistakes are the most salient thing to learn from. This is what lets a changed
    # org policy actually flip a rule instead of being outvoted by history forever.
    _GAMMA = 0.96          # per-episode decay; half-weight after ~17 episodes
    _MISTAKE_WEIGHT = 2.0  # corrected mispredictions carry extra evidence

    def _reflect_offline(self, episodes: list[MemoryRecord]) -> dict:
        """Statistical distiller: associate keywords with outcome categories."""
        kw_cat: dict[str, Counter] = defaultdict(Counter)
        kw_sources: dict[str, list[str]] = defaultdict(list)
        cat_counts: Counter = Counter()

        n = len(episodes)
        for i, e in enumerate(episodes):
            cat = e.attrs.get("category")
            if not cat:
                continue
            w = self._GAMMA ** (n - 1 - i)  # episodes arrive in chronological order
            if e.attrs.get("correct") is False:
                w *= self._MISTAKE_WEIGHT
            cat_counts[cat] += 1
            # sorted() so rule-creation order doesn't depend on set-iteration order
            # (PYTHONHASHSEED randomizes str hashing) — keeps the whole eval reproducible.
            for kw in sorted(set(_keywords(e.content))):
                kw_cat[kw][cat] += w
                if len(kw_sources[kw]) < 5:
                    kw_sources[kw].append(e.id)

        procedural = []
        for kw in sorted(kw_cat):
            cats = kw_cat[kw]
            cat, hits = cats.most_common(1)[0]
            total = sum(cats.values())
            if hits >= 2.0 and hits / total >= 0.75:  # strong, consistent, current signal
                conf = min(0.95, 0.5 + 0.1 * hits)
                procedural.append({
                    "content": f"IF ticket mentions '{kw}' THEN category={cat}",
                    "category": cat,
                    "keywords": [kw],
                    "confidence": round(conf, 2),
                    "importance": min(0.9, 0.4 + 0.05 * hits),
                    "source_ids": kw_sources[kw],
                })
        # Stable ordering: confidence desc, then keyword — fully deterministic.
        procedural.sort(key=lambda p: (-p["confidence"], p["keywords"][0]))

        semantic = []
        if cat_counts:
            top_cat, top_n = cat_counts.most_common(1)[0]
            semantic.append({
                "content": f"Most incoming tickets in this window resolved to '{top_cat}' "
                           f"({top_n}/{sum(cat_counts.values())}).",
                "category": top_cat,  # lets the decision layer use it as a weak prior
                "confidence": 0.7,
                "importance": 0.5,
                "source_ids": [e.id for e in episodes[:5]],
            })
        return {"semantic": semantic, "procedural": procedural[:12]}


def _keywords(text: str) -> list[str]:
    toks = re.findall(r"[a-z][a-z0-9]+", text.lower())
    return [t for t in toks if t not in _STOP and len(t) > 2]
