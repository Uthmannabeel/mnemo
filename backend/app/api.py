"""FastAPI surface for Mnemo — the deployable backend on Alibaba Cloud.

Endpoints:
  GET  /health                 liveness + which Qwen model / mode is live
  POST /triage                 predict a ticket's category (with provenance)
  POST /feedback               teach the agent the true category
  POST /consolidate            trigger a Dreaming pass (also a Function Compute cron)
  GET  /memory                 full tier snapshot (drives the dashboard)
  POST /seed                   populate the live store with one session of demo experience
  POST /eval                   run the 3-arm learning experiment (cached; drives the chart)
"""
from __future__ import annotations

import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

from . import __version__
from .agent.triage import CATEGORIES, TriageAgent
from .config import get_settings
from .memory.consolidation import Consolidator
from .memory.manager import MemoryManager
from .memory.types import Decision, Tier

# No CORS middleware on purpose: the dashboard is served same-origin by this app,
# and the mutating endpoints have no auth — don't invite cross-origin callers.
app = FastAPI(title="Mnemo", version=__version__)

_manager = MemoryManager()
_agent = TriageAgent(_manager, mode="full")
_consolidator = Consolidator(_manager)
_dream_lock = threading.Lock()  # one auto-Dreaming pass at a time


class TriageIn(BaseModel):
    ticket: str
    user_id: str = "default"


class FeedbackIn(BaseModel):
    ticket: str
    predicted_category: str
    true_category: str
    used_memory_ids: list[str] = []
    fired_memory_ids: list[str] = []  # rules that drove the call — from /triage's response
    user_id: str = "default"

    # Categories end up in stored attrs and rendered in the dashboard — reject
    # anything outside the known taxonomy at the boundary.
    @field_validator("predicted_category", "true_category")
    @classmethod
    def _known_category(cls, v: str) -> str:
        if v not in CATEGORIES:
            raise ValueError(f"unknown category {v!r}; expected one of {CATEGORIES}")
        return v


_STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/")
def landing() -> FileResponse:
    """Product landing page — the front door and the case for the product."""
    return FileResponse(_STATIC / "landing.html")


@app.get("/console")
def console() -> FileResponse:
    """The working console: triage, memory browser, evidence charts."""
    return FileResponse(_STATIC / "index.html")


@app.get("/evidence")
def evidence_page() -> FileResponse:
    """Deep dive: both experiments, methodology, CI invariants, reproduction."""
    return FileResponse(_STATIC / "evidence.html")


@app.get("/how")
def how_page() -> FileResponse:
    """Architecture: the four tiers, the Dreaming loop, the deployment topology."""
    return FileResponse(_STATIC / "how.html")


@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "version": __version__,
        "qwen_model": s.qwen_model,
        "store": s.mnemo_store,
        "mode": "offline-mock" if s.offline else "qwen-live",
    }


@app.post("/triage")
def triage(body: TriageIn) -> dict:
    d = _agent.predict(body.ticket, user_id=body.user_id)
    fired = set(d.fired_memory_ids)
    provenance = [
        {**m.to_public(), "fired": m.id in fired}
        for mid in d.used_memory_ids
        if (m := _manager.store.get(mid))
    ]
    return {
        "category": d.prediction["category"],
        "rationale": d.rationale,
        "provenance": provenance,
        "used_memory_ids": d.used_memory_ids,
        "fired_memory_ids": d.fired_memory_ids,  # echo back so /feedback can credit-assign
    }


@app.post("/feedback")
def feedback(body: FeedbackIn) -> dict:
    d = Decision(
        query=body.ticket,
        prediction={"category": body.predicted_category},
        used_memory_ids=body.used_memory_ids,
        fired_memory_ids=body.fired_memory_ids,
        rationale="",
    )
    _agent.learn(d, body.true_category, user_id=body.user_id)

    # Autonomy: once enough new experience has accumulated, dream on it automatically.
    # The trigger is derived from the store (unconsolidated episodes for THIS
    # workspace), not a process-local counter — so it stays correct per user, across
    # request threads, and across processes, same as the Function Compute cron.
    dreamed = None
    if _dream_lock.acquire(blocking=False):
        try:
            pending = len(_consolidator.pending_episodes(body.user_id))
            if pending >= get_settings().consolidation_every:
                dreamed = _consolidator.run(user_id=body.user_id)
        finally:
            _dream_lock.release()
    return {"ok": True, "dreamed": dreamed}


@app.post("/consolidate")
def consolidate(user_id: str = "default") -> dict:
    return _consolidator.run(user_id=user_id)


