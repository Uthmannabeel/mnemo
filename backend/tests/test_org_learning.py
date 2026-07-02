"""Regression test for Experiment 2: org conventions are learnable from experience.

Offline pipeline test (deterministic mock — the live run swaps in Qwen3.7-Max on the
same code path). Asserts the properties the experiment's claim rests on:

  1. every org convention is distilled into a correct procedural rule,
  2. the memory arm's convention accuracy climbs across sessions,
  3. the memory arm beats the no-memory arm on convention tickets.
"""
import os

os.environ.setdefault("MNEMO_OFFLINE", "1")
os.environ.setdefault("MNEMO_STORE", "memory")

from app.eval.live_harness import run_experiment  # noqa: E402

MARKERS = {
    "falcon": "technical",
    "refund": "account",
    "acme": "shipping",
    "beta": "feedback",
    "purchase": "billing",
}


def test_org_conventions_are_learned():
    r = run_experiment(n_sessions=5, per_session=15, seed=11)
    alone = r["arms"]["qwen-alone"]
    mnemo = r["arms"]["qwen+mnemo"]

    # 1. All five conventions distilled, each with the *org's* category (not surface).
    rules = mnemo["distilled_rules"]
    for marker, category in MARKERS.items():
        assert any(
            f"'{marker}'" in rule and f"category={category}" in rule for rule in rules
        ), f"convention '{marker}' -> {category} was not distilled; rules: {rules}"

    # 2. Experience accumulates: convention accuracy climbs.
    assert mnemo["convention_last"] > mnemo["convention_first"], mnemo
    assert mnemo["convention_last"] >= 0.5, mnemo

    # 3. Memory beats no-memory where knowledge is org-specific.
    assert mnemo["convention_mean"] > alone["convention_mean"], r["headline"]
    assert r["headline"]["convention_gap_last_session"] > 0.2, r["headline"]


if __name__ == "__main__":
    test_org_conventions_are_learned()
    print("ok")
