from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import RequireRole
from backend.app.core.database import get_db
from backend.app.core.enums import UserRole
from backend.app.services.admin.analytics_service import AdminAnalyticsService

router = APIRouter(prefix="/analytics", tags=["Admin Analytics"])


@router.get("/predictions/trends", response_model=List[Dict[str, Any]])
async def get_prediction_trends(
    days: int = Query(
        30, ge=1, le=365, description="Number of days to analyze"
    ),
    db: AsyncSession = Depends(get_db),
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Get prediction volume over time."""
    return await AdminAnalyticsService.get_prediction_trends(db, days)


@router.get("/predictions/diseases", response_model=List[Dict[str, Any]])
async def get_disease_distribution(
    db: AsyncSession = Depends(get_db),
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Get prediction distribution by disease model."""
    return await AdminAnalyticsService.get_disease_distribution(db)
