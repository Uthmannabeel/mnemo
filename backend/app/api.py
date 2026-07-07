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

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__
from .agent.triage import TriageAgent
from .config import get_settings
from .memory.consolidation import Consolidator
from .memory.manager import MemoryManager

app = FastAPI(title="Mnemo", version=__version__)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

_manager = MemoryManager()
_agent = TriageAgent(_manager, mode="full")
_consolidator = Consolidator(_manager)
_feedback_since_dream = 0  # auto-triggers a Dreaming pass every `consolidation_every`


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
    from .memory.types import Decision

    d = Decision(
        query=body.ticket,
        prediction={"category": body.predicted_category},
        used_memory_ids=body.used_memory_ids,
        fired_memory_ids=body.fired_memory_ids,
        rationale="",
    )
    _agent.learn(d, body.true_category, user_id=body.user_id)

    # Autonomy: once enough new experience has accumulated, dream on it automatically.
    # (The scheduled Function Compute cron is the production path; this makes a
    # standalone API self-improving too.)
    global _feedback_since_dream
    _feedback_since_dream += 1
    dreamed = None
    if _feedback_since_dream >= get_settings().consolidation_every:
        _feedback_since_dream = 0
        dreamed = _consolidator.run(user_id=body.user_id)
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


@app.post("/seed")
def seed(body: SeedIn | None = None) -> dict:
    """Populate a workspace's LIVE memory with two sessions of demo experience.

    Runs synthetic tickets through the real agent (predict → learn) with a Dreaming
    pass per session. Workspaces are isolated by user_id — seed two with different
    profiles and the same ticket routes differently in each, each citing its own
    learned rules. Distinct seeds from the benchmarks so this can't be mistaken
    for the experiments.
    """
    body = body or SeedIn()
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


@app.post("/eval")
def eval_run(sessions: int = 8, per_session: int = 25, seed: int = 7) -> dict:
    """Run the 3-arm learning experiment. Deterministic + isolated + offline by design
    (see harness.run_arm), so results are cached — the dashboard can call this on every
    page load without recomputing or ever touching the Qwen API."""
    from .eval.harness import run

    key = (sessions, per_session, seed)
    if key not in _eval_cache:
        _eval_cache[key] = run(sessions, per_session, seed)
    return _eval_cache[key]


_eval2_cache: dict[tuple[int, int, int], dict] = {}


@app.post("/eval2")
def eval2_run(sessions: int = 5, per_session: int = 15, seed: int = 11) -> dict:
    """Experiment 2 (org conventions) for the dashboard chart. Always the deterministic
    offline pipeline + cached — same zero-credit policy as /eval. The live Qwen run is
    the CLI's job (`python -m app.eval.live_harness --yes`)."""
    from .eval.live_harness import run_experiment

    key = (sessions, per_session, seed)
    if key not in _eval2_cache:
        _eval2_cache[key] = run_experiment(sessions, per_session, seed, force_offline=True)
    return _eval2_cache[key]
