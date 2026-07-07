# Stop bolting vector databases to chatbots: build an agent that actually *learns*

*How we built Mnemo — a memory agent with a human-like four-tier architecture — and
proved, with a controlled experiment, that distilling experience beats hoarding it.*

---

Ask ten teams to build a "memory agent" and nine will hand you the same thing: a
chatbot with a vector database stapled to its side. Every message gets embedded and
stashed; before each reply, the top-k most similar snippets are pulled back into the
prompt. It feels like memory. It demos well.

But it isn't learning. It's a filing cabinet with good search. The agent that answered
your 500th ticket is exactly as capable as the one that answered your first — it just
has more paper to rummage through. And more paper is not obviously better: a bigger,
noisier context is the very thing that gives modern LLMs *context rot*.

We wanted something different for the **Qwen Cloud MemoryAgent track**: an agent whose
competence *compounds* with experience — and, just as important, a way to **measure**
that instead of gesturing at it in a demo. We called it **Mnemo**.

This post is the honest version of how we built it, including the moment our own
experiment told us we were wrong.

---

## The idea: memory should have tiers, like yours does

Human memory isn't one bucket. Cognitive scientists carve it roughly into:

- **Working memory** — the handful of things you're holding right now.
- **Episodic memory** — specific events. *"On Tuesday a customer was charged twice."*
- **Semantic memory** — distilled facts. *"Duplicate-charge complaints are usually billing."*
- **Procedural memory** — skills and rules you run without re-deriving. *"Refund requests → billing queue."*

The magic isn't any single tier — it's the **flow between them**. You live through
episodes, and while you sleep your brain consolidates the useful ones into durable
semantic and procedural knowledge, and lets the rest fade.

Mnemo copies this directly. Four tiers:

| Tier | Holds | Written by | Read for |
|------|-------|-----------|----------|
| Working | current session | the live turn | reasoning |
| Episodic | raw events | every decision + outcome | grounding |
| Semantic | distilled facts | the *Dreaming* loop | fast context |
| Procedural | learned `IF…THEN` rules | the *Dreaming* loop | steering decisions |

Every ticket the agent handles is written as a raw **episode**. Then a background
process we call the **Dreaming loop** — powered by **Qwen3.7-Max** — periodically
reflects on recent episodes and *promotes* what's durable up into the semantic and
procedural tiers. That's the sentence the track literally asks for: an agent that
"autonomously accumulates experience."

```python
# The Dreaming loop, in spirit: reflect over raw episodes, distil durable knowledge.
def run(self, user_id="default"):
    episodes = self._recent_unconsolidated(user_id)
    result = self._reflect_online(episodes)   # Qwen3.7-Max returns structured insights
    for item in result["procedural"]:
        self._commit(user_id, item, Tier.PROCEDURAL)  # with conflict-resolution + decay
    for item in result["semantic"]:
        self._commit(user_id, item, Tier.SEMANTIC)
```

Consolidation isn't just an INSERT. It does three grown-up things:

- **Credit assignment** — a rule that drove a *correct* decision gains confidence; one
  that drove a wrong call loses it, and below a threshold it deactivates. Trust tracks
  reality.
- **Conflict resolution** — a refined rule *supersedes* an outdated one (keeping a
  provenance link) instead of piling up near-duplicates.
- **Decay** — memories that go unused fade in retrieval weight over a half-life.

And every decision is **explainable**: it records the exact memory ids that justified
it, so you can always answer "why did you route this to billing?"

---

## Retrieval that isn't just cosine similarity

Raw similarity is a blunt instrument. Mnemo re-ranks candidate memories with a blend:

```
score = 0.60·similarity + 0.15·recency(decay) + 0.15·importance + 0.10·confidence
```

So a slightly-less-similar but high-confidence, recently-useful procedural rule can —
correctly — beat a very-similar but stale raw episode. Under a **finite context
budget** (you can only fit so much in a prompt), *what* you retrieve matters more than
*how much*.

Hold onto that phrase — "finite context budget" — because it's where the story turns.

---

## The part where we were wrong

Here's the trap we walked into, and I think most memory-agent demos quietly live inside
it.

Our first evaluation compared "memory on" vs "memory off" on a synthetic support-ticket
stream. Memory on climbed to 100% accuracy. Great! Except… so did memory off.

The dataset was too easy. Our tickets were near-duplicates of a few templates, so a
plain k-nearest-neighbours lookup over raw episodes trivially aced it. Our fancy
consolidation was decorative. A senior engineer judging this would see through it in
about four seconds.

The fix wasn't to make memory look better — it was to make the *experiment honest*. Two
changes:

1. **A finite retrieval budget.** Every arm may look at the same small number of
   memories per decision. No stuffing the whole history into context.
2. **Realistic, noisy tickets.** We pad each ticket with category-neutral chit-chat
   ("I've been a customer for years and love the product, quick question…"). This is
   what real tickets look like — and it pollutes raw cosine similarity, because now
   *everything* looks a bit alike. The one discriminative token ("charged twice") gets
   drowned out in a raw k-NN match, but a *distilled rule* that keys on exactly that
   token stays sharp.

