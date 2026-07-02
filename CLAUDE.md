# Mnemo — Claude Code project guide

Self-improving memory agent for the Qwen Cloud hackathon (**MemoryAgent track**).
Four-tier cognitive memory + an autonomous "Dreaming" consolidation loop powered by
Qwen3.7-Max. Deployed on Alibaba Cloud. Full story in [README.md](README.md).

## The invariant (do not break this)
Mnemo's entire thesis is that **memory makes decisions measurably more accurate**. The
regression test encodes it:

```
no-memory (≈chance)  <  episodic-RAG  <  Mnemo (episodic + Dreaming)
```

`backend/tests/test_learning.py` fails the build if that ordering ever breaks or if the
accuracy curve stops climbing. The `test-guardian` hook runs it automatically when core
memory/agent/eval code changes. If you touch retrieval, consolidation, or the agent,
keep this green.

## Run it (all offline — no API key needed)
```powershell
cd backend
pip install -r requirements.txt
$env:MNEMO_OFFLINE=1; $env:MNEMO_STORE="memory"
python -m tests.test_learning          # regression test
python -m app.eval.harness             # 3-arm accuracy comparison
uvicorn app.api:app --reload           # API + dashboard at http://localhost:8000
```

`MNEMO_OFFLINE=1` swaps in a deterministic hashing-embedding + statistical distiller so
the **exact same code paths** run without spending Qwen credits. Set `MNEMO_OFFLINE=0`
with a `DASHSCOPE_API_KEY` to run live Qwen3.7-Max reasoning + Qwen embeddings.

## Architecture (where things live)
```
backend/app/
  qwen_client.py        Qwen/DashScope wrapper (+ offline mock). Online path only in chat().
  memory/
    types.py            tiered memory data model (Tier enum, MemoryRecord, Decision)
    store.py            InMemoryStore (dev) + PostgresStore (pgvector on RDS)
    manager.py          retrieval scoring (sim + recency-decay + importance + confidence)
    consolidation.py    the Dreaming loop — reflect, promote, decay, conflict-resolve
  agent/triage.py       TriageAgent — predicts with memory, learns from feedback
  eval/                 synthetic dataset + 3-arm experiment (harness.py)
  api.py                FastAPI surface; serves the dashboard at "/"
  static/index.html     Chart.js dashboard (accuracy curve, live triage, memory tiers)
fc_dream.py             Function Compute handler for the scheduled Dreaming cron
```

## Conventions
- **Offline-first**: every feature must work with `MNEMO_OFFLINE=1`. Online is the same
  code path with Qwen swapped in — never fork behavior between modes beyond the client.
- **Retrieval is budgeted**: decisions look at a *finite* number of memories (`_BUDGET`
  in `agent/triage.py`). The whole result depends on this — don't quietly lift it.
- **Provenance always**: a `Decision` records the memory ids that justified it. Keep it.
- **Consolidation is stateless across processes**: the "consolidated" flag lives in the
  store (not process memory) so the ECS API and FC cron share state over RDS.
- Style: standard library + type hints, module docstrings explain *why*. Match the
  existing tone — concise, no ceremony.

## Deployment
Alibaba Cloud: FastAPI on ECS/Function Compute, pgvector on RDS for PostgreSQL, Dreaming
loop as a scheduled FC job. Live deploys **require** `MNEMO_STORE=postgres` so the API
and cron share memory. Full steps: [docs/DEPLOY.md](docs/DEPLOY.md). Verify the exact
Qwen model id (`qwen3.7-max`) and embedding model against the Model Studio console for
your region before going live.

## Security
- Never commit `.env` (it holds `DASHSCOPE_API_KEY`). Only `.env.example` is tracked.
- Don't hardcode the RDS `DATABASE_URL` or API keys in source or docs.
