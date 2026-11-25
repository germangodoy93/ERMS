"""Application settings loaded from environment variables (12-factor).

Secrets never live in the repository: they come from the environment or a local,
git-ignored `.env` file. See `.env.example` at the repository root.
"""

from enum import StrEnum
from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
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

    # --- Authentication (docs/ERMS-HLD.md §4) ---------------------------------
    jwt_secret: SecretStr = Field(
        description="HMAC key for access tokens. Generate with: openssl rand -hex 32",
    )
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = Field(default=15, ge=1, le=60)
    session_max_hours: int = Field(default=12, ge=1, le=24 * 30)
    session_idle_minutes: int = Field(default=120, ge=5)
    refresh_reuse_grace_seconds: int = Field(
        default=30,
        ge=0,
        le=120,
        description="A just-rotated refresh token reused within this window (another tab) "
        "is rejected without revoking the session.",
    )
    login_max_attempts: int = Field(default=5, ge=1)
    login_lockout_minutes: int = Field(default=15, ge=1)
    login_ip_max_failures: int = Field(
        default=20, ge=1, description="Fallos de login por IP (todas las cuentas) por ventana"
    )
    login_ip_window_minutes: int = Field(default=15, ge=1)
    password_reset_ttl_minutes: int = Field(default=30, ge=5, le=24 * 60)
    password_min_length: int = Field(default=12, ge=8)
    refresh_cookie_secure: bool | None = Field(
        default=None, description="Defaults to true in production, false otherwise."
    )

    # --- Email ---------------------------------------------------------------
    frontend_url: str = Field(
        default="http://localhost:5173", description="Base URL used in links sent by email."
    )
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = True
    smtp_from: str = "ERMS <no-reply@erms.local>"

    # --- Attachments (ADR-023) ----------------------------------------------------------
    # With the S3_* variables set (a Railway bucket in production) photos are durable.
    # Without them files go to the server disk, which Railway erases on every deploy, so
    # the UI labels photos as a demo.
    attachments_dir: str = Field(
        default="var/attachments", description="Directory for the local storage backend."
    )
    s3_bucket: str | None = Field(default=None, description="S3 bucket name (Railway: BUCKET).")
    s3_endpoint: str | None = Field(
        default=None, description="S3 endpoint URL (Railway: ENDPOINT)."
    )
    s3_region: str = Field(default="auto", description="S3 region (Railway: REGION).")
    s3_access_key_id: str | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_addressing_style: Literal["virtual", "path"] = Field(
        default="virtual", description="Railway buckets use virtual-hosted style."
    )
    attachment_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)
    attachment_max_per_order: int = Field(default=20, ge=1, le=100)

    # --- Diagnostic agent (Sprint 4) -------------------------------------------------
    agent_download_url: str = Field(
        default="https://github.com/germangodoy93/ERMS/releases/latest/download/erms-agente.exe",
        description="Where technicians download the portable Windows agent.",
    )
    agent_pairing_minutes: int = Field(default=30, ge=5, le=240)
    agent_token_minutes: int = Field(default=15, ge=5, le=120)

    @field_validator("jwt_secret")
    @classmethod
    def _strong_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return value

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

    @model_validator(mode="after")
    def _complete_s3(self) -> Self:
        """S3 is all or nothing: half a configuration would silently fall back to demo mode."""
        values = (self.s3_bucket, self.s3_endpoint, self.s3_access_key_id)
        given = [*values, self.s3_secret_access_key]
        if any(given) and not all(given):
            raise ValueError(
                "S3 storage needs S3_BUCKET, S3_ENDPOINT, S3_ACCESS_KEY_ID and "
                "S3_SECRET_ACCESS_KEY together"
            )
        return self

    @property
    def uses_s3(self) -> bool:
        return self.s3_bucket is not None

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION

    @property
    def cookie_secure(self) -> bool:
        if self.refresh_cookie_secure is not None:
            return self.refresh_cookie_secure
        return self.is_production


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment
