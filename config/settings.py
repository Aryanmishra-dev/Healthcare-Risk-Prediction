"""Central settings loader for local tooling and application modules."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000
    model_dir: str = "ml/models"
    database_url: str = "sqlite:///data/interim/audit_log.db"
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_per_minute: int = 60

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / "config" / ".env.example",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
