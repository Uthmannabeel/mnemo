# 3-minute demo video script

Target: ~3:00. Screen-record the dashboard + a terminal + the Alibaba Cloud console.
Judging leans on Technical Depth + Innovation, so **lead with the result**, then show
the architecture that earns it, then prove it runs on Alibaba Cloud.

---

### 0:00–0:20 — The hook (talking head or voiceover over dashboard)
> "Most memory agents just bolt a chatbot to a vector database. They *store* the past,
> they don't *learn* from it. Mnemo is a cognitive memory architecture — and I can
> prove it makes better decisions the longer it runs."

Show the dashboard hero: the three-line accuracy chart already rendered.

### 0:20–1:00 — The proof (dashboard, click "Run learning experiment")
- Point at the three lines as they draw:
  > "Same support tickets, same context budget per decision. The only difference is
  > memory. No-memory stays at chance — 21%. Classic episodic RAG climbs to 60%.
  > Mnemo hits 71% mean, 100% by the last session."
- Emphasize: "This is a controlled ablation, not a cherry-picked demo."

### 1:00–1:45 — The architecture (README mermaid diagram on screen)
> "Here's why. Mnemo has four memory tiers, modelled on human memory. Every ticket
> and outcome is written as a raw *episode*. Then a background **Dreaming loop**,
> powered by **Qwen3.7-Max**, reflects on those episodes and distils them into
> **semantic facts** and **procedural rules** — 'if a ticket mentions *charged twice*,
> it's billing.'"
- Cut to the dashboard's memory tiers: show procedural rules that were auto-distilled.
> "Under a finite context budget, a handful of distilled rules beat a pile of noisy
> raw tickets — that's the context-rot problem Qwen's own models are built to fight."

### (insert if live Exp-2 results are in) — the killer-question slide (~15s)
> "And to the obvious objection — 'wouldn't Qwen alone ace this?' — we ran it. On
> tickets governed by org conventions no model can know, zero-shot Qwen3.7-Max stays
> wrong forever. With Mnemo's memory, the same model learns every convention."
Show the `results/org_experiment.json` table / README Exp-2 section. Trim the
architecture beat by ~15s to fit.

### 1:45–2:15 — Live triage with provenance (dashboard triage box)
- Type: *"I was charged twice this month, please refund the duplicate charge."*
> "It predicts **billing** — and it *shows its work*: the exact memories that justified
> the call. Every decision is explainable."
- Mention decay + conflict resolution in one line:
> "Rules that prove wrong lose confidence and fade; refined rules supersede stale ones."

### 2:15–2:50 — Running on Alibaba Cloud (console + curl)
- Show `GET /health` on the ECS/Function Compute public URL → `qwen-live`, `postgres`.
- Show the **scheduled Dreaming function** in the Function Compute console firing.
> "The backend runs on Alibaba Cloud — Qwen3.7-Max and Qwen embeddings via Model
> Studio, pgvector on RDS, and the Dreaming loop as a scheduled Function Compute job.
> The agent accumulates experience autonomously, in production."

### 2:50–3:00 — Close
> "Mnemo — an agent that doesn't just remember. It learns. Code's open-source, MIT."
Show repo URL + the accuracy chart one last time.

---

**Recording tips**
- Pre-run `POST /eval` once so the chart is warm; re-run it on camera for the reveal.
- Seed the memory before filming triage (run a session) so provenance is populated.
- Keep the terminal font large. 1080p minimum. Upload to YouTube (public/unlisted).
