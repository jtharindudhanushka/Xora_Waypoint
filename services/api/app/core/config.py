"""Application settings (12-factor: every value comes from the environment; see .env.example)."""

from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Xora Waypoint API"
    environment: str = Field(default="development", description="development | test | production")
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://xora:change-me@localhost:5432/xora"

    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_ttl_hours: int = 12

    # NoDecode: a comma-separated env value is split by the validator, not parsed as JSON.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:8080",
        "http://localhost:5173",
    ]

    dataset_dir: Path = Path("./datasets")
    demo_start: datetime = datetime.fromisoformat("2026-04-06T14:50:00+05:30")
    seed_reset_demo: bool = False
    timezone: str = Field(default="Asia/Colombo", alias="TZ")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            if value.startswith("["):
                return json.loads(value)
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _real_secret_in_production(self) -> Settings:
        """Fail fast: a placeholder or short JWT secret would let anyone mint tokens."""
        if self.is_production and ("change-me" in self.jwt_secret or len(self.jwt_secret) < 32):
            raise ValueError(
                "JWT_SECRET must be set to a random value of 32+ characters in production"
            )
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
