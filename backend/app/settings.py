"""Application settings loaded once from backend/.env (pydantic-settings).

The env file is resolved relative to this file, not the current working directory,
so the server works the same from any shell. Real environment variables take
precedence over .env values (pydantic-settings precedence), which is what the
pytest conftest uses to point tests at an isolated E: database.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"
DATA_DIR = BACKEND_DIR / "data"
DEFAULT_DB_URL = f"sqlite:///{(DATA_DIR / 'fcd.sqlite').as_posix()}"

WEATHER_MODES = ("live", "replay", "synthetic")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"
    database_url: str = Field(default_factory=lambda: DEFAULT_DB_URL)
    cors_origins: str = "http://localhost:5173"

    # Weather: live | replay | synthetic. Replay is the safe demo mode (R7).
    weather_mode: str = "replay"
    replay_event: str = "michaung_2023"

    # Drawing reading (free tier only, no billing). Key stays out of logs and responses.
    gemini_api_key: str = ""
    gemini_model: str = ""
    vision_provider_chain: str = "cache,gemini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = ""

    # Readiness staleness default (M8); readiness.yaml remains the source of truth
    # for score behaviour - this only mirrors it for quick access.
    staleness_days: int = 90

    @field_validator("weather_mode")
    @classmethod
    def _validate_weather_mode(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in WEATHER_MODES:
            raise ValueError(f"weather_mode must be one of {WEATHER_MODES}, got {value!r}")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def vision_providers(self) -> list[str]:
        return [provider.strip().lower() for provider in self.vision_provider_chain.split(",") if provider.strip()]

    @property
    def data_dir(self) -> Path:
        return DATA_DIR


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()