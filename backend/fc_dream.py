"""Alibaba Cloud Function Compute handler — the scheduled Dreaming loop.

Deploy as an *event* function using the same container image as the API, with a
Time Trigger (e.g. cron `0 0 */2 * * *` — every 2 hours). It runs one consolidation
pass: reflect over new episodes with Qwen3.7-Max and distil durable memory.

Because the "consolidated" flag is persisted in RDS (see Consolidator), this shares
state with the ECS/FC API process and never re-processes the same episodes.

Requires (function env vars):
    DASHSCOPE_API_KEY, QWEN_BASE_URL, QWEN_MODEL=qwen3.7-max, MNEMO_OFFLINE=0,
    MNEMO_STORE=postgres, DATABASE_URL=postgresql://user:pass@<rds-host>:5432/mnemo
"""
import json
import logging

logger = logging.getLogger()


def handler(event, context):
    # Import inside the handler so cold-start import errors surface in FC logs.
    from app.memory.consolidation import Consolidator
    from app.memory.manager import MemoryManager

    # `event` may carry {"user_id": "..."} when invoked manually; default otherwise.
    user_id = "default"
    try:
        if event:
            payload = json.loads(event) if isinstance(event, (bytes, str)) else event
            user_id = payload.get("user_id", "default")
    except (ValueError, AttributeError):
        pass

    summary = Consolidator(MemoryManager()).run(user_id=user_id)
    logger.info("Dreaming pass complete: %s", summary)
    return json.dumps({"ok": True, "user_id": user_id, **summary})
