# 3-minute demo video script

Target: **hard cap 3:00** — the official rules state judges "are not required to
watch beyond three minutes", and may judge from the video + text alone without ever
touching the live demo. Everything that scores must be on screen inside 3:00, and
the 0%→100% number must land in the first ten seconds. Screen-record the dashboard +
a terminal + the Alibaba Cloud console. Judging leans on Technical Depth +
Innovation, so **lead with the result**, then show the architecture that earns it,
then prove it runs on Alibaba Cloud.

---

### 0:00–0:20 — The hook (a failure story with a number, not category talk)
> "We gave the strongest Qwen model support tickets governed by rules that exist only
> inside one company — refunds go to account managers, Project Falcon gets the
> white-glove team. Zero-shot, it scored **zero percent**. Four sessions in a row.
> Not because the model is weak — because that knowledge doesn't exist outside the
> org. Mnemo is how the model learns it."

Open on the LANDING PAGE (http://47.84.232.162:8000) — the 0→100 scoreboard is the
first frame. Then click "Open the console" for the rest.

### 0:20–0:55 — The proof (the LIVE experiment — strongest evidence first)
- Show the README Experiment-2 live table:
  > "We ran it live — both arms real Qwen3.7-Max. Zero-shot: 98% on ordinary tickets,
  > 0% on convention tickets, four sessions straight. The same model with Mnemo:
  > 14, 71, 86, then **100%** — an 86-point final gap. Every one of the 150
  > predictions is committed to the repo. And Mnemo does it on **half the context
  > tokens per decision** — better answers at half the token spend."
- Show one distilled rule with its self-written rationale.

### 0:55–1:25 — The architecture (README mermaid diagram on screen)
> "Here's why. Mnemo has four memory tiers, modelled on human memory. Every ticket
> and outcome is written as a raw *episode*. Then a background **Dreaming loop**,
> powered by **Qwen3.7-Max**, reflects on those episodes and distils them into
> **semantic facts** and **procedural rules** — 'if a ticket mentions *charged twice*,
> it's billing.'"
- Cut to the dashboard's memory tiers: show procedural rules that were auto-distilled.
> "Under a finite context budget, a handful of distilled rules beat a pile of noisy
> raw tickets — that's the context-rot problem Qwen's own models are built to fight."

### 1:25–1:50 — the rigor slide (controlled ablation, Experiment 1)
> "Is it the memory *architecture*, or would any retrieval do? Controlled ablation —
> same tickets, same fixed context budget per decision, only the memory differs.
> No memory sits at chance, 21%. Classic episodic RAG climbs to 60%. Mnemo hits 71%
> mean and 100% by the final session. Distilled rules beat raw retrieval when
> context is finite."
Point at the three lines of the Experiment-1 chart in the console Evidence section.

### 1:50–2:20 — Live triage with provenance (console triage box)
- In the **Northwind** workspace, type:
  *"Please refund my duplicate subscription charge."*
> "Surface reading says billing. Mnemo routes it to **account** — because it *learned*
> Northwind's policy: refunds go to account managers. And it shows its work: the
> decision ledger cites the fired rule, which the Dreaming loop wrote itself."
- (If time allows) switch the workspace to **Globex**, same ticket → **billing**:
> "Same model, same ticket, different org — each workspace cites its own learned policy."
- Mention decay + conflict resolution in one line:
> "Rules that prove wrong lose confidence and fade; refined rules supersede stale ones."

### 2:20–2:50 — Running on Alibaba Cloud (Alibaba console + terminal + browser)
- Show the ECS instance in the Alibaba Cloud console (Singapore region, public IP
  visible), then `GET http://47.84.232.162:8000/health` in a terminal →
  `"mode": "qwen-live"`, `"qwen_model": "qwen3.7-max"`.
- Click **Dream now** in the console (or `POST /consolidate`) and show new
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
