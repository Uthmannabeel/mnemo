# Devpost submission — Mnemo

> **PRE-FLIGHT — do NOT paste this into Devpost until the three `<fill in>` links at
> the bottom are real URLs.** Stage 1 of judging is a literal completeness gate: a
> placeholder or dead link is an automatic rejection, unread.

**Track:** MemoryAgent

**Tagline (Devpost subtitle):** The memory layer that measurably learns your
organization — same model, 0% → 100%, live.

## Elevator pitch (one line)
Zero-shot Qwen3.7-Max scores 0% on decisions governed by your organization's private
conventions. With Mnemo the same model reaches 100% — increasingly accurate decisions
across cross-session interactions, measured live, every prediction committed for
audit — and distilled memory beats raw RAG on half the context per decision.

## Try it in 60 seconds (live on Alibaba Cloud)
1. Open http://47.84.232.162:8000/console (ECS Singapore, `/health` = `qwen-live`).
2. Workspace **Northwind** → paste *"Please refund my duplicate subscription charge."*
   → Triage. Surface reading says billing; Mnemo answers **account**, and the decision
   ledger cites the routing rule it wrote for itself from Northwind's feedback.
3. Switch to **Globex** (no such policy): the same ticket routes to **billing**.
   Same model — different learned memory, each decision fully auditable.

If the live box is ever unreachable or looks empty, the identical result reproduces
offline in ~2 seconds with no API key (`MNEMO_OFFLINE=1 python -m app.eval.harness`),
and every live prediction is committed at `backend/results/org_experiment.json`.

## Inspiration
Almost every "memory agent" is a chatbot wired to a vector store: it can recall the
past but never *learns* from it. Even the strong frameworks — mem0, Zep, Letta/MemGPT —
solve storage and recall, not measured improvement. We wanted an agent whose competence
visibly compounds with experience — and, crucially, a way to **measure** that instead
of just claiming it.

## What it does
Mnemo triages support tickets. Each ticket + outcome becomes a raw **episode**. An
autonomous **Dreaming loop** (Qwen3.7-Max) reflects on recent episodes and distils them
into **semantic facts** and **procedural rules**, which then steer future decisions.
Every decision is transparent and auditable: it cites the exact memory ids that
justified it, so a support lead can see *why* a ticket routed where it did — and
correct the rule, not just the ticket.

The problem this solves: in every support org, routing knowledge lives in veterans'
heads. Mnemo turns it into auditable, self-correcting rules — the value is fewer
misroutes and a halved memory-token bill per decision, both measured below.

## Track fit — the MemoryAgent brief, point by point
The track asks for three specific capabilities; each is implemented **and enforced by
a CI regression test** that fails the build if it stops working:
- *"Efficient memory storage and retrieval"* → four tiers with blended scoring
  (similarity + recency-decay + importance + confidence). Result: **50% smaller
  context per decision** than raw RAG, at higher accuracy.
- *"Timely forgetting of outdated information"* → confidence decay, recency-weighted
  consolidation (mistakes count double), supersede-on-conflict. Proof:
  `tests/test_adaptation.py` — a changed refund policy flips its own rule.
- *"Recalling critical memories within limited context windows"* → a hard
  per-decision retrieval budget of 6 memories, spent across tiers. Proof: **+10.5 pts
  over episodic RAG under the identical budget** (the ablation control below).
- *"Increasingly accurate decisions across multi-turn, cross-session interactions"*
  → the Dreaming loop consolidates between sessions. Proof: **14 → 71 → 86 → 100%**
  across sessions, live, real Qwen3.7-Max (the live result below).

Two controlled experiments back the claim:
- **The live result (does memory help Qwen itself? LIVE, real Qwen3.7-Max both
  arms):** tickets whose ground truth depends on *organization conventions no model can
  know a priori* (refunds route to account managers by policy; "Project Falcon" tickets
  go to the white-glove team…). That 0% is the controlled premise, not a gotcha — each
  convention ticket's surface reading points at the wrong queue by design, exactly the
  org-private knowledge no amount of pre-training can contain. Zero-shot Qwen3.7-Max:
  **98% on plain tickets, 0% on convention tickets four sessions straight** (14% in the
  fifth — never above one lucky guess). The same model with Mnemo: **14 → 71 → 86 →
  100%** (+86 pt final gap) while retaining **95% on plain tickets**. All five
  conventions distilled into readable rules with self-written rationales; every one of
  the 150 predictions committed to the repo for audit.
- **The ablation control (why distillation, not just retrieval — deterministic offline
  pipeline, model held constant, same code path the live model runs through):** under a
  fixed per-decision context budget, 21% (no memory) → 60% (episodic RAG) →
  **71% mean / 100% final** (Mnemo) — distilled rules beat raw retrieval when context
  is finite.
- **The economics, costed:** a misrouted ticket bounces between queues — industry
  help-desk benchmarks put one escalation at **$15–40 of agent time**. At 1,000
  convention-governed tickets a month, going from 0% to 100% on those decisions removes
  ~1,000 misroutes — **five figures of monthly triage waste** — while Mnemo's memory
  context is **half the size per decision** (574 vs 1,155 chars measured, roughly half
  the tokens), halving the per-decision spend on memory payload.
- **Also test-enforced:** **unlearning** — a changed org policy supersedes its stale
  rule within a few corrections; and **isolated workspaces** — the same ticket routes
  differently in two orgs, each citing its own learned policy.

## What's novel
Memory frameworks solve storage and recall. Mnemo's contribution is not the tier
diagram — it is the measured, enforced learning loop:
- **A test-enforced learning curve** — CI fails the build if consolidation ever stops
  beating retrieval on the deterministic pipeline.
- **Measured unlearning** — a changed policy must overturn its own stale rule, or the
  build fails.
- **Fully autonomous consolidation** — the Dreaming loop distils rules with no human
  approving the merge, and every decision cites the exact memory ids that justified
  it, so autonomy never costs auditability.

## How we built it (technical depth)
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
- **Proof, not vibes**: a three-arm ablation harness + regression tests that fail the
  build if the memory pipeline stops improving accuracy (run on the deterministic
  offline path — the same code the live model executes).

## Challenges we ran into
Our first "ablation" still hit 100% because raw k-NN over near-duplicate tickets was
trivially easy — which would have made the memory look pointless. We redesigned the
experiment around a **finite context budget** and **noisy, realistic tickets**, which
is exactly the regime where distilled rules beat raw recall — the "context rot" effect
Chroma Research documented in 2025: model performance degrades as input context grows,
so what you put in the window matters more than how much you can fit.

## Accomplishments we're proud of
Two controlled, reproducible experiments — the ablation runs in 2 seconds offline, no
API key — showing consolidation beats retrieval by +10.5 pts under an identical budget,
and that Mnemo teaches Qwen3.7-Max org knowledge no model could know zero-shot. Both
are locked behind regression tests that fail the build if the learning curve ever
flattens (deterministic offline path, same code the live model runs through).

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
- Alibaba Cloud services/API usage in code (required with the proof):
  https://github.com/Uthmannabeel/mnemo/blob/main/backend/app/qwen_client.py
  (Qwen3.7-Max + Qwen embeddings via Model Studio) and
  https://github.com/Uthmannabeel/mnemo/blob/main/backend/fc_dream.py
  (Function Compute handler)
- Blog post (Blog Post Award): <published url — fill in>
