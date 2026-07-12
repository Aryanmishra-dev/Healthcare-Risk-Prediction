import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.base import utc_now
from backend.app.models.usage import UsageRecord
from backend.app.services.quota_service import QuotaService


class UsageAnalyticsService:
    """Usage history, endpoint statistics, and API analytics."""

    @staticmethod
    async def track_usage(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        endpoint: str,
        method: str = "GET",
        status_code: Optional[int] = None,
        api_key_id: Optional[uuid.UUID] = None,
    ) -> None:
        record = UsageRecord(
            tenant_id=tenant_id,
            api_key_id=api_key_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            recorded_at=utc_now(),
        )
        db.add(record)
        await db.commit()

        await QuotaService.increment_monthly_counter(tenant_id)

    @staticmethod
    async def get_usage_stats(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        since: Optional[datetime] = None,
    ) -> dict:
        if since is None:
            since = utc_now() - timedelta(days=30)

        total_stmt = select(func.count(UsageRecord.id)).where(
            UsageRecord.tenant_id == tenant_id,
            UsageRecord.recorded_at >= since,
        )
        total_result = await db.execute(total_stmt)
        total = total_result.scalar() or 0

        by_endpoint = (
            select(
                UsageRecord.endpoint,
                func.count(UsageRecord.id),
            )
            .where(
                UsageRecord.tenant_id == tenant_id,
                UsageRecord.recorded_at >= since,
            )
            .group_by(UsageRecord.endpoint)
        )

        endpoint_result = await db.execute(by_endpoint)
        endpoints = {row[0]: row[1] for row in endpoint_result}

        return {
            "total_requests": total,
            "since": since.isoformat(),
            "by_endpoint": endpoints,
        }

    @staticmethod
    async def get_usage_by_api_key(
        db: AsyncSession,
        api_key_id: uuid.UUID,
        since: Optional[datetime] = None,
    ) -> list[dict]:
        if since is None:
            since = utc_now() - timedelta(days=30)

        stmt = (
            select(
                UsageRecord.endpoint,
                UsageRecord.method,
                func.count(UsageRecord.id),
            )
            .where(
                UsageRecord.api_key_id == api_key_id,
                UsageRecord.recorded_at >= since,
            )
            .group_by(UsageRecord.endpoint, UsageRecord.method)
        )

        result = await db.execute(stmt)
        return [
            {
                "endpoint": row[0],
                "method": row[1],
                "count": row[2],
            }
            for row in result
        ]
