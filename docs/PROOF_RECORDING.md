# Proof-of-deployment recording — run sheet

Target: 60–90 seconds, no editing needed. One continuous screen recording that shows
the app running on Alibaba Cloud infrastructure. This is a *deliverable* (separate
from the 3-min demo video), so it only needs to prove deployment — don't re-pitch.

## Before you hit record

- **Record from home/hotspot** — the office FortiGuard firewall blocks 47.84.232.162:8000
  (the server is fine; the office network isn't).
- Check the server is up and seeded:
  ```powershell
  Invoke-RestMethod http://47.84.232.162:8000/health
  # expect: status ok, qwen_model qwen3.7-max, mode qwen-live
  Invoke-RestMethod "http://47.84.232.162:8000/memory?user_id=northwind"
  # expect: populated tiers. If empty (container restarted), re-seed:
  #   Invoke-RestMethod -Uri http://47.84.232.162:8000/seed -Method Post `
  #     -ContentType application/json -Body '{"user_id":"northwind","profile":"conventions"}'
  #   Invoke-RestMethod -Uri http://47.84.232.162:8000/seed -Method Post `
  #     -ContentType application/json -Body '{"user_id":"globex","profile":"standard"}'
  ```
- Log in to the Alibaba Cloud console in one browser tab, region **Singapore**;
  have http://47.84.232.162:8000 open in a second tab; a large-font terminal ready.
- **Never show on screen:** the `.env` file, `docker inspect mnemo` (it prints env
  vars including the API key), the Model Studio API-key page, terminal scrollback.
  Use fresh terminal windows.

## The recording, beat by beat

1. **(0:00) Alibaba Cloud console — ECS → Instances** (Singapore region).
   Point at the instance: ID `i-t4n1vhjybtduj4xiluf9`, status *Running*, public IP
   **47.84.232.162**. Say: *"Mnemo runs on this Alibaba Cloud ECS instance in
   Singapore."*

2. **(0:15) Terminal — health on the public IP:**
   ```powershell
   Invoke-RestMethod http://47.84.232.162:8000/health
   ```
   Point at `"mode": "qwen-live"` and `"qwen_model": "qwen3.7-max"`:
   *"Live mode — real Qwen3.7-Max through Alibaba Cloud Model Studio."*

3. **(0:30, optional but strong) Console → the instance → Connect → Workbench:**
   ```bash
   docker ps
   ```
   One container, `mnemo`, up, port 8000. (Nothing else — exit Workbench.)

4. **(0:45) Browser — http://47.84.232.162:8000.** Landing page, click *Open the
   console*, type a ticket in the triage box (Northwind workspace):
   *"Please refund my duplicate subscription charge"* → decision + the numbered
   evidence ledger appears. *"A live decision, made by Qwen3.7-Max steered by
   learned memory, served from this ECS instance."*

5. **(1:15) Close** on the health response or the console. Done.

## After BOTH recordings and the Devpost submission are in

- **Judges may test the live project at any time during the Judging Period
  (Jul 28 – Aug 11, 2026)** and can judge from the video/text alone — but if they do
  visit, the console must work. Keep the ECS instance running until at least
  **Aug 11** (winners announced ~Aug 17; ~$0.04/hr ≈ $30/month), then release it.
- The `MNEMO_AUTOSEED` redeploy happens **before** the recordings, not here — the
  deployed image predates the current site. See [ENDGAME.md](ENDGAME.md) step 0.
- **Reset the DASHSCOPE API key** in Model Studio (it appeared in terminal
  scrollback during setup) — but only *after* judging ends, or coordinate the reset
  with updating the VM's `.env` and restarting the container in the same sitting,
  or the live demo dies mid-judging.
