from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import RequireRole
from backend.app.core.database import get_db
from backend.app.core.enums import UserRole
from backend.app.schemas.security import (
    AdminActionResponse,
    LoginHistoryResponse,
    SecurityEventResponse,
)
from backend.app.services.admin.security_service import AdminSecurityService

router = APIRouter(prefix="/security", tags=["Admin Security"])


@router.get("/admin-actions", response_model=List[AdminActionResponse])
async def get_admin_actions(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Get recent actions performed by admins."""
    return await AdminSecurityService.get_recent_admin_actions(db, limit)


@router.get("/events", response_model=List[SecurityEventResponse])
async def get_security_events(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Get recent security events across the platform."""
    return await AdminSecurityService.get_recent_security_events(db, limit)


@router.get("/failed-logins", response_model=List[LoginHistoryResponse])
async def get_failed_logins(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Get recent failed login attempts."""
    return await AdminSecurityService.get_recent_failed_logins(db, limit)
