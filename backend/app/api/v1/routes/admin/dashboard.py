from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import RequireRole
from backend.app.core.database import get_db
from backend.app.core.enums import UserRole
from backend.app.services.admin.dashboard_service import AdminDashboardService

router = APIRouter(prefix="/dashboard", tags=["Admin Dashboard"])


@router.get("/overview", response_model=Dict[str, Any])
async def get_overview(
    db: AsyncSession = Depends(get_db),
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Get the platform overview metrics for the admin dashboard."""
    return await AdminDashboardService.get_overview(db)


@router.get("/charts", response_model=Dict[str, Any])
async def get_charts(
    db: AsyncSession = Depends(get_db),
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Get time-series chart data for the admin dashboard."""
    return await AdminDashboardService.get_charts(db)
