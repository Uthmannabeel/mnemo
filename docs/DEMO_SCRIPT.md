# 3-minute demo video script

Target: ~3:00. Screen-record the dashboard + a terminal + the Alibaba Cloud console.
Judging leans on Technical Depth + Innovation, so **lead with the result**, then show
the architecture that earns it, then prove it runs on Alibaba Cloud.

---

### 0:00–0:20 — The hook (talking head or voiceover over dashboard)
> "Most memory agents just bolt a chatbot to a vector database. They *store* the past,
> they don't *learn* from it. Mnemo is a cognitive memory architecture — and I can
> prove it makes better decisions the longer it runs."

Open on the LANDING PAGE (http://47.84.232.162:8000) — the 0→100 scoreboard is the
first frame. Then click "Open the console" for the rest.

### 0:20–0:55 — The proof (console, Evidence section — both charts load on page open)
- Point at the three lines of Experiment 1:
  > "Same support tickets, same context budget per decision. The only difference is
  > memory. No-memory stays at chance — 21%. Classic episodic RAG climbs to 60%.
  > Mnemo hits 71% mean, 100% by the last session."
- Emphasize: "This is a controlled ablation, not a cherry-picked demo."

### 0:55–1:25 — The architecture (README mermaid diagram on screen)
> "Here's why. Mnemo has four memory tiers, modelled on human memory. Every ticket
> and outcome is written as a raw *episode*. Then a background **Dreaming loop**,
> powered by **Qwen3.7-Max**, reflects on those episodes and distils them into
> **semantic facts** and **procedural rules** — 'if a ticket mentions *charged twice*,
> it's billing.'"
- Cut to the dashboard's memory tiers: show procedural rules that were auto-distilled.
> "Under a finite context budget, a handful of distilled rules beat a pile of noisy
> raw tickets — that's the context-rot problem Qwen's own models are built to fight."

### 1:25–1:50 — the killer-question slide (the strongest 25 seconds)
> "The obvious objection: wouldn't Qwen alone ace this? We ran it — live, both arms
> real Qwen3.7-Max. On ordinary tickets, zero-shot scores 98%. On tickets governed by
> org conventions, it scores **zero** — four sessions straight. With Mnemo, the same
> model reaches **100%**. Every one of the 150 predictions is in the repo."
Show the live table in README's Experiment-2 section, then one distilled rule with
its self-written rationale.

### 1:50–2:20 — Live triage with provenance (console triage box, Northwind workspace)
- Type: *"I was charged twice this month, please refund the duplicate charge."*
> "It predicts **billing** — and it *shows its work*: the exact memories that justified
> the call. Every decision is explainable."
- Mention decay + conflict resolution in one line:
> "Rules that prove wrong lose confidence and fade; refined rules supersede stale ones."

### 2:20–2:50 — Running on Alibaba Cloud (Alibaba console + terminal + browser)
- Show the ECS instance in the Alibaba Cloud console (Singapore region, public IP
  visible), then `GET http://47.84.232.162:8000/health` in a terminal →
  `"mode": "qwen-live"`, `"qwen_model": "qwen3.7-max"`.
- Click **💤 Dream now** in the console (or `POST /consolidate`) and show new
  procedural rules appearing in the memory browser — the Dreaming loop running live
  on Alibaba Cloud infrastructure.
> "This is running right now on an Alibaba Cloud ECS instance in Singapore —
> Qwen3.7-Max and Qwen embeddings via Model Studio. Trigger a Dreaming pass and
> watch it distil the session's episodes into new rules, live. The same image ships
> a Function Compute handler so consolidation can run on a schedule in production."

### 2:50–3:00 — Close
> "Mnemo — an agent that doesn't just remember. It learns. Code's open-source, MIT."
Show repo URL + the accuracy chart one last time.

---

**Recording tips**
- The live store is in-memory: if the container ever restarts, seed both workspaces
  again before filming (`POST /seed {"user_id":"northwind","profile":"conventions"}`
  and `{"user_id":"globex","profile":"standard"}`) so the memory browser and triage
  provenance are populated. Sanity-check `GET /memory?user_id=northwind` first.
- Both evidence charts are cached server-side after first load — open the console
  once before recording so they render instantly on camera.
- Record from home/hotspot — the office firewall blocks the ECS IP.
- Keep the terminal font large. 1080p minimum. Upload to YouTube (public/unlisted).
