---
name: deploy-check
description: Pre-deployment gate for Mnemo — verifies the regression test passes, secrets/config are correct, the container builds, and the live Qwen path is reachable before shipping to Alibaba Cloud.
disable-model-invocation: true
---

# /deploy-check — pre-flight before deploying Mnemo to Alibaba Cloud

Run these in order. Stop at the first failure and fix before continuing.

## 1. Invariant is green (offline)
```powershell
cd "C:\Users\Nabeel Uthman\mnemo\backend"
$env:MNEMO_OFFLINE="1"; $env:MNEMO_STORE="memory"
python -m tests.test_learning
```
Expect `ok`. If it fails, the core claim is broken — do not deploy.

## 2. Config sanity
- `backend/.env` exists, `MNEMO_OFFLINE=0`, `MNEMO_STORE=postgres`, real
  `DASHSCOPE_API_KEY`, correct region `QWEN_BASE_URL`, and `DATABASE_URL` pointing at
  RDS.
- Confirm `QWEN_MODEL` (`qwen3.7-max`) and `QWEN_EMBED_MODEL` (`text-embedding-v4`)
  match the Model Studio console for your region.
- `.env` is git-ignored (`git status` should NOT list it).

## 3. Container builds
```powershell
cd "C:\Users\Nabeel Uthman\mnemo\backend"
docker build -t mnemo .
```

## 4. Live Qwen path works (local, with real key)
```powershell
docker run --rm -p 8000:8000 --env-file .env mnemo
# in another shell (PowerShell-native; `curl` aliases Invoke-WebRequest on 5.1):
Invoke-RestMethod http://localhost:8000/health   # expect mode "qwen-live", store "postgres"
Invoke-RestMethod -Uri http://localhost:8000/triage -Method Post -ContentType 'application/json' `
  -Body '{"ticket":"I was charged twice, please refund the duplicate"}'
```
`mode: qwen-live` confirms Qwen3.7-Max is actually being called. If it shows
`offline-mock`, the key/env didn't load.

## 5. RDS reachable + schema created
The first request against `MNEMO_STORE=postgres` auto-creates the `memories` table and
`vector` extension. Confirm no connection errors in the container logs.

## 6. Run Experiment 2 live (once)
```powershell
cd "C:\Users\Nabeel Uthman\mnemo\backend"
python -m app.eval.live_harness --yes   # ~160 Qwen3.7-Max calls; results/org_experiment.json
```
Commit the results JSON and paste the live table into README's Experiment 2 section.

Once all six pass, follow `docs/DEPLOY.md` to ship to ECS, then add the Function
Compute Dreaming cron (`fc_dream.handler`).
