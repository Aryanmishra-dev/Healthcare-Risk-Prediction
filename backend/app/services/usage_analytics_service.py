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

        by_status = (
            select(
                UsageRecord.status_code,
                func.count(UsageRecord.id),
            )
            .where(
                UsageRecord.tenant_id == tenant_id,
                UsageRecord.recorded_at >= since,
                UsageRecord.status_code.isnot(None),
            )
            .group_by(UsageRecord.status_code)
        )

        status_result = await db.execute(by_status)
        status_codes = {str(row[0]): row[1] for row in status_result}

        by_method = (
            select(
                UsageRecord.method,
                func.count(UsageRecord.id),
            )
            .where(
                UsageRecord.tenant_id == tenant_id,
                UsageRecord.recorded_at >= since,
            )
            .group_by(UsageRecord.method)
        )

        method_result = await db.execute(by_method)
        methods = {row[0]: row[1] for row in method_result}

        return {
            "total_requests": total,
            "since": since.isoformat(),
            "by_endpoint": endpoints,
            "by_method": methods,
            "by_status_code": status_codes,
        }

    @staticmethod
    async def get_endpoint_stats(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        endpoint: str,
        since: Optional[datetime] = None,
    ) -> dict:
        if since is None:
            since = utc_now() - timedelta(days=30)

        stmt = (
            select(
                UsageRecord.method,
                UsageRecord.status_code,
                func.count(UsageRecord.id),
            )
            .where(
                UsageRecord.tenant_id == tenant_id,
                UsageRecord.endpoint == endpoint,
                UsageRecord.recorded_at >= since,
            )
            .group_by(UsageRecord.method, UsageRecord.status_code)
        )

        result = await db.execute(stmt)
        rows = result.all()

        total = sum(row[2] for row in rows)
        errors = sum(
            row[2] for row in rows if row[1] is not None and row[1] >= 400
        )

        return {
            "endpoint": endpoint,
            "total_requests": total,
            "error_count": errors,
            "error_rate": round(errors / total, 4) if total > 0 else 0.0,
            "details": [
                {
                    "method": row[0],
                    "status_code": row[1],
                    "count": row[2],
                }
                for row in rows
            ],
        }

    @staticmethod
    async def get_daily_usage(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        days: int = 30,
    ) -> list[dict]:
        since = utc_now() - timedelta(days=days)
        from sqlalchemy import Date, cast

        stmt = (
            select(
                cast(UsageRecord.recorded_at, Date).label("day"),
                func.count(UsageRecord.id),
            )
            .where(
                UsageRecord.tenant_id == tenant_id,
                UsageRecord.recorded_at >= since,
            )
            .group_by(cast(UsageRecord.recorded_at, Date))
            .order_by(cast(UsageRecord.recorded_at, Date))
        )

        result = await db.execute(stmt)
        return [
            {
                "date": str(row[0]),
                "count": row[1],
            }
            for row in result
        ]

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
