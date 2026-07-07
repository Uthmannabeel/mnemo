# Devpost submission — Mnemo

**Track:** MemoryAgent

## Elevator pitch (one line)
Frontier models can't know your organization — Mnemo makes Qwen3.7-Max learn it,
measurably, with a human-like four-tier memory that distils experience into rules.

## Inspiration
Almost every "memory agent" is a chatbot wired to a vector store: it can recall the
past but never *learns* from it. We wanted an agent whose competence visibly compounds
with experience — and, crucially, a way to **measure** that instead of just claiming it.

## What it does
Mnemo triages support tickets. Each ticket + outcome becomes a raw **episode**. An
autonomous **Dreaming loop** (Qwen3.7-Max) reflects on recent episodes and distils them
into **semantic facts** and **procedural rules**, which then steer future decisions.
Every decision is explainable and cites the exact memories that justified it.

Two controlled experiments back the claim:
- **Exp 1 (architecture ablation):** under a fixed per-decision context budget,
  21% (no memory) → 60% (episodic RAG) → **71% mean / 100% final** (Mnemo) — distilled
  rules beat raw retrieval when context is finite.
- **Exp 2 (does memory help Qwen itself? — LIVE, real Qwen3.7-Max both arms):**
  tickets whose ground truth depends on *organization conventions no model can know a
  priori* (refunds route to account managers by policy; "Project Falcon" tickets go to
  the white-glove team…). Zero-shot Qwen3.7-Max: **98% on plain tickets, 0% on
  convention tickets for four straight sessions**. The same model with Mnemo: **100%
  by session 4** (+86 pt final gap). All five conventions distilled into readable
  rules with self-written rationales; every one of the 150 predictions committed to
  the repo for audit.
- **Also test-enforced:** 50% smaller memory context per decision than raw RAG (token
  economics); **unlearning** — a changed org policy supersedes its stale rule within a
  few corrections; and **isolated workspaces** — the same ticket routes differently in
  two orgs, each citing its own learned policy.

## How we built it
- **Four-tier memory** (working / episodic / semantic / procedural), modelled on human
  cognition, with retrieval that blends similarity, recency-decay, importance and
  confidence.
- **Dreaming consolidation loop** — Qwen3.7-Max reflects over episodes, promotes durable
  knowledge upward, does **credit assignment**, **conflict resolution**, and **decay**.
- **Qwen Cloud**: Qwen3.7-Max + Qwen embeddings via the Model Studio
  OpenAI-compatible endpoint (`preserve_thinking` for coherent agent reasoning).
- **Alibaba Cloud**: live on an ECS instance in Singapore (Docker, FastAPI —
  http://47.84.232.162:8000). The store abstraction also ships a pgvector-on-RDS
  backend, and the Dreaming loop ships as a Function Compute handler
  (`fc_dream.py`) for scheduled consolidation in production.
- **Proof, not vibes**: a three-arm ablation harness + a regression test that fails if
  memory ever stops improving accuracy.

## Challenges we ran into
Our first "ablation" still hit 100% because raw k-NN over near-duplicate tickets was
trivially easy — which would have made the memory look pointless. We redesigned the
experiment around a **finite context budget** and **noisy, realistic tickets**, which
is exactly the regime where distilled rules beat raw recall (the "context rot" problem).

## Accomplishments we're proud of
Two controlled, reproducible experiments — the ablation runs in 2 seconds offline, no
API key — showing consolidation beats retrieval by +10.5 pts under an identical budget,
and that Mnemo teaches Qwen3.7-Max org knowledge no model could know zero-shot. Both
are locked behind regression tests that fail the build if learning ever stops.

## What we learned
Memory *architecture* matters more than memory *size*: a few high-signal distilled rules
outperform a large pile of raw episodes when context is finite.

## What's next
Multi-user memory isolation, procedural-rule promotion into callable tools, and porting
the Dreaming loop to Qwen3.7-Max's thousand-step long-horizon execution.

## Built with
`python` · `qwen3.7-max` · `dashscope` · `qwen-embeddings` · `fastapi` ·
`alibaba-cloud-ecs` · `alibaba-cloud-model-studio` · `pgvector` · `docker` · `chart.js`

## Links
- Repo: https://github.com/Uthmannabeel/mnemo (MIT license)
- Architecture diagram: docs/architecture.svg + docs/architecture.png (Devpost gallery)
- Live product (landing + console): http://47.84.232.162:8000 — Alibaba Cloud ECS, Singapore
- Demo video (~3 min): <youtube url — fill in>
- Proof-of-deployment recording: <url — fill in>
