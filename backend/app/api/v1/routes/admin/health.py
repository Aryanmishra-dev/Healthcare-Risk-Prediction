from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import RequireRole
from backend.app.core.database import get_db
from backend.app.core.enums import UserRole
from backend.app.services.admin.health_service import AdminHealthService

router = APIRouter(prefix="/health", tags=["Admin Health"])


@router.get("", response_model=Dict[str, Any])
async def get_system_health(
    db: AsyncSession = Depends(get_db),
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Get comprehensive system health including DB, Redis, MLflow, and System Resources."""
    return await AdminHealthService.get_system_health(db)
