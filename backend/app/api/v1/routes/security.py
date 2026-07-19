from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.router import get_current_session_id, get_current_user
from backend.app.core.database import get_db
from backend.app.models.user import User, UserSession
from backend.app.schemas.security import (
    DeviceResponse,
    PaginatedLoginHistoryResponse,
    PaginatedSecurityEventResponse,
    PaginatedSessionResponse,
    SecurityQueryParams,
)
from backend.app.services.security_service import (
    get_active_sessions,
    get_login_history,
    get_security_events,
    revoke_all_other_sessions,
    revoke_session,
)

router = APIRouter(prefix="/security", tags=["Security"])


@router.get("/sessions", response_model=PaginatedSessionResponse)
async def list_sessions(
    params: SecurityQueryParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_active_sessions(db, current_user.id, params)


@router.delete(
    "/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await revoke_session(db, current_user.id, session_id)
    return None


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_other_sessions(
    current_session_id: UUID = Depends(get_current_session_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await revoke_all_other_sessions(db, current_user.id, current_session_id)
    return None


@router.get("/login-history", response_model=PaginatedLoginHistoryResponse)
async def list_login_history(
    params: SecurityQueryParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_login_history(db, current_user.id, params)


@router.get("/events", response_model=PaginatedSecurityEventResponse)
async def list_security_events(
    params: SecurityQueryParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_security_events(db, current_user.id, params)


@router.get("/devices", response_model=list[DeviceResponse])
async def list_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get distinct devices from active sessions
    query = (
        select(
            UserSession.device_name,
            UserSession.browser,
            UserSession.operating_system,
            func.max(UserSession.last_activity).label("last_active"),
        )
        .where(
            UserSession.user_id == current_user.id,
            UserSession.is_revoked == False,
        )
        .group_by(
            UserSession.device_name,
            UserSession.browser,
            UserSession.operating_system,
        )
    )
    result = await db.execute(query)
    devices = []
    for row in result.all():
        devices.append(
            DeviceResponse(
                device_name=row.device_name or "Unknown",
                browser=row.browser or "Unknown",
                operating_system=row.operating_system or "Unknown",
                last_active=row.last_active,
            )
        )
    return devices
