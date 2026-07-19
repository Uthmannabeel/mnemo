# Mnemo — campaign plan, pre- and post-submission

All times WAT (Nigeria). Deadline: **Sunday Jul 20, 10:00pm WAT** (2:00pm PDT).
Mechanics live in [ENDGAME.md](ENDGAME.md) (build/record/submit run-sheet),
[PROOF_RECORDING.md](PROOF_RECORDING.md), and [DEMO_SCRIPT.md](DEMO_SCRIPT.md) —
this file is the schedule and the after-plan.

---

## Phase 1 — Pre-submission (NOW → Sat Jul 19 night)

Goal: a COMPLETE submission on Devpost tonight, a full day before the wall.
Early-submit-then-edit is explicitly allowed — submitted-but-imperfect beats
unsubmitted-perfect, so submit the moment all links exist.

| # | Task | Time | Notes |
|---|---|---|---|
| 1 | Open Devpost form, save draft with everything already final | 10 min | Discover any custom form questions NOW, not at 9pm |
| 2 | Redeploy container w/ `MNEMO_AUTOSEED` (ENDGAME step 0) | 15 min | BEFORE any recording — live box still serves the old UI |
| 3 | Screenshot ECS instance page (Running + public IP) | 2 min | Required proof per "Proof of Deployment 101"; goes in gallery |
| 4 | Verify `/`, `/console`, `/evidence`, `/how`, `/memory?user_id=northwind` | 5 min | Autoseed needs ~2 min after start |
| 5 | Record proof screencast (60–90s) | 20 min | PROOF_RECORDING.md; dwell on the IP match |
| 6 | Record demo video (≤3:00) | 45 min | DEMO_SCRIPT.md; clipboard ticket, no music, never click Consolidate now |
| 7 | Upload both to YouTube, **public** | 15 min | Not unlisted — rules say publicly visible |
| 8 | Build 8 gallery images (plan + captions in SUBMISSION.md) | 30 min | Image 1 = 3:2 card "Same model. 0% → 100%." — it's the thumbnail |
| 9 | Publish BLOG.md to dev.to (fill video link first) | 15 min | Blog Post Prize = $500 + $500 credits, 10 winners |
| 10 | Fill 3 links in SUBMISSION.md → commit → push → CI green | 10 min | |
| 11 | **Submit on Devpost** → incognito-check every link | 15 min | Stage 1 is a literal completeness gate |
| 12 | `git tag v1.0-submission && git push --tags` | 2 min | Freeze marker for the judging window |

**Sunday Jul 20 (buffer day):** re-watch both videos once with fresh eyes;
re-check every submission link in incognito; final edits to the Devpost text if
anything reads wrong. Stop touching everything by **8:00pm WAT** — two hours of
margin against upload hiccups and clock ambiguity.

## Phase 2 — Quiet period (Jul 21 → Jul 27)

- **Do not push to main.** The submission is frozen; the repo state should match
  the `v1.0-submission` tag judges will see. Any new work happens on a branch.
- Keep the ECS instance running (≈$0.04/hr). Do NOT reset the DASHSCOPE key.
- Check the Devpost updates tab twice this week for judging announcements.
- Amplify the blog post once (X/LinkedIn, dev.to tags #qwen #ai #agents) — the
  Blog Post Prize is judged separately and visibility costs nothing.
- Recheck the project gallery once it goes public: know who actually submitted
  in the MemoryAgent track (recon found ~10 credible rivals; many will have
  missed the completeness gate).

## Phase 3 — Judging window (Jul 28 → Aug 11, 2:00pm PT)

Judges may open the live URL at ANY time in this window. The demo working when
they click is the whole ballgame.

- **Daily (2 min):** `Invoke-RestMethod "http://47.84.232.162:8000/memory?user_id=northwind"`
  — if empty (container bounced and autoseed somehow failed), re-seed both
  workspaces immediately (commands in PROOF_RECORDING.md). Also glance at
  `/health` = `qwen-live`.
- Keep Alibaba Cloud billing/credits alive — an expired credit killing the
  instance mid-judging sinks the entry after a perfect submission.
- No substantive pushes to main; no key rotation; no instance resizing.
- If the server dies irrecoverably: redeploy from the `v1.0-submission` tag —
  restoring the judged state is maintenance, not alteration.

## Phase 4 — Results & cleanup (Aug 11 → ~Aug 17 announcement)

Immediately after Aug 11, 2:00pm PT (judging ends):
- **Reset the DASHSCOPE API key** in Model Studio (it appeared in terminal
  scrollback during setup) — safe now that judges are done.
- **Release ECS instance `i-t4n1vhjybtduj4xiluf9`** (stop the ~$30/month bleed).
  Optional: snapshot first if a live demo might be wanted for the announcement.
- Watch for the winner announcement (~Aug 17, 2:00pm PT) and check email/spam —
  winner obligations (affidavit + W-8BEN for non-US residents) are due within
  **10 business days** of notice; prize wires within 60 days.

**If Mnemo wins (track prize or honorable mention):**
- Complete the forms immediately; confirm bank routing for a Nigeria wire.
- Update README with the placement badge; post the announcement (X/LinkedIn +
  a follow-up dev.to post — "what won and why" content performs).
- Accept the winner blog-feature/ambassador offers — free distribution.

**If Mnemo doesn't place:**
- Do the post-mortem against whoever won the MemoryAgent track: what did their
  submission have that ours lacked? Add the lessons to the hackathon playbook
  (the Shockwave post-mortem materially improved this entry — repeat that).
- The asset survives the contest: Mnemo is a portfolio-grade, live-benchmarked
  memory architecture. Reuse targets — the CockroachDB survivable-memory agent
  (closest sibling, deadline Aug 18), and the four-tier + Dreaming +
  eval-harness pattern as a component in any future agent entry.
- Keep the repo public with the README intact — it's a reference piece either
  way; the offline mode means it demos forever with zero API cost.

## Standing rules across all phases

- Office network blocks the ECS IP — all server checks/ops from home/hotspot.
- Never show `.env`, `docker inspect`, `docker logs`, or the Model Studio key
  page on any screen that might be shared or recorded.
- Every date here is absolute; if anything slips, the only immovable object is
  **Jul 20, 10:00pm WAT**.
