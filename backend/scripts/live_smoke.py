"""Live smoke test — one chat call + one embedding against real Qwen Cloud.

Validates in ~10 seconds what no offline test can: the model id exists in this
region, the base URL is right, streaming works on the thinking-only Max tier,
and the embedding dimension matches the pgvector schema. Run from backend/:

    python -m scripts.live_smoke
"""
import sys

from app.config import get_settings
from app.qwen_client import QwenClient


def main() -> int:
    s = get_settings()
    if not s.dashscope_api_key or s.offline:
        print("No live key / offline mode set — nothing to smoke-test.")
        return 1
    print(f"model={s.qwen_model}  embed={s.qwen_embed_model}  base={s.qwen_base_url}")

    client = QwenClient()

    print("chat: ", end="", flush=True)
    reply = client.chat(
        [{"role": "user", "content": "Reply with exactly one word: OK"}],
        temperature=0.0,
        preserve_thinking=False,
    )
    print(repr(reply.strip()[:60]))

    print("embed: ", end="", flush=True)
    vec = client.embed_one("smoke test")
    print(f"dim={len(vec)} (config expects {s.qwen_embed_dim})")

    print("json: ", end="", flush=True)
    data = client.complete_json(
        "You classify support tickets into one of: billing, technical.",
        'TICKET: "the app crashes on upload". Respond as {"category": "..."}',
    )
    print(data)

    ok = bool(reply) and len(vec) == s.qwen_embed_dim and data.get("category") in ("billing", "technical")
    print("RESULT:", "LIVE PATH OK" if ok else "CHECK FAILED")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
