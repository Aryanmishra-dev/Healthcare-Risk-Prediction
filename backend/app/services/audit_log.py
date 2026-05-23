"""Prediction audit logging helpers."""

import asyncio
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Request


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = REPO_ROOT / "data" / "interim" / "audit_log.db"


def _db_path() -> Path:
    configured = os.environ.get("AUDIT_DB_PATH") or os.environ.get("AUTH_DB_PATH")
    return Path(configured) if configured else DEFAULT_DB_PATH


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_audit_log_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prediction_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT,
                user_id TEXT,
                disease_model TEXT NOT NULL,
                source TEXT NOT NULL,
                risk_percentage REAL NOT NULL,
                risk_level TEXT NOT NULL,
                input_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(prediction_audit_logs)").fetchall()
        }
        migrations = {
            "request_id": "ALTER TABLE prediction_audit_logs ADD COLUMN request_id TEXT",
            "user_id": "ALTER TABLE prediction_audit_logs ADD COLUMN user_id TEXT",
            "input_json": "ALTER TABLE prediction_audit_logs ADD COLUMN input_json TEXT",
            "created_at": "ALTER TABLE prediction_audit_logs ADD COLUMN created_at TEXT",
        }
        for column, statement in migrations.items():
            if column not in columns:
                conn.execute(statement)
        conn.commit()


def _write_prediction_log(
    request_id: str,
    user_id: str | None,
    disease_model: str,
    input_data: dict[str, Any],
    risk_percentage: float,
    risk_level: str,
    source: str,
) -> None:
    ensure_audit_log_db()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO prediction_audit_logs (
                request_id, user_id, disease_model, source, risk_percentage,
                risk_level, input_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                user_id,
                disease_model,
                source,
                float(risk_percentage),
                risk_level,
                json.dumps(input_data, sort_keys=True, default=str)[:4000],
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()


async def log_prediction_to_db(
    request: Request,
    disease_model: str,
    input_data: dict[str, Any],
    risk_percentage: float,
    risk_level: str,
    source: str,
    user_id: str | None = None,
) -> None:
    """Persist anonymized prediction metadata without blocking the event loop."""
    request_id = getattr(request.state, "request_id", None) or request.headers.get("x-request-id") or str(uuid.uuid4())
    await asyncio.to_thread(
        _write_prediction_log,
        request_id,
        user_id,
        disease_model,
        input_data,
        risk_percentage,
        risk_level,
        source,
    )
