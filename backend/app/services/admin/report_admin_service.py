import uuid
from typing import Any, Dict, List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.report import UserReport
from backend.app.repositories.admin_reports_repo import AdminReportsRepository
from backend.app.schemas.report import ReportResponse


class AdminReportsService:

    @staticmethod
    async def get_report_stats(db: AsyncSession) -> Dict[str, Any]:
        """Aggregate report statuses and processing errors."""
        return await AdminReportsRepository.get_report_stats(db)

    @staticmethod
    async def get_recent_reports(db: AsyncSession, limit: int = 50) -> List[UserReport]:
        """Get recently uploaded reports."""
        return await AdminReportsRepository.get_recent_reports(db, limit)

    @staticmethod
    async def delete_report(db: AsyncSession, report_id: uuid.UUID) -> Dict[str, str]:
        """Admin delete report."""
        report = await db.get(UserReport, report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Report not found"
            )

        await db.delete(report)
        await db.commit()
        return {"detail": "Report deleted successfully"}
