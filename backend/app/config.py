"""
Kage Scan — Application Settings
Loads from environment variables / .env file via pydantic-settings.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration — values can be overridden via .env or env vars."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Paths ──────────────────────────────────────────────────────────
    DATA_DIR: Path = Path("./data")
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/kagescan_data.db"

    # ── LLM / BYOK ────────────────────────────────────────────────────
    LLM_API_KEY: str | None = None
    LLM_MODEL: str = "gpt-4o-mini"  # Default model for litellm

    # ── Server ─────────────────────────────────────────────────────────
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True


# Singleton instance — import this everywhere
settings = Settings()
