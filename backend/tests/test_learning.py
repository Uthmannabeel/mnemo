"""Regression test for Mnemo's core claim: memory makes decisions more accurate.

Runs fully offline (deterministic heuristic + hashing embeddings), so CI needs no
API key. Asserts the ordering that defines the project:

    no-memory  <  episodic-RAG  <  Mnemo (episodic + Dreaming consolidation)

and that Mnemo's accuracy actually climbs across sessions.
"""
import os

os.environ.setdefault("MNEMO_OFFLINE", "1")
os.environ.setdefault("MNEMO_STORE", "memory")

from app.eval.harness import run  # noqa: E402


def test_memory_improves_accuracy():
    result = run(n_sessions=8, per_session=25, seed=7)
    none = result["arms"]["none"]
    episodic = result["arms"]["episodic"]
    full = result["arms"]["full"]

    # 1. Consolidation beats raw retrieval beats no memory.
    assert full["mean"] > episodic["mean"] > none["mean"], result

    # 2. The memoryless control does not learn (stays near chance for 5 classes).
    assert none["mean"] < 0.35, none

    # 3. Mnemo genuinely improves over sessions.
    assert full["last"] > full["first"], full
    assert full["improvement"] > 0.2, full

    # 4. The Dreaming loop actually produced distilled higher-tier memories.
    assert full["memory_counts"]["procedural"] > 0
    assert full["memory_counts"]["semantic"] > 0

    # 5. Token economics: Mnemo wins while consuming a SMALLER memory context
    #    than raw retrieval — signal per token, the answer to context rot.
    assert full["avg_context_chars"] < episodic["avg_context_chars"] * 0.8, (
        full["avg_context_chars"], episodic["avg_context_chars"])


if __name__ == "__main__":
    test_memory_improves_accuracy()
    print("ok")
