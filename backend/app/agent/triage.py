"""TriageAgent — predicts a ticket's category, grounded in memory, then learns.

Decision flow:
  1. retrieve() a blended working set (procedural rules + semantic facts + similar
     past episodes) for the incoming ticket.
  2. decide the category. Online: Qwen3.7-Max reasons over the memory context.
     Offline: a memory-weighted vote (procedural rules + episodic k-NN).
  3. every decision carries provenance — the exact memory ids that justified it.
  4. learn(): record the outcome as a new episode and reinforce/penalise the
     procedural rules that were actually used, so trust tracks real accuracy.

The whole point: prediction #1 has no memory and is a coin-flip; after the Dreaming
loop distils rules from feedback, later predictions get measurably better.
"""
from __future__ import annotations

import logging

from ..memory.manager import MemoryManager
from ..memory.types import Decision, ScoredMemory, Tier

logger = logging.getLogger(__name__)

CATEGORIES = ["billing", "technical", "account", "shipping", "feedback"]

_SYSTEM = """You are a support-ticket triage agent. Assign exactly one category from:
billing, technical, account, shipping, feedback.

You are given MEMORY: learned rules and similar past tickets with their true category.
Trust high-confidence procedural rules and consistent precedent. Respond as JSON:
{"category": "<one-of-the-categories>", "rationale": "<one sentence>"}"""


# Retrieval budget: a decision may only look at this many memories (finite context).
# The experiment's whole point is what an agent does with a *limited* budget.
_BUDGET = 6

_MODE_TIERS: dict[str, dict] = {
    "none": {},  # memoryless control
    "episodic": {Tier.EPISODIC: _BUDGET},  # raw-RAG baseline: only past tickets
    # Mnemo spends the same total budget across tiers. max(0, ...) guards small budgets.
    "full": {Tier.PROCEDURAL: 3, Tier.SEMANTIC: 1, Tier.EPISODIC: max(0, _BUDGET - 4)},
}


class TriageAgent:
    def __init__(self, manager: MemoryManager | None = None, mode: str = "full") -> None:
        self.m = manager or MemoryManager()
        self.qwen = self.m.qwen  # share the manager's client so embed + reason stay consistent
        self.mode = mode

    # --------------------------------------------------------------- predict
    def predict(self, ticket: str, user_id: str = "default") -> Decision:
        tiers = _MODE_TIERS[self.mode]
        working = self.m.retrieve(ticket, user_id=user_id, k_per_tier=tiers) if tiers else []
        if self.qwen.offline:
            category, rationale = self._decide_offline(ticket, working)
        else:
            category, rationale = self._decide_online(ticket, working)
        return Decision(
            query=ticket,
            prediction={"category": category},
            used_memory_ids=[sm.record.id for sm in working],
            fired_memory_ids=self._fired_rules(ticket, working, category),
            context_chars=sum(len(sm.record.content) for sm in working),
            rationale=rationale,
        )

    @staticmethod
    def _fired_rules(ticket: str, working: list[ScoredMemory], category: str) -> list[str]:
        """Procedural rules that actually influenced this call: right category AND a
        keyword present in the ticket. Only these earn credit/blame in learn()."""
        t = ticket.lower()
        return [
            sm.record.id
            for sm in working
            if sm.record.tier is Tier.PROCEDURAL
            and sm.record.attrs.get("category") == category
            and any(kw in t for kw in sm.record.attrs.get("keywords", []))
        ]

    def _decide_online(self, ticket: str, working: list[ScoredMemory]) -> tuple[str, str]:
        ctx = self._format_memory(working) or "(no memory yet)"
        messages = [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"MEMORY:\n{ctx}\n\nTICKET:\n{ticket}"},
        ]
        try:
            from ..qwen_client import _extract_json

            content = self.qwen.chat(messages, temperature=0.1)
            data = _extract_json(content or "{}")
            cat = data.get("category", "").lower()
            if cat not in CATEGORIES:
                cat, _ = self._decide_offline(ticket, working)
                return cat, "fallback: model returned an unknown category"
            return cat, data.get("rationale", "")
        except Exception:
            # Otherwise a broken key / endpoint looks exactly like offline mode.
            logger.warning("online decision failed; falling back to offline vote", exc_info=True)
            return self._decide_offline(ticket, working)

    def _decide_offline(self, ticket: str, working: list[ScoredMemory]) -> tuple[str, str]:
        """Memory-weighted vote: procedural rules + episodic precedent."""
        scores: dict[str, float] = {c: 0.0 for c in CATEGORIES}
        used_rule = None
        t = ticket.lower()
        for sm in working:
            rec = sm.record
            cat = rec.attrs.get("category")
            if cat not in scores:
                continue
            if rec.tier is Tier.PROCEDURAL:
                if any(kw in t for kw in rec.attrs.get("keywords", [])):
                    scores[cat] += 2.5 * rec.confidence * sm.score
                    used_rule = rec.content
            elif rec.tier is Tier.EPISODIC:
                scores[cat] += 1.0 * sm.similarity
            elif rec.tier is Tier.SEMANTIC:
                # Distilled facts act as a weak prior — same signal the online model
                # reads from the semantic tier, so offline/online don't fork. Kept small
                # so it can never override a concrete rule or precedent.
                scores[cat] += 0.3 * rec.confidence * sm.score
        best = max(scores, key=scores.get)
        if scores[best] == 0.0:  # cold start / "none" control — no useful memory in scope
            # Deterministic ~chance guess (1/len(CATEGORIES)); anchors the no-memory arm.
            return CATEGORIES[len(ticket) % len(CATEGORIES)], "cold start: no memory, guessed"
        why = f"matched rule: {used_rule}" if used_rule else "matched similar past tickets"
        return best, why

    # ----------------------------------------------------------------- learn
    def learn(self, decision: Decision, true_category: str, user_id: str = "default") -> None:
        correct = decision.prediction["category"] == true_category
        # 1. Write the outcome as a new episode (raw experience).
        self.m.remember(
            content=decision.query,
            tier=Tier.EPISODIC,
            user_id=user_id,
            confidence=0.9,
            importance=0.55 if correct else 0.75,  # mistakes are more salient to learn from
            attrs={
                "category": true_category,
                "predicted": decision.prediction["category"],
                "correct": correct,
            },
        )
        # 2. Credit-assign: reinforce/penalise ONLY the rules that actually fired for this
        # decision (not every retrieved memory), so an inert rule isn't rewarded/blamed.
        # Ownership check is load-bearing: fired ids arrive from the client on /feedback,
        # so one workspace must never be able to move another workspace's rules.
        for mid in decision.fired_memory_ids:
            rec = self.m.store.get(mid)
            if rec and rec.user_id == user_id and rec.tier is Tier.PROCEDURAL:
                self.m.reinforce(rec, +0.05 if correct else -0.12)

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _format_memory(working: list[ScoredMemory]) -> str:
        lines = []
        for sm in working:
            r = sm.record
            tag = r.tier.value.upper()
            extra = f" (cat={r.attrs.get('category')})" if r.attrs.get("category") else ""
            lines.append(f"- [{tag} conf={r.confidence:.2f}] {r.content}{extra}")
        return "\n".join(lines)
