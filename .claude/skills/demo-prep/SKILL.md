---
name: demo-prep
description: Warms up Mnemo before recording the demo video — seeds memory so the dashboard's tiers and provenance are populated, and pre-runs the accuracy experiment so the chart is ready to reveal on camera.
disable-model-invocation: true
---

# /demo-prep — get Mnemo camera-ready

Goal: when you hit record, the dashboard already tells the story — populated memory
tiers, a live triage that cites real provenance, and the accuracy chart ready to draw.

## 1. Start the API + dashboard
```powershell
cd "C:\Users\Nabeel Uthman\mnemo\backend"
# Offline is fine for filming the dashboard; use live env for the Alibaba Cloud proof clip.
$env:MNEMO_OFFLINE="1"; $env:MNEMO_STORE="memory"
uvicorn app.api:app --port 8000
```
Open http://localhost:8000.

## 2. Seed memory so the browser + ledger are non-empty
Click **Seed sample workload** on the console (or `Invoke-RestMethod -Method Post http://localhost:8000/seed`).
This routes 25 synthetic tickets through the live agent + one consolidation pass, so the
memory browser fills with real distilled rules. Then click a sample-ticket chip, watch
the decision ledger cite a FIRED rule, and confirm/correct it — that's the learning
loop on camera.

## 3. Pre-warm the evidence charts
Load the page once before filming — both experiment charts compute and cache on first
load, so on camera they render instantly (Exp 1: the 20%→100% Mnemo climb; Exp 2: the
convention gap Qwen can't close alone).

## 4. Shot list
Follow `docs/DEMO_SCRIPT.md`. Order that lands best on camera:
1. Hero: the three-line accuracy chart.
2. Architecture diagram (`docs/architecture.svg`).
3. Live triage with provenance.
4. The Alibaba Cloud proof clip (health = qwen-live, FC Dreaming cron firing).

Tips: 1080p+, large terminal font, YouTube (public/unlisted) for the ~3-min cut.
