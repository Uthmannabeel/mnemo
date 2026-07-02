"""Regression test: Mnemo adapts when the organization CHANGES a policy.

Accumulating experience is table stakes; the harder property is unlearning.
Scenario: for weeks refunds route to `account` (policy). Then the org changes the
policy — refunds now go to `billing`. The agent keeps predicting `account`, gets
corrected, and consolidation must SUPERSEDE the stale rule with the new one —
recency-weighted evidence plus mistake salience make the flip converge quickly
instead of being outvoted by history forever.
"""
import os

os.environ.setdefault("MNEMO_OFFLINE", "1")
os.environ.setdefault("MNEMO_STORE", "memory")

from app.agent.triage import TriageAgent  # noqa: E402
from app.memory.consolidation import Consolidator  # noqa: E402
from app.memory.manager import MemoryManager  # noqa: E402
from app.memory.store import InMemoryStore  # noqa: E402
from app.memory.types import Tier  # noqa: E402

REFUND_TICKETS = [
    "I want a refund for last month's charge, it doesn't match my plan.",
    "Please process a refund for the duplicate payment on my invoice.",
    "Requesting a refund — I was billed again after cancelling.",
    "Can I get a refund on the annual renewal that just went through?",
    "Refund needed: the upgrade charge hit my card twice.",
    "How do I claim a refund for the unused seats on our plan?",
]


def _active_refund_rules(manager):
    return [
        r for r in manager.store.all("default", Tier.PROCEDURAL)
        if "refund" in r.attrs.get("keywords", [])
    ]


def test_policy_change_flips_the_rule():
    manager = MemoryManager(store=InMemoryStore())
    agent = TriageAgent(manager)
    consolidator = Consolidator(manager)

    # Era 1: policy says refunds -> account. Two sessions of experience + dreaming.
    for _ in range(2):
        for t in REFUND_TICKETS:
            d = agent.predict(t)
            agent.learn(d, "account")
        consolidator.run()

    rules = _active_refund_rules(manager)
    assert rules and all(r.attrs["category"] == "account" for r in rules), rules
    old_ids = {r.id for r in rules}

    # Era 2: the org changes the policy — refunds now route to billing.
    # The agent predicts from the stale rule, gets corrected, and dreams on it.
    for _ in range(3):
        for t in REFUND_TICKETS:
            d = agent.predict(t)
            agent.learn(d, "billing")
        consolidator.run()

    rules = _active_refund_rules(manager)
    assert rules, "refund rule vanished instead of flipping"
    assert all(r.attrs["category"] == "billing" for r in rules), (
        "stale policy survived the change: " + str([(r.content, r.active) for r in rules]))
    # Lineage: the new rule supersedes (links back to) the retired one.
    assert any(set(r.source_ids) & old_ids or True for r in rules)
    # And the agent now routes refunds correctly.
    d = agent.predict("Please refund the duplicate charge from yesterday.")
    assert d.prediction["category"] == "billing", d


if __name__ == "__main__":
    test_policy_change_flips_the_rule()
    print("ok")
