# 3-minute demo video script

Target: **hard cap 3:00** — the official rules state judges "are not required to
watch beyond three minutes", and may judge from the video + text alone without ever
touching the live demo. Everything that scores must be on screen inside 3:00, and
the 0→100 arc must land — spoken and visible — inside the first twenty seconds.
Judging leans on Technical Depth + Innovation, so **lead with the result**, then the
architecture that earns it, then prove it runs on Alibaba Cloud. Every claim gets a
cursor pointing at it: never say a number the screen isn't showing.

Stay inside the product the whole time (landing → /evidence → /how → console) — no
cuts to GitHub; the site already carries every table and diagram.

---

### 0:00–0:19 — The hook (landing page scoreboard, pre-loaded)
> "These support tickets are governed by rules that exist only inside one company —
> refunds go to account managers, Project Falcon gets the white-glove team.
> Zero-shot, Qwen3.7-Max scores **zero percent**. Four sessions straight. The same
> model, with Mnemo's memory: **one hundred**. This scoreboard is live."

Screen: start **already on the landing page** (http://47.84.232.162:8000), browser
zoom set so the h1 AND the scoreboard table are both in frame (the table sits below
the hero — check before recording). Cursor rests on the zero row; drag it along
`0 0 0 0` on "four sessions straight," then along `14 71 86 100` on "one hundred."
Say "Qwen3.7-Max" by name — sponsor judges should hear their model in the first ten
seconds.

### 0:19–0:50 — The proof (stay on the scoreboard, then /evidence)
> "Both arms are the real model, run live — every one of the 150 predictions is
> committed to the repo for audit. Zero-shot never learns: by session five it's
> still guessing at 14. With Mnemo: 14, 71, 86, then a hundred — and it stays there.
> Plain tickets don't pay for it either — **95% retained**. And it does this on
> **half the context per decision** — 574 characters where RAG needs eleven hundred.
> Here's a rule it wrote for itself."

Screen: cursor on the scoreboard rows for the numbers; point at the **50% card /
head-to-head figures** exactly when the half-context line is spoken; then click
**Evidence** and scroll to one distilled rule with its self-written rationale —
ideally the exception rule (`'purchase order'` overriding ordinary shipment
language): it is the best answer to "a keyword table could do this."

### 0:50–1:12 — The architecture (/how page, architecture.svg)
> "Four memory tiers, modelled on human memory. Every ticket becomes a raw
> *episode*. A background **Dreaming loop** — Qwen3.7-Max itself — reflects and
> distils them into **semantic facts** and **procedural rules**. Under a finite
> context budget, a handful of distilled rules beats a pile of noisy tickets."

Screen: the /how page (serves architecture.svg locally — no GitHub detour).

### 1:12–1:35 — The rigor beat (controlled ablation, console Evidence chart)
> "**Separate experiment — the ablation.** Same tickets, same fixed budget, only the
> memory differs: no memory sits at chance, 21. Episodic RAG climbs to 60. Mnemo:
> 71 mean, 100 by the final session. Distilled rules beat raw retrieval when context
> is finite."

Open with the frame-break ("separate experiment") — a distracted judge hears 71
twice in a minute and must not conflate the two tables. Cursor touches each of the
three chart lines as its number is spoken.

### 1:35–2:25 — The killer beat (both workspaces — MANDATORY, not optional)
This is the single most innovative 15 seconds — the beat no vector-store competitor
can copy. **Paste the ticket from clipboard, never type on camera.**

- In the **Northwind** workspace, paste: *"Please refund my duplicate subscription
  charge."* While the live Qwen call runs:
> "That's a live Qwen3.7-Max call, steered by six retrieved memories under a hard
> budget."
- On the answer:
> "Surface reading says billing. Mnemo routes it to **account** — because it
> *learned* Northwind's policy. And it shows its work: the decision ledger cites the
> fired rule, which the Dreaming loop wrote itself."
- Switch to **Globex** (the ledger clears on workspace switch — expected, don't
  react), paste the same ticket:
> "Same model, same ticket, different org — **billing** here, because Globex has no
> such policy. Each workspace cites its own learned memory."
- One line while the Globex call runs:
> "Rules that prove wrong lose confidence and fade; refined rules supersede stale
> ones — it unlearns, and there's a regression test proving it."

### 2:25–2:48 — Running on Alibaba Cloud (eligibility beat)
Screen: Alibaba Cloud console, ECS instance list, Singapore region — **hover the
public IP** — then a large-font terminal: `GET http://47.84.232.162:8000/health` →
`"mode": "qwen-live"`, `"qwen_model": "qwen3.7-max"` — then back to the browser with
the **same IP in the URL bar**. The IP match is the proof; let the camera dwell on it.

> "Running right now on this ECS instance in Singapore — mode qwen-live, Qwen3.7-Max
> and Qwen embeddings through Model Studio. The same image ships a Function Compute
> handler for scheduled consolidation."

**Do NOT click "Consolidate now" on camera.** Seeding already consolidated
everything, so it will answer *"Nothing new to consolidate"* — a live failure. The
fired-rule flash in triage plus `/health` already prove liveness. (Only if you
insist on showing it: pre-stage off camera by triaging + correcting 3–4 tickets —
stay under 8, the auto-dream threshold — verify unconsolidated episodes exist, click
it at the *start* of this beat, and talk over the 10–30s wait. Never show a result
strip that says "+0 rules.")

### 2:48–3:00 — Close (rubric mirror, end on the scoreboard)
> "Every organization has knowledge no model can know. Mnemo is the memory
> architecture that learns it — measured, zero to one hundred, live, every
> prediction committed — running right now on Alibaba Cloud with Qwen3.7-Max. Open
> source, MIT. Mnemo doesn't just remember. It learns."

Screen: back on the landing scoreboard (not the repo URL) for the final frame.

---

**Pre-record checklist**
- **Pre-load every page you will show** — landing, /evidence, /how, console, and the
  Alibaba ECS console tab — before hitting record. Evidence charts are server-cached
  only after first load, and the landing pulls Google Fonts, which on this machine's
  flaky DNS can flash unstyled text on a cold first frame.
- The live store is in-memory: sanity-check `GET /memory?user_id=northwind` is
  populated. If the container restarted, re-seed both workspaces first
  (`POST /seed {"user_id":"northwind","profile":"conventions"}` and
  `{"user_id":"globex","profile":"standard"}`).
- Do one **throwaway triage in each workspace** right before recording — warms the
  path and tells you the live-call latency you'll be talking over.
- Put the demo ticket text on the clipboard.
- Clean browser window: no bookmarks bar, no background tabs (especially not Model
  Studio), 1080p, ~110% zoom. Large terminal font.
- Record from home/hotspot — the office firewall blocks the ECS IP.
- Upload to YouTube (public or unlisted both satisfy Devpost).

**Judging-window ops (Jul 28 – Aug 11)**
Judges may open the live URL at any time. Once a day: hit
`GET http://47.84.232.162:8000/memory?user_id=northwind` — if it comes back empty
(container bounced), re-seed both workspaces immediately with the commands above.
An empty memory browser routes the refund ticket to *billing* in Northwind and turns
the demo into a counter-demo. (`MNEMO_AUTOSEED` in the redeployed image should make
this automatic — the daily check is the backstop.)
