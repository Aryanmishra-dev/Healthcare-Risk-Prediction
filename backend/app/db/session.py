"""
Database configuration for prediction audit logging.
Uses a lightweight SQLite database to meet healthcare compliance
without requiring external infrastructure changes.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.models.prediction import PredictionAuditLog

# ── Configuration ──────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")
REPO_ROOT = Path(__file__).resolve().parents[3]

# ── Database Setup ─────────────────────────────────────────────────────────
if DATABASE_URL.startswith("postgresql") or DATABASE_URL.startswith("postgres"):
    engine = create_engine(DATABASE_URL)
else:
    # Fallback to local SQLite
    DB_DIR = REPO_ROOT / "data" / "interim"
    DB_DIR.mkdir(parents=True, exist_ok=True)
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_DIR / 'audit_log.db'}"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create tables on import
Base.metadata.create_all(bind=engine)


# ── Dependency ─────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
