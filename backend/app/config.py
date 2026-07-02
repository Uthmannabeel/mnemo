"""Central configuration, loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Qwen Cloud / DashScope
    dashscope_api_key: str = ""
    qwen_base_url: str = "https://dashscope-us.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen3.7-max"
    qwen_embed_model: str = "text-embedding-v4"
    qwen_embed_dim: int = 1024

    # Runtime
    mnemo_offline: int = 0
    mnemo_store: str = "memory"  # "memory" | "postgres"
    database_url: str = "postgresql://mnemo:mnemo@localhost:5432/mnemo"

    # Consolidation / decay
    consolidation_every: int = 8
    memory_half_life_days: float = 30.0

    @property
    def offline(self) -> bool:
        # Offline if explicitly requested, or if no key is configured.
        return bool(self.mnemo_offline) or not self.dashscope_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
