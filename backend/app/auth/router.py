"""SQLite-backed authentication endpoints for local and Render deployments."""

import hashlib
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from backend.app.auth.utils import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from backend.app.core.config import settings


router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = REPO_ROOT / "data" / "interim" / "audit_log.db"
BAD_USER_AGENT_MARKERS = ("python-requests", "curl/", "scrapy", "wget/", "httpie/")


def _db_path() -> Path:
    configured = os.environ.get("AUTH_DB_PATH")
    if configured:
        return Path(configured)
    return DEFAULT_DB_PATH


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                full_name TEXT,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                refresh_token_hash TEXT NOT NULL UNIQUE,
                user_agent TEXT,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
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


def _row_to_user(row: sqlite3.Row) -> UserResponse:
    return UserResponse(id=row["id"], email=row["email"], full_name=row["full_name"])


def _get_user_by_email(email: str) -> sqlite3.Row | None:
    init_auth_db()
    with _connect() as conn:
        return conn.execute(
            "SELECT id, email, full_name, password_hash FROM users WHERE email = ?",
            (email.lower(),),
        ).fetchone()


def _get_user_by_id(user_id: str) -> sqlite3.Row | None:
    init_auth_db()
    with _connect() as conn:
        return conn.execute(
            "SELECT id, email, full_name, password_hash FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> sqlite3.Row:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    payload = None
    from backend.app.auth.utils import decode_access_token

    payload = decode_access_token(credentials.credentials)
    if payload is None or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = _get_user_by_id(str(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return user


def _enforce_browser_user_agent(request: Request) -> None:
    user_agent = request.headers.get("user-agent", "").strip().lower()
    if not user_agent or any(marker in user_agent for marker in BAD_USER_AGENT_MARKERS):
        raise HTTPException(status_code=403, detail="Browser user agent required")


def _create_session(user_id: str, request: Request) -> tuple[str, str]:
    refresh_token, refresh_hash = create_refresh_token()
    session_id = str(uuid.uuid4())
    now = _utc_now()
    expires = now + timedelta(days=settings.refresh_token_expire_days)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO auth_sessions (
                id, user_id, refresh_token_hash, user_agent, created_at, expires_at, revoked
            )
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (
                session_id,
                user_id,
                refresh_hash,
                request.headers.get("user-agent", "")[:250],
                now.isoformat(),
                expires.isoformat(),
            ),
        )
        conn.commit()
    return create_access_token({"sub": user_id, "sid": session_id}), refresh_token


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(payload: RegisterRequest) -> UserResponse:
    init_auth_db()
    email = payload.email.lower()
    if _get_user_by_email(email):
        raise HTTPException(status_code=409, detail="Email is already registered")

    user_id = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO users (id, email, full_name, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                email,
                payload.full_name,
                hash_password(payload.password),
                _utc_now().isoformat(),
            ),
        )
        conn.commit()
    return UserResponse(id=user_id, email=email, full_name=payload.full_name)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request) -> TokenResponse:
    _enforce_browser_user_agent(request)
    user = _get_user_by_email(payload.email.lower())
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access_token, refresh_token = _create_session(user["id"], request)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, refresh_token: str) -> TokenResponse:
    refresh_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
    init_auth_db()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT s.id, s.user_id, s.expires_at, s.revoked, u.email
            FROM auth_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.refresh_token_hash = ?
            """,
            (refresh_hash,),
        ).fetchone()
    if row is None or row["revoked"]:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    expires_at = datetime.fromisoformat(row["expires_at"])
    if expires_at < _utc_now():
        raise HTTPException(status_code=401, detail="Refresh token expired")

    with _connect() as conn:
        conn.execute("UPDATE auth_sessions SET revoked = 1 WHERE id = ?", (row["id"],))
        conn.commit()
    access_token, new_refresh = _create_session(row["user_id"], request)
    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.get("/me", response_model=UserResponse)
async def me(user: sqlite3.Row = Depends(get_current_user)) -> UserResponse:
    return _row_to_user(user)


@router.put("/me", response_model=UserResponse)
@router.patch("/me", response_model=UserResponse)
async def update_me(payload: dict, user: sqlite3.Row = Depends(get_current_user)) -> UserResponse:
    full_name = payload.get("full_name", user["full_name"])
    with _connect() as conn:
        conn.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, user["id"]))
        conn.commit()
    updated = _get_user_by_id(user["id"])
    return _row_to_user(updated)


@router.get("/sessions")
async def sessions(user: sqlite3.Row = Depends(get_current_user)) -> list[dict]:
    init_auth_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, user_agent, created_at, expires_at, revoked
            FROM auth_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user["id"],),
        ).fetchall()
    return [dict(row) for row in rows]


@router.delete("/sessions/{session_id}")
async def revoke_session(session_id: str, user: sqlite3.Row = Depends(get_current_user)) -> dict:
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE auth_sessions SET revoked = 1 WHERE id = ? AND user_id = ?",
            (session_id, user["id"]),
        )
        conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "revoked"}


@router.get("/history")
async def history(user: sqlite3.Row = Depends(get_current_user)) -> list[dict]:
    disease_type = None
    init_auth_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, disease_model, source, risk_percentage, risk_level, created_at
            FROM prediction_audit_logs
            WHERE user_id IS NULL OR user_id = ?
            ORDER BY id DESC
            LIMIT 50
            """,
            (user["id"],),
        ).fetchall()
    return [dict(row) for row in rows if disease_type is None or row["disease_model"] == disease_type]


@router.delete("/history/{history_id}")
async def delete_history(history_id: int, user: sqlite3.Row = Depends(get_current_user)) -> dict:
    raise HTTPException(status_code=404, detail="History entry not found")


@router.get("/stats")
async def stats(user: sqlite3.Row = Depends(get_current_user)) -> dict:
    init_auth_db()
    with _connect() as conn:
        total_predictions = conn.execute(
            "SELECT COUNT(*) FROM prediction_audit_logs WHERE user_id IS NULL OR user_id = ?",
            (user["id"],),
        ).fetchone()[0]
    return {
        "total_uploads": 0,
        "total_predictions": int(total_predictions),
        "risk_breakdown": {"low": 0, "medium": 0, "high": 0},
    }


@router.get("/uploads")
async def uploads(user: sqlite3.Row = Depends(get_current_user)) -> list[dict]:
    return []


@router.get("/uploads/{upload_id}")
async def upload_detail(upload_id: str, user: sqlite3.Row = Depends(get_current_user)) -> dict:
    raise HTTPException(status_code=404, detail="Upload not found")
