"""Application settings loaded from environment variables (12-factor).

Secrets never live in the repository: they come from the environment or a local,
git-ignored `.env` file. See `.env.example` at the repository root.
"""

from enum import StrEnum
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ERMS – Electronic Repair Management System"
    app_version: str = "0.1.0"
    environment: Environment = Environment.DEVELOPMENT
    api_prefix: str = "/api/v1"

    database_url: str = Field(
        description="PostgreSQL URL. Plain postgres:// URLs (e.g. from Railway) are accepted.",
    )
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_connect_timeout_seconds: int = Field(default=5, ge=1, le=60)

    redis_url: str | None = Field(
        default=None,
        description="Redis URL. Optional until Celery workers are introduced.",
    )

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    log_level: str = "INFO"
    log_json: bool = True

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, value: str) -> str:
        """Force the psycopg 3 driver regardless of the URL scheme provided."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value.removeprefix(prefix)
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accept a comma-separated string, as environment variables are flat."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment
