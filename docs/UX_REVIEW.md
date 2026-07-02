# Mnemo — code optimization & UX review

*Full-codebase optimization pass + walkthrough of every major user path.
Items marked ✅ were fixed in the same change as this report; 📋 are deferred with rationale.*

---

## Part 1 — Code review: optimizations & correctness

### ✅ Fixed

**1. `/eval` was a cost bomb on live deployments (critical).**
The dashboard auto-runs the benchmark on every page load. With a real API key, each run
= 3 arms × 200 predictions × (embedding + chat) + consolidations ≈ **700+ Qwen calls per
page view**. Fixes: the benchmark now *always* runs on a `force_offline` QwenClient
(it is deterministic and free by design — that's the point of it), and `/eval` results
are cached server-side. Second call returns in <100 ms.

**2. Feedback credit-assignment was broken over the API (critical).**
`learn()` reinforces `Decision.fired_memory_ids`, but `/feedback` built its `Decision`
without them — so **no API-driven feedback ever reinforced a rule**. The eval harness
masked this because it calls `learn()` in-process. Fixes: `/triage` now returns
`fired_memory_ids` (and marks provenance items `"fired": true`); `/feedback` accepts and
threads them through. Covered by a new test (`tests/test_api.py`) that asserts
confidence actually rises after positive feedback.

**3. Embedding calls: no retry, no cache, order assumption.**
`chat()` had tenacity retry but `embed()` — the *more frequent* call — didn't. Added the
same retry, an LRU cache on `embed_one()` (saves credits + latency on repeated queries),
and results are sorted by `.index` instead of assuming server ordering.

**4. Client injection instead of hidden singletons.**
`MemoryManager` now accepts a `QwenClient`; `TriageAgent`/`Consolidator` inherit the
manager's client. One consistent client per pipeline, and the benchmark can pin
offline without env-var hacks.

### 📋 Deferred (documented, not blocking)

- **`Consolidator` loads all episodes via `store.all()`** — on Postgres this fetches
  every episode *with embeddings* per Dreaming pass. Fine at demo scale; at production
  scale, push the `consolidated` filter into SQL (`WHERE attrs->>'consolidated' IS NULL`)
  and skip the embedding column. ~10 lines when needed.
- **`_commit` conflict-resolution is O(rules²) per pass** — irrelevant below ~10k rules.
- **`PostgresStore` uses one shared connection** — FastAPI's threadpool serializes on
  it. Correct (autocommit, no shared cursors) but a `psycopg_pool.ConnectionPool` is the
  right move if the demo ever takes concurrent traffic. Deliberately not done now: more
  moving parts before a deadline, zero demo benefit.
- **`retrieve()` writes a `touch()` update per retrieved memory per decision** — up to 6
  UPDATEs/request on Postgres. Could batch into one statement. Demo-scale fine.

---

## Part 2 — UX walkthrough: every user path

### Path A — Judge lands on the dashboard
**Before:** chart auto-draws (good hook) — but the memory tiers below said `empty`,
while the chart's stat line mentions "72 procedural rules." **Confusion: "where are
these rules?"** The benchmark runs on an *isolated* store; the live tiers are separate,
and nothing explained that.
**✅ Fixed:** a note under the chart says the benchmark is isolated/deterministic/free,
and the tiers panel now has **⚡ Seed demo data** — one click runs 25 tickets through
the *live* agent + a Dreaming pass, filling all three tiers with real distilled rules.

### Path B — Triage a ticket (cold start)
**Before:** prediction appears with "no memory used yet" — a dead end. Nothing tells the
user why it guessed or what to do next.
**✅ Fixed:** empty-provenance message now says "the agent guessed. Teach it below," and
empty tier panels point at Seed/feedback. Cold start is now a *story beat* (watch it be
dumb, then teach it) instead of a bug-looking state.

### Path C — Teach the agent (THE core loop)
**Before: the single biggest gap.** Mnemo's whole pitch is "learns from feedback across
sessions" — and the UI had **no way to give feedback**. The learning loop existed only
for curl users. A judge could never experience the product's thesis.
**✅ Fixed:** after every prediction, a feedback row renders: **✓ Correct (billing)**
plus one button per other category. Clicking posts `/feedback` (with the fired-rule ids
— see bug #2), confirms "Reinforced ✓ / Corrected → X ✓ — episode written," notes when
an automatic Dreaming pass fired, and refreshes the tiers so the episodic count visibly
ticks up. The learning loop is now a 5-second on-camera moment.

### Path D — Watch it learn (consolidation)
**Before:** the "Dreaming loop" — the most differentiating feature — had **no UI
trigger**. `/consolidate` was curl-only; on a fresh store a user would wait forever to
see rules appear.
**✅ Fixed:** **💤 Dream now** button with a result readout ("reflected on 12 episodes →
+3 procedural, +1 semantic"), and a helpful message when there's nothing new to
consolidate. Provenance cards also badge **● fired** so users see *which* rule decided.

### Path E — Developer clones the repo
README quickstart works offline in ~2s — good. **📋 Remaining friction:** commands are
bash-syntax (`MNEMO_OFFLINE=1 python ...`); Windows users need `$env:`. Add a PowerShell
variant block to the README (one-line fix, listed in Part 3).

### Path F — Judge verifies the Alibaba deployment
`/health` returning `mode: qwen-live` vs `offline-mock` is exactly the right proof
surface. **📋 Watch-out:** during the live demo recording, if the key/env fails to load,
the header quietly shows `offline-mock` — double-check it on camera *before* recording
(already in DEPLOY.md's verify step; /deploy-check gates it too).

### Path G — Recording the demo video
**Before:** demo-prep skill had a broken seeding one-liner.
**✅ Fixed:** now just "click ⚡ Seed demo data," and the shot list includes the new
feedback moment (Path C) — the strongest new footage: *teach it wrong → watch it
correct itself.*

---

## Part 3 — Recommended next actions (in order)

1. **(2 min)** Add a PowerShell variant of the quickstart to README (Path E).
2. **(during deploy)** Keep `/health` on screen when recording — the `qwen-live` +
   `store: postgres` frame *is* the deployment proof (Path F).
3. **(post-hackathon)** Connection pool + SQL-side consolidation filter if Mnemo takes
   real traffic (Part 1 deferred items).

## Verification
- `tests/test_learning.py` — invariant green: no-memory 21% < episodic 60% < Mnemo 71%/100%.
- `tests/test_api.py` (new) — seed → fired-rule provenance → feedback reinforcement →
  eval cache, all asserted.
- Benchmark numbers unchanged and deterministic across processes.
