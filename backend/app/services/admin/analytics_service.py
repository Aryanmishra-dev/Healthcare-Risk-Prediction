from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repositories.admin_analytics_repo import \
    AdminAnalyticsRepository
from backend.app.services.cache_service import cached


class AdminAnalyticsService:

    @staticmethod
    @cached(expire=30)
    async def get_prediction_trends(
        db: AsyncSession, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get prediction volume over time."""
        return await AdminAnalyticsRepository.get_predictions_over_time(db, days=days)

    @staticmethod
    @cached(expire=30)
    async def get_disease_distribution(db: AsyncSession) -> List[Dict[str, Any]]:
        """Get prediction distribution by disease model."""
        return await AdminAnalyticsRepository.get_disease_distribution(db)
