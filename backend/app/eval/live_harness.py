"""Experiment 2 — does memory help *Qwen itself*?

Two arms, identical org-idiosyncratic tickets (see org_dataset.py):

  qwen-alone   Qwen3.7-Max zero-shot — no memory context at all
  qwen+mnemo   the same model, thinking with Mnemo's memory; Dreaming consolidation
               (Qwen3.7-Max reflection) runs between sessions

Hypothesis: a frontier model aces the PLAIN tickets without help, but *cannot* know
Northwind's org conventions a priori — so the alone arm fails the convention subset
forever, while the memory arm learns the conventions from feedback and closes the gap.
That is the claim that survives the "wouldn't the model alone ace this?" question.

Cost safety: a live run makes real Qwen calls, so it prints an estimate and requires
--yes. Offline (MNEMO_OFFLINE=1) it runs the deterministic pipeline test for free —
same code path, mock client — which is what CI exercises.

Results are checkpointed to JSON after every session (a mid-run failure loses nothing)
and are meant to be committed to the repo so judges can inspect a real run without
re-spending credits:

    python -m app.eval.live_harness --yes            # live (needs DASHSCOPE_API_KEY)
    python -m app.eval.live_harness                  # offline pipeline test
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..agent.triage import TriageAgent
from ..memory.consolidation import Consolidator
from ..memory.manager import MemoryManager
from ..memory.store import InMemoryStore
from ..memory.types import Tier
from ..qwen_client import get_qwen
from .org_dataset import make_org_sessions

ARMS = [("none", "qwen-alone"), ("full", "qwen+mnemo")]


def _estimate_calls(n_sessions: int, per_session: int) -> int:
    # chat: 2 arms x tickets, + 1 reflection per session (memory arm only)
    return 2 * n_sessions * per_session + n_sessions


def run_experiment(
    n_sessions: int = 5,
    per_session: int = 15,
    seed: int = 11,
    out: str | None = None,
    force_offline: bool = False,
) -> dict:
    """force_offline pins the deterministic mock client — used by the dashboard's
    /eval2 endpoint so a page view can never spend API credits (same policy as /eval)."""
    from ..qwen_client import QwenClient

    qwen = QwenClient(force_offline=True) if force_offline else get_qwen()
    result: dict = {
        "experiment": "org-conventions: qwen-alone vs qwen+mnemo",
        "mode": "offline-pipeline-test" if qwen.offline else "live-qwen",
        "model": qwen.s.qwen_model,
        "sessions": n_sessions,
        "per_session": per_session,
        "seed": seed,
        "arms": {},
    }

    for mode, label in ARMS:
        manager = MemoryManager(store=InMemoryStore(), qwen=qwen)
        agent = TriageAgent(manager, mode=mode)
        consolidator = Consolidator(manager)
        sessions = make_org_sessions(n_sessions, per_session, seed)

        arm: dict = {"per_session": [], "predictions": []}
        result["arms"][label] = arm
        for s_idx, session in enumerate(sessions):
            tally = {"conv": [0, 0], "plain": [0, 0]}  # [correct, total]
            for text, truth, is_conv in session:
                d = agent.predict(text)
                ok = d.prediction["category"] == truth
                agent.learn(d, truth)
                key = "conv" if is_conv else "plain"
                tally[key][0] += int(ok)
                tally[key][1] += 1
                arm["predictions"].append(
                    {"session": s_idx + 1, "ticket": text, "truth": truth,
                     "predicted": d.prediction["category"], "convention": is_conv}
                )
            if mode == "full":
                consolidator.run()  # the Dreaming pass — live: Qwen3.7-Max reflection
            arm["per_session"].append({
                "session": s_idx + 1,
                "convention_acc": round(tally["conv"][0] / max(tally["conv"][1], 1), 4),
                "plain_acc": round(tally["plain"][0] / max(tally["plain"][1], 1), 4),
            })
            if out:  # checkpoint after every session — a dropped run loses nothing
                Path(out).parent.mkdir(parents=True, exist_ok=True)
                Path(out).write_text(json.dumps(result, indent=2), encoding="utf-8")

        rows = arm["per_session"]
        arm["convention_first"] = rows[0]["convention_acc"]
        arm["convention_last"] = rows[-1]["convention_acc"]
        arm["convention_mean"] = round(sum(r["convention_acc"] for r in rows) / len(rows), 4)
        arm["plain_mean"] = round(sum(r["plain_acc"] for r in rows) / len(rows), 4)
        if mode == "full":
            rules = manager.store.all("default", Tier.PROCEDURAL)
            rules.sort(key=lambda r: (-r.confidence, r.content))  # corroborated org rules first
            arm["distilled_rules"] = [r.content for r in rules]

    a, m = result["arms"]["qwen-alone"], result["arms"]["qwen+mnemo"]
    result["headline"] = {
        "convention_gap_last_session": round(m["convention_last"] - a["convention_last"], 4),
        "alone_convention_mean": a["convention_mean"],
        "mnemo_convention_mean": m["convention_mean"],
    }
    if out:
        Path(out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _print_table(r: dict) -> None:
    print(f"\n=== Experiment 2: does memory help Qwen itself? [{r['mode']}] ===")
    print(f"model={r['model']}  {r['sessions']} sessions x {r['per_session']} tickets "
          f"(half org-convention, half plain)\n")
    header = "                        " + "".join(f"   S{i+1}" for i in range(r["sessions"]))
    print("convention-ticket accuracy (the org knowledge no model can guess):")
    print(header)
    for label in ("qwen-alone", "qwen+mnemo"):
        row = "".join(f"{s['convention_acc']*100:5.0f}" for s in r["arms"][label]["per_session"])
        print(f"  {label:<20}{row}   mean {r['arms'][label]['convention_mean']*100:4.0f}%")
    print("\nplain-ticket accuracy (surface reading is enough):")
    for label in ("qwen-alone", "qwen+mnemo"):
        print(f"  {label:<20} mean {r['arms'][label]['plain_mean']*100:4.0f}%")
    h = r["headline"]
    print(f"\n  final-session convention gap (mnemo - alone): "
          f"{h['convention_gap_last_session']*100:+.0f} pts")
    rules = r["arms"]["qwen+mnemo"].get("distilled_rules", [])
    print(f"  org rules Mnemo distilled: {len(rules)}")
    for rule in rules[:6]:
        print(f"    · {rule}")
    if r["mode"] == "offline-pipeline-test":
        print("\n  NOTE: offline pipeline test (deterministic mock). Run with a real "
              "DASHSCOPE_API_KEY and --yes for the live Qwen3.7-Max result.")
    print()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--sessions", type=int, default=5)
    p.add_argument("--per-session", type=int, default=15)
    p.add_argument("--seed", type=int, default=11)
    p.add_argument("--out", default="results/org_experiment.json")
    p.add_argument("--yes", action="store_true", help="confirm a LIVE (credit-spending) run")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    qwen = get_qwen()
    if not qwen.offline and not args.yes:
        est = _estimate_calls(args.sessions, args.per_session)
        print(f"LIVE run: ~{est} Qwen chat calls (+embeddings) against {qwen.s.qwen_model}. "
              f"Re-run with --yes to confirm, or set MNEMO_OFFLINE=1 for the free pipeline test.")
        sys.exit(1)

    result = run_experiment(args.sessions, args.per_session, args.seed, args.out)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_table(result)
        print(f"  results checkpointed to {args.out}\n")


if __name__ == "__main__":
    main()
