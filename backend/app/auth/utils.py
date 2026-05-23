"""Authentication utility helpers."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from backend.app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    password_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {**data, "type": "access", "iat": int(now.timestamp()), "exp": int(expire.timestamp())}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode an access token, returning None for invalid or expired tokens."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
    if payload.get("type") != "access":
        return None
    return payload


def create_refresh_token() -> tuple[str, str]:
    """Return a raw refresh token and its SHA-256 digest for storage."""
    raw = secrets.token_urlsafe(48)
    return raw, hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_session_token() -> str:
    """Generate an opaque session identifier."""
    return secrets.token_urlsafe(32)
