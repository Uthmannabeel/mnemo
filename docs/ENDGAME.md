# Endgame — one session, from home/hotspot, in order

Devpost deadline: **Sunday Jul 20, 2:00pm PDT** (= **10:00pm WAT**). One organizer
update post says "PST", which would be an hour *earlier* — treat 2:00pm PDT as the
wall and submit hours before it. Organizers have stated **no further extensions**.
Target finishing this entire sheet by **Saturday Jul 19** so the ambiguity never
matters. Budget ~2–3
hours. Everything below needs a network that can reach 47.84.232.162:8000 — the office
FortiGuard blocks it, so this is a home/hotspot session.

Have open before starting: Alibaba Cloud console (Singapore region), a fresh
large-font terminal, http://47.84.232.162:8000, your screen recorder.

---

## 0 — Redeploy with autoseed (~15 min, BEFORE any recording)

The running container predates both the multi-page site (`/evidence`, `/how`) and
`MNEMO_AUTOSEED` self-healing. Recording against it would film the old UI, and a
restart during the Jul 28–Aug 11 judging window would show judges an empty console.
Redeploy first.

ECS console → Instances → `i-t4n1vhjybtduj4xiluf9` → **Connect → Workbench**
(no SSH key exists on your machine — Workbench is the way in). Then:

```bash
# NB: the repo was double-cloned on the VM — the real checkout is nested:
cd ~/mnemo/backend/mnemo && git pull
cd backend
grep -q MNEMO_AUTOSEED .env || echo 'MNEMO_AUTOSEED=northwind:conventions,globex:standard' >> .env
docker build -t mnemo .
docker rm -f mnemo
docker run -d --name mnemo --restart unless-stopped -p 8000:8000 --env-file .env mnemo
sleep 5 && curl -s localhost:8000/health
```

Do **not** run `docker inspect mnemo` (prints the API key). Close Workbench.

Verify from your own browser before recording anything:

```powershell
Invoke-RestMethod http://47.84.232.162:8000/health          # mode = qwen-live
Invoke-RestMethod "http://47.84.232.162:8000/memory?user_id=northwind"   # populated tiers
```

Autoseed re-seeds and pre-warms the evidence charts in a background thread — give it
a couple of minutes after start, then click through `/`, `/console`, `/evidence`,
`/how` and confirm the charts render.

## 1 — Proof-of-deployment recording (60–90 s)

Follow [PROOF_RECORDING.md](PROOF_RECORDING.md) beat by beat (console → health →
`docker ps` → live triage). Fresh terminal windows only; never show `.env`, scrollback,
or the Model Studio key page.

## 2 — Demo video (~3:00 hard cap)

Follow [DEMO_SCRIPT.md](DEMO_SCRIPT.md). Judges are not required to watch past three
minutes — the 0% → 100% story must land inside the cap. Record in one or two takes;
done beats perfect.

## 3 — Upload both videos

YouTube (public or unlisted both satisfy Devpost). Copy both URLs.

## 4 — Publish the blog (Blog Post Award)

Paste [BLOG.md](BLOG.md) into dev.to (or Hashnode/Medium — any public URL qualifies).
Copy the URL.

## 5 — Fill and submit

1. In `SUBMISSION.md`, fill the three `<fill in>` links (demo video, proof recording,
   blog). Commit + push.
2. Devpost form: paste SUBMISSION.md section by section, track = **MemoryAgent**,
   gallery image = `docs/architecture.png`, add the video URL, the proof recording,
   the two Alibaba-API code links, repo link, live URL.
3. **Submit.** Then re-open the submission page and confirm every link resolves in a
   private/incognito window (Stage 1 of judging is a literal completeness gate).

## After submitting

- Keep the ECS instance (and working demo) up through **Aug 11** — judges may test
  the live URL at any point in the judging period. Release it after (~$0.04/hr).
- Reset the DASHSCOPE key only after judging ends, or in the same sitting as a
  container `.env` update + restart — otherwise the live demo dies mid-judging.