@app.get("/memory")
def memory(user_id: str = "default") -> dict:
    return _manager.snapshot(user_id=user_id)


class SeedIn(BaseModel):
    user_id: str = "default"
    # "standard": generic tickets, surface reading is truth (e.g. Globex).
    # "conventions": org-idiosyncratic routing policies (e.g. Northwind:
    #   refunds -> account managers, Falcon tickets -> the white-glove team...).
    profile: str = "standard"


_seed_lock = threading.Lock()
_SEED_EPISODE_CAP = 500  # abuse brake: an unauthenticated caller can't bloat a workspace


@app.post("/seed")
def seed(body: SeedIn | None = None) -> dict:
    """Populate a workspace's LIVE memory with two sessions of demo experience.

    Runs synthetic tickets through the real agent (predict → learn) with a Dreaming
    pass per session. Workspaces are isolated by user_id — seed two with different
    profiles and the same ticket routes differently in each, each citing its own
    learned rules. Distinct seeds from the benchmarks so this can't be mistaken
    for the experiments.

    Serialized (one run at a time) and capped per workspace: this endpoint is
    unauthenticated and, in live mode, each run spends real Qwen credits.
    """
    body = body or SeedIn()
    if not _seed_lock.acquire(blocking=False):
        raise HTTPException(429, "a seed run is already in progress; try again shortly")
    try:
        return _seed(body)
    finally:
        _seed_lock.release()


def _seed(body: SeedIn) -> dict:
    if len(_manager.store.all(body.user_id, Tier.EPISODIC)) >= _SEED_EPISODE_CAP:
        raise HTTPException(
            409, f"workspace '{body.user_id}' already holds {_SEED_EPISODE_CAP}+ episodes; not reseeding"
        )
    if body.profile == "conventions":
        from .eval.org_dataset import make_org_sessions

        sessions = [[(t, c) for t, c, _ in s] for s in make_org_sessions(2, 15, seed=97)]
    else:
        from .eval.dataset import make_sessions

        sessions = make_sessions(n_sessions=2, per_session=13, seed=99)

    seeded = correct = 0
    dreamed = {"procedural": 0, "semantic": 0, "episodes": 0}
    for session in sessions:
        for ticket, truth in session:
            d = _agent.predict(ticket, user_id=body.user_id)
            correct += int(d.prediction["category"] == truth)
            seeded += 1
            _agent.learn(d, truth, user_id=body.user_id)
        summary = _consolidator.run(user_id=body.user_id)
        for k in dreamed:
            dreamed[k] += summary.get(k, 0)
    return {"seeded": seeded, "correct": correct, "profile": body.profile, "dreamed": dreamed}


_eval_cache: dict[tuple[int, int, int], dict] = {}
_eval2_cache: dict[tuple[int, int, int], dict] = {}
_EVAL_CACHE_MAX = 16  # distinct param tuples worth keeping; beyond this, evict oldest


def _clamped(sessions: int, per_session: int, max_s: int, max_p: int) -> tuple[int, int]:
    # These are public, unauthenticated endpoints running CPU-bound work — clamp the
    # experiment size so a caller can't request an arbitrarily expensive run.
    return max(1, min(sessions, max_s)), max(1, min(per_session, max_p))


def _cached(cache: dict, key: tuple, compute) -> dict:
    if key not in cache:
        if len(cache) >= _EVAL_CACHE_MAX:
            cache.pop(next(iter(cache)))
        cache[key] = compute()
    return cache[key]


@app.post("/eval")
def eval_run(sessions: int = 8, per_session: int = 25, seed: int = 7) -> dict:
    """Run the 3-arm learning experiment. Deterministic + isolated + offline by design
    (see harness.run_arm), so results are cached — the dashboard can call this on every
    page load without recomputing or ever touching the Qwen API."""
    from .eval.harness import run

    sessions, per_session = _clamped(sessions, per_session, 12, 50)
    key = (sessions, per_session, seed)
    return _cached(_eval_cache, key, lambda: run(sessions, per_session, seed))


@app.post("/eval2")
def eval2_run(sessions: int = 5, per_session: int = 15, seed: int = 11) -> dict:
    """Experiment 2 (org conventions) for the dashboard chart. Always the deterministic
    offline pipeline + cached — same zero-credit policy as /eval. The live Qwen run is
    the CLI's job (`python -m app.eval.live_harness --yes`)."""
    from .eval.live_harness import run_experiment

    sessions, per_session = _clamped(sessions, per_session, 10, 30)
    key = (sessions, per_session, seed)
    return _cached(
        _eval2_cache, key, lambda: run_experiment(sessions, per_session, seed, force_offline=True)
    )
