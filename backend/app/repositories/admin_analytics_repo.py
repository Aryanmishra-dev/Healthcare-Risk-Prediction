from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.export import DataExport
from backend.app.models.prediction import PredictionAuditLog
from backend.app.models.report import UserReport
from backend.app.models.user import User


class AdminAnalyticsRepository:

    @staticmethod
    async def get_dashboard_overview(db: AsyncSession) -> Dict[str, Any]:
        """Get aggregate counts for the dashboard overview."""
        total_users = await db.scalar(select(func.count(User.id)))
        verified_users = await db.scalar(
            select(func.count(User.id)).where(User.is_verified.is_(True))
        )
        active_users = await db.scalar(
            select(func.count(User.id)).where(User.is_active.is_(True))
        )

        # Predictions
        total_predictions = await db.scalar(
            select(func.count(PredictionAuditLog.id))
        )

        # Reports
        total_reports = await db.scalar(select(func.count(UserReport.id)))

        # Exports
        total_exports = await db.scalar(select(func.count(DataExport.id)))

        # Latency avg (assuming latency_ms exists, else we can mock or use a
        # similar field)
        # Assuming PredictionAuditLog has execution_time_ms based on Phase 3
        # Let's check if it has execution_time_ms.
        # Note: If column is missing, this will fail. We'll use 0.0 if None.
        avg_latency = (
            await db.scalar(
                select(func.avg(PredictionAuditLog.processing_time_ms))
            )
            or 0.0
        )

        avg_confidence = (
            await db.scalar(
                select(func.avg(PredictionAuditLog.confidence_score))
            )
            or 0.0
        )

        return {
            "total_users": total_users or 0,
            "verified_users": verified_users or 0,
            "active_users": active_users or 0,
            "total_predictions": total_predictions or 0,
            "total_reports": total_reports or 0,
            "total_exports": total_exports or 0,
            "avg_prediction_latency_ms": round(avg_latency, 2),
            "avg_confidence": round(avg_confidence, 2),
        }

    @staticmethod
    async def get_predictions_over_time(
        db: AsyncSession, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get daily prediction counts for the last X days."""
        # SQLite compatible date truncation
        # For cross-compatibility in tests (SQLite) and Prod (Postgres), we
        # cast to Date
        cutoff = datetime.utcnow() - timedelta(days=days)

        stmt = (
            select(
                func.date(PredictionAuditLog.created_at).label("day"),
                func.count(PredictionAuditLog.id).label("count"),
            )
            .where(PredictionAuditLog.created_at >= cutoff)
            .group_by(func.date(PredictionAuditLog.created_at))
            .order_by("day")
        )

        result = await db.execute(stmt)
        return [
            {"date": str(row.day), "count": row.count} for row in result.all()
        ]

    @staticmethod
    async def get_disease_distribution(
        db: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """Get count of predictions by disease model."""
        stmt = (
            select(
                PredictionAuditLog.disease_model,
                func.count(PredictionAuditLog.id).label("count"),
            )
            .group_by(PredictionAuditLog.disease_model)
            .order_by(desc("count"))
        )

        result = await db.execute(stmt)
        return [
            {"disease": row.disease_model, "count": row.count}
            for row in result.all()
        ]
