"""Replay multi-session interactions and measure accuracy per session.

Three arms, same tickets, same finite retrieval budget per decision:

  none      memoryless control        — should sit near cold-start (no learning)
  episodic  raw-RAG baseline          — retrieves past tickets only, no consolidation
  full      Mnemo                     — Dreaming distils episodes into procedural rules

Headline claim: under a *fixed* per-decision context budget, Mnemo converges faster
and higher than raw episodic retrieval, because a handful of distilled rules carry
more signal than the same number of noisy raw tickets ("context rot"). The emitted
JSON drives the dashboard chart.

Run:
    python -m app.eval.harness              # compare all three arms (table)
    python -m app.eval.harness --json       # machine-readable, feeds the dashboard
"""
from __future__ import annotations

import argparse
import json
import sys

from ..agent.triage import TriageAgent
from ..memory.consolidation import Consolidator
from ..memory.manager import MemoryManager
from ..memory.store import InMemoryStore
from ..qwen_client import QwenClient
from .dataset import make_sessions


def run_arm(mode: str, n_sessions: int, per_session: int, seed: int) -> dict:
    # Fresh, isolated store per arm so results are reproducible + independent.
    # force_offline: the benchmark is deterministic and free BY DESIGN — it must never
    # burn API credits, even on a live deployment (the dashboard calls /eval on load).
    manager = MemoryManager(store=InMemoryStore(), qwen=QwenClient(force_offline=True))
    agent = TriageAgent(manager, mode=mode)
    consolidator = Consolidator(manager)
    sessions = make_sessions(n_sessions, per_session, seed)

    acc_by_session: list[float] = []
    for session in sessions:
        correct = 0
        for ticket, truth in session:
            decision = agent.predict(ticket)
            if decision.prediction["category"] == truth:
                correct += 1
            agent.learn(decision, truth)  # writes the episode (all arms)
        acc_by_session.append(round(correct / len(session), 4))
        # Only the full arm dreams; that is the sole difference between full & episodic.
        if mode == "full":
            consolidator.run()

    snap = manager.snapshot()
    return {
        "mode": mode,
        "accuracy_by_session": acc_by_session,
        "first": acc_by_session[0],
        "last": acc_by_session[-1],
        "improvement": round(acc_by_session[-1] - acc_by_session[0], 4),
        "mean": round(sum(acc_by_session) / len(acc_by_session), 4),
        "memory_counts": {tier: len(items) for tier, items in snap.items()},
    }


def run(n_sessions: int = 8, per_session: int = 25, seed: int = 7) -> dict:
    arms = {m: run_arm(m, n_sessions, per_session, seed) for m in ("none", "episodic", "full")}
    return {"sessions": n_sessions, "per_session": per_session, "seed": seed, "arms": arms}


def _bar(acc: float, peak: float = 1.0) -> str:
    return "#" * int(round(acc / (peak or 1.0) * 32))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--sessions", type=int, default=8)
    p.add_argument("--per-session", type=int, default=25)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    result = run(args.sessions, args.per_session, args.seed)
    if args.json:
        print(json.dumps(result, indent=2))
        return

    labels = {"none": "no-memory ", "episodic": "episodic  ", "full": "MNEMO     "}
    print(f"\n=== Mnemo eval — {result['sessions']} sessions x {result['per_session']} tickets ===\n")
    header = "session:  " + "".join(f"{i+1:>5}" for i in range(result["sessions"]))
    print(header)
    for mode in ("none", "episodic", "full"):
        arm = result["arms"][mode]
        row = "".join(f"{a*100:5.0f}" for a in arm["accuracy_by_session"])
        print(f"{labels[mode]} {row}   mean {arm['mean']*100:4.0f}%")
    print()
    for mode in ("none", "episodic", "full"):
        arm = result["arms"][mode]
        print(f"  {labels[mode]} last {arm['last']*100:5.1f}%  {_bar(arm['last'])}")
    full, epi = result["arms"]["full"], result["arms"]["episodic"]
    print(
        f"\n  Mnemo vs episodic-RAG:  +{(full['mean']-epi['mean'])*100:.1f} pts mean accuracy"
        f"  |  distilled rules: {full['memory_counts']['procedural']} procedural,"
        f" {full['memory_counts']['semantic']} semantic\n"
    )


if __name__ == "__main__":
    sys.exit(main())
