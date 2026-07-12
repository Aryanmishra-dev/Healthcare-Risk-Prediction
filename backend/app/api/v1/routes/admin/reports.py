import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import RequireRole
from backend.app.core.database import get_db
from backend.app.core.enums import UserRole
from backend.app.schemas.report import ReportResponse
from backend.app.services.admin.report_admin_service import AdminReportsService

router = APIRouter(prefix="/reports", tags=["Admin Reports"])


@router.get("/stats", response_model=Dict[str, Any])
async def get_report_stats(
    db: AsyncSession = Depends(get_db),
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Aggregate report statuses and processing errors."""
    return await AdminReportsService.get_report_stats(db)


@router.get("/recent", response_model=List[ReportResponse])
async def get_recent_reports(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Get recently uploaded reports."""
    return await AdminReportsService.get_recent_reports(db, limit)


@router.delete("/{report_id}", response_model=Dict[str, str])
async def delete_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Admin delete report."""
    return await AdminReportsService.delete_report(db, report_id)