This is the context-rot regime — the same failure mode Qwen's own long-horizon models
are engineered to resist. And it's precisely where distillation should win.

---

## The result

Three arms, identical tickets, identical per-decision budget. The only variable is what
the agent does with memory.

```
session:      1    2    3    4    5    6    7    8
no-memory     28   24   16   12   24   24   16   24   mean  21%   (≈ chance, 5 classes)
episodic      28   68   60   56   72   52   68   80   mean  60%   (raw-RAG baseline)
MNEMO         20   72   72   64   84   72   84  100   mean  71%   (episodic + Dreaming)
```

- **No memory** never learns — it sits at chance.
- **Episodic RAG** genuinely helps, but noisy raw context caps it around 60%.
- **Mnemo** distils experience into a handful of high-signal rules and, *under the same
  budget*, reaches **71% mean and 100% by the final session** — **+10.5 points** over RAG.

The headline isn't "100%." It's that **memory architecture beats memory size**. A few
distilled rules carry more usable signal than a pile of raw episodes when your context
is finite — which, in the real world, it always is.

And because the whole thing is a controlled ablation, we could lock it behind a
regression test that *fails the build* if memory ever stops improving accuracy:

```python
assert full["mean"] > episodic["mean"] > none["mean"]   # consolidation > retrieval > none
assert full["improvement"] > 0.2                        # Mnemo actually gets better over time
```

You can reproduce all of it in about two seconds, no API key required — Mnemo ships with
a deterministic offline mode (hashing embeddings + a statistical distiller) so the exact
same code paths run in CI. Flip on a `DASHSCOPE_API_KEY` and the reasoning and
consolidation run on real **Qwen3.7-Max**; the embeddings on real Qwen embeddings.

---

## But wouldn't a frontier model just... ace this?

The sharpest objection to the whole experiment: Qwen3.7-Max zero-shot would classify
most support tickets without any memory at all. Correct — on *generic* tickets. So we
built a second experiment around the thing no model can do: know **your organization**.

At our fictional org, ground truth follows conventions that contradict surface reading.
Refund requests route to *account managers* (policy), not billing. "Project Falcon"
tickets — invoices included — go to the white-glove *technical* team. Acme's "sync
issues" are a known *shipping*-feed bug. No amount of model quality gets these right
zero-shot; they're not in any training distribution.

Two arms, same tickets, real Qwen3.7-Max on both: **alone** vs **with Mnemo**. The
live numbers were starker than our own validation predicted. Zero-shot scored **98%
on plain tickets** — and **0% on convention tickets, four sessions straight**. Not
low. Zero. With Mnemo, the same model climbed 14% → 71% → 86% → **100%**, a +86-point
final gap, while keeping 95% on plain tickets. And the consolidation pass wrote its
own runbook — readable rules with rationales:

> `IF text mentions 'Project Falcon' THEN category=technical (Project Falcon
> hardware, workspaces, and add-ons are technical)`

Every one of the 150 predictions is committed to the repo. That's the claim in one
line: **frontier models can't know your organization — memory is how they learn it.**

---

## Running it on Alibaba Cloud

The live deployment is deliberately simple: a Docker container on an **ECS instance
in Singapore**, talking to **Qwen3.7-Max and Qwen embeddings** through Model Studio's
OpenAI-compatible endpoint (with `preserve_thinking` to keep the agent's reasoning
coherent across turns). One gotcha worth passing on: qwen3.7-max is a thinking model,
so the chat path must stream and aggregate — a plain non-streaming call fails.

The architecture is built to grow past that. The store is an abstraction with a
**pgvector-on-RDS** backend for the episodic vector index, and the Dreaming loop
ships as a **Function Compute handler** with a time trigger — so in production,
consolidation is a serverless function waking up on a cron, reflecting on the last
few hours of tickets, and writing brand-new procedural rules into memory, entirely
on its own.

That last part is the whole thesis made literal. The agent isn't just answering
questions. While nothing is looking, it's turning experience into skill.

---

## Takeaways

1. **A vector DB is recall, not learning.** If your agent's competence doesn't change
   with experience, you built a search index, not a memory.
2. **Tier your memory.** Separating raw episodes from distilled facts and rules is what
   lets an agent get *sharper* instead of just *bigger*.
3. **Measure it, and try to prove yourself wrong.** Our best design decision came from an
   experiment that embarrassed our first one. Build the ablation. Add the regression test.
4. **Finite context is the real world.** Optimize for signal-per-token, not tokens.

Mnemo is open-source (MIT). If you're building agents that need to remember *and* learn,
steal the architecture.

*Built for the Global AI Hackathon with Qwen Cloud — MemoryAgent track.*

- **Repo (MIT):** https://github.com/Uthmannabeel/mnemo
- **Live console** (Alibaba Cloud ECS, Singapore): http://47.84.232.162:8000
- **Demo video:** *(YouTube link)*
