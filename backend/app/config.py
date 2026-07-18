"""Central configuration, loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # env_file anchored to backend/.env so behavior doesn't depend on the launch
    # directory (a relative ".env" silently loads nothing from the repo root).
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env", extra="ignore"
    )

    # Qwen Cloud / DashScope — Alibaba Cloud Model Studio OpenAI-compatible
    # endpoint. The live ECS deployment overrides this via QWEN_BASE_URL with its
    # region workspace endpoint (ap-southeast-1); dashscope-intl works equally.
    dashscope_api_key: str = ""
    qwen_base_url: str = "https://dashscope-us.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen3.7-max"
    qwen_embed_model: str = "text-embedding-v4"
    qwen_embed_dim: int = 1024

    # Runtime
    mnemo_offline: bool = False
    mnemo_store: str = "memory"  # "memory" | "postgres"
    database_url: str = "postgresql://mnemo:mnemo@localhost:5432/mnemo"

    # Consolidation / decay
    consolidation_every: int = 8
    memory_half_life_days: float = 30.0

    @property
    def offline(self) -> bool:
        # Offline if explicitly requested, or if no key is configured.
        return self.mnemo_offline or not self.dashscope_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
