import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.base import utc_now
from backend.app.models.usage import TenantQuota, UsageRecord
from backend.app.services.cache_service import cache_service


class QuotaService:
    """Tenant quotas, monthly usage, and billing counters."""

    QUOTA_PREFIX = "quota:tenant:"
    DEFAULT_RATE_LIMIT = 100
    DEFAULT_MONTHLY_QUOTA = 10000

    @staticmethod
    async def initialize_tenant_quota(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        rate_limit_per_minute: int = DEFAULT_RATE_LIMIT,
        monthly_quota: int = DEFAULT_MONTHLY_QUOTA,
    ) -> TenantQuota:
        existing = await QuotaService.get_tenant_quota(db, tenant_id)
        if existing:
            return existing

        quota = TenantQuota(
            tenant_id=tenant_id,
            rate_limit_per_minute=rate_limit_per_minute,
            monthly_quota=monthly_quota,
        )
        db.add(quota)
        await db.commit()
        await db.refresh(quota)
        return quota

    @staticmethod
    async def get_tenant_quota(
        db: AsyncSession, tenant_id: uuid.UUID
    ) -> Optional[TenantQuota]:
        stmt = select(TenantQuota).where(TenantQuota.tenant_id == tenant_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def set_tenant_quota(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        rate_limit_per_minute: Optional[int] = None,
        monthly_quota: Optional[int] = None,
    ) -> TenantQuota:
        quota = await QuotaService.get_tenant_quota(db, tenant_id)
        if not quota:
            quota = await QuotaService.initialize_tenant_quota(
                db,
                tenant_id,
                rate_limit_per_minute or QuotaService.DEFAULT_RATE_LIMIT,
                monthly_quota or QuotaService.DEFAULT_MONTHLY_QUOTA,
            )
            return quota

        if rate_limit_per_minute is not None:
            quota.rate_limit_per_minute = rate_limit_per_minute
        if monthly_quota is not None:
            quota.monthly_quota = monthly_quota

        db.add(quota)
        await db.commit()
        await db.refresh(quota)
        return quota

    @staticmethod
    async def check_quota(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        max_quota: Optional[int] = None,
    ) -> bool:
        if max_quota is None:
            quota = await QuotaService.get_tenant_quota(db, tenant_id)
            default_quota = QuotaService.DEFAULT_MONTHLY_QUOTA
            max_quota = quota.monthly_quota if quota else default_quota

        current_month_start = utc_now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        if cache_service._redis and cache_service._enabled:
            current_month = utc_now().strftime("%Y-%m")
            key = f"{QuotaService.QUOTA_PREFIX}{tenant_id}:{current_month}"
            try:
                count_str = await cache_service._redis.get(key)
                count = int(count_str) if count_str else 0
                if count < max_quota:
                    return True
            except Exception:
                pass

        stmt = select(func.count(UsageRecord.id)).where(
            UsageRecord.tenant_id == tenant_id,
            UsageRecord.recorded_at >= current_month_start,
        )
        result = await db.execute(stmt)
        db_count = result.scalar() or 0
        return db_count < max_quota

    @staticmethod
    async def increment_monthly_counter(
        tenant_id: uuid.UUID,
    ) -> None:
        if cache_service._redis and cache_service._enabled:
            current_month = utc_now().strftime("%Y-%m")
            key = f"{QuotaService.QUOTA_PREFIX}{tenant_id}:{current_month}"
            try:
                await cache_service._redis.incr(key)
            except Exception:
                pass
