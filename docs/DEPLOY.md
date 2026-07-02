# Deploying Mnemo on Alibaba Cloud

This is the "Proof of Alibaba Cloud Deployment" path. Two supported topologies —
pick **ECS** for the simplest screencast, or **Function Compute** to show the
Dreaming loop running as a serverless scheduled job.

## Prerequisites

1. **Model Studio API key** — Model Studio console → API-KEY → *Create*. Note your
   region; the OpenAI-compatible base URL differs per region (see `.env.example`).
2. Apply the **hackathon credit coupon** in Billing so Qwen calls are free.
3. **RDS for PostgreSQL** instance with the `vector` extension enabled (Console →
   RDS → *Extensions* → enable `vector`). Grab its connection string.

Set these on whichever compute you use:

```
DASHSCOPE_API_KEY=sk-...
QWEN_BASE_URL=https://dashscope-us.aliyuncs.com/compatible-mode/v1   # your region
QWEN_MODEL=qwen3.7-max
MNEMO_OFFLINE=0
MNEMO_STORE=postgres
DATABASE_URL=postgresql://user:pass@<rds-host>:5432/mnemo
```

---

## Option A — ECS (VM), simplest for the demo video

```bash
# on an Ubuntu ECS instance, security group open on 8000
git clone <your-repo> && cd mnemo/backend
docker build -t mnemo .
docker run -d --name mnemo -p 8000:8000 --env-file .env mnemo

curl http://<ecs-public-ip>:8000/health
# {"status":"ok","qwen_model":"qwen3.7-max","store":"postgres","mode":"qwen-live"}
```

The `mode: qwen-live` + `store: postgres` in the health response, filmed on the ECS
public IP, is your deployment proof.

---

## Option B — Function Compute (serverless + scheduled Dreaming)

1. **API service** — create a Function Compute *custom-container* function from the
   `backend/Dockerfile` image (push to Alibaba Cloud Container Registry first).
   Bind an HTTP trigger. This serves `/triage`, `/feedback`, `/memory`, `/eval`.

2. **Dreaming cron** — create a second *event* function from the **same image**, set
   its handler to `fc_dream.handler` (the file ships in the image), and attach a
   **Time Trigger** (e.g. `0 0 */2 * * *`, every 2h). Give it the same env vars as the
   API (crucially `MNEMO_STORE=postgres` + the same `DATABASE_URL`, so it shares memory
   with the API). The handler persists a `consolidated` flag in RDS, so it never
   re-processes episodes across runs.

   Filming this scheduled function firing and writing new procedural memories is the
   most compelling proof — it shows the agent *autonomously accumulating experience*
   on Alibaba Cloud infrastructure, exactly what the track asks for.

---

## Verify the Qwen path end-to-end

```bash
curl -s -X POST http://<host>:8000/triage \
  -H 'content-type: application/json' \
  -d '{"ticket":"I was charged twice this month, please refund the duplicate"}'
# -> {"category":"billing","rationale":"matched rule: IF ... 'charged' THEN billing","provenance":[...]}
```

Then `POST /feedback` with the true category, `POST /consolidate`, and watch
`GET /memory` grow new semantic + procedural entries.

## Run Experiment 2 live (once, before submitting)

With the live `.env` loaded, run the org-conventions experiment against real
Qwen3.7-Max and **commit the results JSON** so judges can audit a real run:

```bash
cd backend
python -m app.eval.live_harness --yes     # ~160 Qwen calls, checkpointed per session
git add results/org_experiment.json && git commit -m "Add live Qwen3.7-Max Experiment 2 results"
```

Then paste the printed table into README's Experiment 2 section, replacing the
offline pipeline numbers with the live ones.
