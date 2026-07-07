"""API smoke test: exercises the full interactive loop the dashboard drives.

seed → triage (fired rules in provenance) → feedback (credit assignment actually
moves confidence) → /eval caching. Offline + in-memory, so it runs anywhere.
"""
import os
import time

os.environ.setdefault("MNEMO_OFFLINE", "1")
os.environ.setdefault("MNEMO_STORE", "memory")

from fastapi.testclient import TestClient  # noqa: E402

from app.api import app  # noqa: E402

TICKET = "I was charged twice, refund the duplicate charge please"


def test_dashboard_loop():
    c = TestClient(app)

    # 1. seed populates the LIVE store and dreams rules into existence
    r = c.post("/seed").json()
    assert r["seeded"] == 26 and r["profile"] == "standard", r
    assert r["dreamed"]["procedural"] > 0, r

    # 1b. workspaces are isolated: a conventions workspace learns org policy
    #     (refund -> account) while the standard workspace keeps surface routing.
    r2 = c.post("/seed", json={"user_id": "northwind", "profile": "conventions"}).json()
    assert r2["dreamed"]["procedural"] > 0, r2
    nw = c.post("/triage", json={"ticket": TICKET, "user_id": "northwind"}).json()
    assert nw["category"] == "account", nw  # Northwind policy, learned from experience

    # 2. triage cites fired rules in provenance
    t = c.post("/triage", json={"ticket": TICKET}).json()
    assert t["category"] == "billing", t
    assert t["fired_memory_ids"], "a billing rule should have fired"
    assert any(p.get("fired") for p in t["provenance"])

    # 3. feedback with fired ids reinforces those rules (the old bug: ids were dropped)
    before = {p["id"]: p["confidence"] for p in t["provenance"] if p.get("fired")}
    c.post("/feedback", json={
        "ticket": TICKET,
        "predicted_category": t["category"],
        "true_category": "billing",
        "fired_memory_ids": t["fired_memory_ids"],
        "used_memory_ids": t["used_memory_ids"],
    })
    mem = c.get("/memory").json()
    after = {m["id"]: m["confidence"] for m in mem["procedural"]}
    assert any(after.get(i, 0) > before[i] for i in before), "feedback must reinforce fired rules"

    # 4. /eval is cached — the second call must be far cheaper than the first
    #    (relative bound: absolute timings are flaky on loaded machines/CI)
    t0 = time.time(); c.post("/eval"); t1 = time.time(); c.post("/eval"); t2 = time.time()
    assert (t2 - t1) < max(0.25, (t1 - t0) / 4), f"first {t1-t0:.3f}s, cached {t2-t1:.3f}s"

    # 5. landing page fronts the product; console lives at /console
    assert c.get("/").status_code == 200
    assert c.get("/console").status_code == 200
    assert c.get("/static/architecture.svg").status_code == 200


if __name__ == "__main__":
    test_dashboard_loop()
    print("ok")
