import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from fastapi import HTTPException

from backend.app.models.user import User, UserSession, SecurityEvent, LoginHistory
from backend.app.schemas.user import UserCreate
from backend.app.auth.utils import hash_password, verify_password, create_access_token, create_refresh_token, parse_user_agent
from backend.app.core.config import settings

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()

async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()

async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    existing_user = await get_user_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(status_code=409, detail="Email is already registered")

    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        password_hash=hash_password(user_in.password),
        role="user"
    )
    db.add(user)
    await db.flush()
    return user

async def create_session(db: AsyncSession, user_id: uuid.UUID, user_agent: str, ip_address: str) -> tuple[str, str]:
    refresh_token, refresh_hash = create_refresh_token()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.refresh_token_expire_days)
    
    device_info = parse_user_agent(user_agent)
    
    session = UserSession(
        user_id=user_id,
        refresh_token_hash=refresh_hash,
        user_agent=user_agent,
        ip_address=ip_address,
        device_name=device_info["device_name"],
        browser=device_info["browser"],
        operating_system=device_info["operating_system"],
        expires_at=expires,
    )
    db.add(session)
    
    # Also log to LoginHistory
    history = LoginHistory(
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        device_name=device_info["device_name"],
        browser=device_info["browser"],
        operating_system=device_info["operating_system"],
        status="success"
    )
    db.add(history)
    
    await db.flush()

    access_token = create_access_token({"sub": str(user_id), "sid": str(session.id)})
    return access_token, refresh_token

async def log_audit(db: AsyncSession, action: str, ip_address: str | None, details: dict | None, user_id: uuid.UUID | None = None, severity: str = "info"):
    # Replaced AuditLog with SecurityEvent
    # Map old actions to new event_types where necessary
    event = SecurityEvent(
        user_id=user_id,
        event_type=action,
        severity=severity,
        description=f"Action {action} performed from IP {ip_address}" if ip_address else f"Action {action} performed",
        metadata_payload=details
    )
    db.add(event)
    await db.flush()
