"""Application settings (12-factor: every value comes from the environment; see .env.example)."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Xora Waypoint API"
    environment: str = Field(default="development", description="development | test | production")
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://xora:change-me@localhost:5432/xora"

    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_ttl_hours: int = 12

    cors_origins: list[str] = ["http://localhost:8080", "http://localhost:5173"]

    dataset_dir: Path = Path("./datasets")
    demo_start: datetime = datetime.fromisoformat("2026-04-06T14:50:00+05:30")
    seed_reset_demo: bool = False
    timezone: str = Field(default="Asia/Colombo", alias="TZ")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
