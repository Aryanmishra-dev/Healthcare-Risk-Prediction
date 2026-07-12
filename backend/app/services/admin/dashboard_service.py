from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repositories.admin_analytics_repo import \
    AdminAnalyticsRepository
from backend.app.services.cache_service import cached


class AdminDashboardService:

    @staticmethod
    @cached(expire=30)
    async def get_overview(db: AsyncSession) -> Dict[str, Any]:
        """
        Get the dashboard overview using cached DB aggregations.
        The @cached decorator uses the method name and kwargs (if any) as cache key.
        Since db is an object, it won't be included in the cache key directly.
        Wait, our cache decorator currently excludes complex objects, which is correct.
        """
        return await AdminAnalyticsRepository.get_dashboard_overview(db)

    @staticmethod
    @cached(expire=30)
    async def get_charts(db: AsyncSession) -> Dict[str, Any]:
        """
        Get charting data (predictions over time, disease distribution, etc.).
        """
        predictions_trend = await AdminAnalyticsRepository.get_predictions_over_time(
            db, days=30
        )
        disease_dist = await AdminAnalyticsRepository.get_disease_distribution(db)

        return {
            "predictions_trend": predictions_trend,
            "disease_distribution": disease_dist,
        }
