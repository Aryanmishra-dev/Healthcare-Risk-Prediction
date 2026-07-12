"""Central settings loader for local tooling and application modules."""

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    # ── Runtime ──────────────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000

    # ── ML models ────────────────────────────────────────────────────────────
    model_dir: str = "ml/models"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///data/interim/audit_log.db"
    sync_database_url: str = "sqlite:///data/interim/audit_log.db"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ── Auth / JWT ───────────────────────────────────────────────────────────
    secret_key: str = Field(
        default="dev-only-healthpredict-secret-change-me",
        validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET_KEY"),
    )
    algorithm: str = Field(
        default="HS256",
        validation_alias=AliasChoices("ALGORITHM", "JWT_ALGORITHM"),
    )
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── Redis / Rate limiting ────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_per_minute: int = 60

    # ── Email ────────────────────────────────────────────────────────────────
    # EMAIL_BACKEND: "development" (default, logs only) | "smtp" (real delivery)
    email_backend: str = "development"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False        # True = implicit TLS (port 465); False = STARTTLS
    email_from_address: str = "noreply@healthpredict.ai"
    email_from_name: str = "HealthPredict AI"

    # ── Application base URL (used in email links) ───────────────────────────
    app_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
