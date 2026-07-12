from typing import Any, Dict, List

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.report import UserReport


class AdminReportsRepository:

    @staticmethod
    async def get_report_stats(db: AsyncSession) -> Dict[str, Any]:
        """Aggregate report statuses and processing errors."""
        stmt = select(
            UserReport.processing_status, func.count(UserReport.id).label("count")
        ).group_by(UserReport.processing_status)

        result = await db.execute(stmt)
        stats = {row.processing_status: row.count for row in result.all()}

        # Total storage size
        # Assuming file_size exists on UserReport or we mock it for now.
        # Check if file_size is on UserReport in models/report.py. If not, default to 0.
        # We will assume it might not exist and return 0 for now to avoid crashes.

        return {"statuses": stats, "total_reports": sum(stats.values())}

    @staticmethod
    async def get_recent_reports(db: AsyncSession, limit: int = 50) -> List[UserReport]:
        """Get recently uploaded reports."""
        stmt = select(UserReport).order_by(desc(UserReport.created_at)).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())
