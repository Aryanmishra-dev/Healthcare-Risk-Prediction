import asyncio
import math
import uuid

from fastapi import HTTPException
from sqlalchemy import desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import (
    LoginHistory,
    SecurityEvent,
    UserSession,
    utc_now,
)
from backend.app.schemas.security import (
    PaginatedLoginHistoryResponse,
    PaginatedSecurityEventResponse,
    PaginatedSessionResponse,
    SecurityQueryParams,
)
from backend.app.services.notifications.notification_service import (
    notification_dispatcher,
)


async def get_active_sessions(
    db: AsyncSession, user_id: uuid.UUID, params: SecurityQueryParams
) -> PaginatedSessionResponse:
    query = select(UserSession).where(UserSession.user_id == user_id)

    if params.status == "active":
        query = query.where(
            UserSession.is_revoked.is_(False),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > utc_now(),
        )
    elif params.status == "revoked":
        query = query.where(
            or_(
                UserSession.is_revoked.is_(True),
                UserSession.revoked_at.is_not(None),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    offset = (params.page - 1) * params.size
    query = (
        query.order_by(desc(UserSession.last_activity))
        .offset(offset)
        .limit(params.size)
    )

    result = await db.execute(query)
    items = result.scalars().all()

    pages = math.ceil(total / params.size) if total > 0 else 0

    return PaginatedSessionResponse(
        items=items,  # type: ignore[arg-type]
        total=total,
        page=params.page,
        size=params.size,
        pages=pages,
    )


async def revoke_session(
    db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
) -> None:
    session = await db.get(UserSession, session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_revoked = True
    session.revoked_at = utc_now()
    await db.commit()

    asyncio.create_task(
        notification_dispatcher.dispatch(
            user_id=user_id,
            notification_type="session_revoked",
            category="Security",
            priority="LOW",
            title="Session Revoked",
            message=(
                f"A session from {session.device_name or 'Unknown'} "
                "has been revoked."
            ),
        )
    )


async def revoke_all_other_sessions(
    db: AsyncSession, user_id: uuid.UUID, current_session_id: uuid.UUID
) -> None:
    await db.execute(
        update(UserSession)
        .where(
            UserSession.user_id == user_id,
            UserSession.id != current_session_id,
            UserSession.is_revoked.is_(False),
        )
        .values(is_revoked=True, revoked_at=utc_now())
    )
    await db.commit()

    asyncio.create_task(
        notification_dispatcher.dispatch(
            user_id=user_id,
            notification_type="logout_all_devices",
            category="Security",
            priority="HIGH",
            title="Logged Out of All Devices",
            message="You have been signed out of all other devices.",
        )
    )


async def get_login_history(
    db: AsyncSession, user_id: uuid.UUID, params: SecurityQueryParams
) -> PaginatedLoginHistoryResponse:
    query = select(LoginHistory).where(LoginHistory.user_id == user_id)

    if params.status:
        query = query.where(LoginHistory.status == params.status)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    offset = (params.page - 1) * params.size
    query = (
        query.order_by(desc(LoginHistory.login_time))
        .offset(offset)
        .limit(params.size)
    )

    result = await db.execute(query)
    items = result.scalars().all()

    pages = math.ceil(total / params.size) if total > 0 else 0

    return PaginatedLoginHistoryResponse(
        items=items,  # type: ignore[arg-type]
        total=total,
        page=params.page,
        size=params.size,
        pages=pages,
    )


async def get_security_events(
    db: AsyncSession, user_id: uuid.UUID, params: SecurityQueryParams
) -> PaginatedSecurityEventResponse:
    query = select(SecurityEvent).where(SecurityEvent.user_id == user_id)

    if params.severity:
        query = query.where(SecurityEvent.severity == params.severity)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    offset = (params.page - 1) * params.size
    query = (
        query.order_by(desc(SecurityEvent.created_at))
        .offset(offset)
        .limit(params.size)
    )

    result = await db.execute(query)
    items = result.scalars().all()

    pages = math.ceil(total / params.size) if total > 0 else 0

    return PaginatedSecurityEventResponse(
        items=items,  # type: ignore[arg-type]
        total=total,
        page=params.page,
        size=params.size,
        pages=pages,
    )
