"""Authentication utility helpers."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from user_agents import parse

from backend.app.core.config import settings


def parse_user_agent(user_agent_string: str) -> dict:
    """Parses a user agent string into browser, OS, and device type."""
    if not user_agent_string:
        return {
            "browser": "Unknown",
            "operating_system": "Unknown",
            "device_name": "Unknown",
        }

    ua = parse(user_agent_string)

    # Browser
    browser = (
        f"{ua.browser.family} {ua.browser.version_string}".strip()
        if ua.browser.family
        else "Unknown"
    )

    # OS
    os_name = (
        f"{ua.os.family} {ua.os.version_string}".strip() if ua.os.family else "Unknown"
    )

    # Device
    if ua.is_mobile:
        device_name = f"Mobile ({ua.device.family})"
    elif ua.is_tablet:
        device_name = f"Tablet ({ua.device.family})"
    elif ua.is_pc:
        device_name = "Desktop"
    else:
        device_name = ua.device.family if ua.device.family else "Unknown"

    return {"browser": browser, "operating_system": os_name, "device_name": device_name}


def hash_password(password: str) -> str:
    pwd_bytes = password[:72].encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password[:72].encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except ValueError:
        return False


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except jwt.PyJWTError:
        return None


def create_refresh_token() -> tuple[str, str]:
    refresh_token = str(uuid.uuid4())
    # We can hash it purely with SHA256 since it's just a random string
    refresh_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
    return refresh_token, refresh_hash


def generate_session_token() -> str:
    """Generate an opaque session identifier."""
    return secrets.token_urlsafe(32)
