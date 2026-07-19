import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.usage import TenantQuota
from backend.app.services.quota_service import QuotaService
from backend.app.services.rate_limit_service import RateLimitService
from backend.app.services.usage_analytics_service import UsageAnalyticsService


class UsageMeterService:
    """Thin orchestrator for usage metering — delegates to sub-services."""

    RATE_LIMIT_PREFIX = RateLimitService.RATE_LIMIT_PREFIX
    QUOTA_PREFIX = QuotaService.QUOTA_PREFIX
    DEFAULT_RATE_LIMIT = QuotaService.DEFAULT_RATE_LIMIT
    DEFAULT_MONTHLY_QUOTA = QuotaService.DEFAULT_MONTHLY_QUOTA

    # ── Tenant Quota Management ──────────────────────────────────────────────

    @staticmethod
    async def initialize_tenant_quota(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        rate_limit_per_minute: int = QuotaService.DEFAULT_RATE_LIMIT,
        monthly_quota: int = QuotaService.DEFAULT_MONTHLY_QUOTA,
    ) -> TenantQuota:
        return await QuotaService.initialize_tenant_quota(
            db, tenant_id, rate_limit_per_minute, monthly_quota
        )

    @staticmethod
    async def get_tenant_quota(
        db: AsyncSession, tenant_id: uuid.UUID
    ) -> Optional[TenantQuota]:
        return await QuotaService.get_tenant_quota(db, tenant_id)

    @staticmethod
    async def set_tenant_quota(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        rate_limit_per_minute: Optional[int] = None,
        monthly_quota: Optional[int] = None,
    ) -> TenantQuota:
        return await QuotaService.set_tenant_quota(
            db, tenant_id, rate_limit_per_minute, monthly_quota
        )

    # ── Rate Limiting ────────────────────────────────────────────────────────

    @staticmethod
    async def check_rate_limit(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        max_requests: Optional[int] = None,
        strategy: str = RateLimitService.STRATEGY_TOKEN_BUCKET,
    ) -> bool:
        return await RateLimitService.check_rate_limit(
            db, tenant_id, max_requests, strategy=strategy
        )

    @staticmethod
    async def get_remaining_tokens(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        max_requests: Optional[int] = None,
    ) -> int:
        return await RateLimitService.get_remaining_tokens(
            tenant_id, max_requests, db=db
        )

    # ── Usage Tracking ───────────────────────────────────────────────────────

    @staticmethod
    async def track_usage(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        endpoint: str,
        method: str = "GET",
        status_code: Optional[int] = None,
        api_key_id: Optional[uuid.UUID] = None,
    ) -> None:
        await UsageAnalyticsService.track_usage(
            db, tenant_id, endpoint, method, status_code, api_key_id
        )

    # ── Quota Checking ───────────────────────────────────────────────────────

    @staticmethod
    async def check_quota(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        max_quota: Optional[int] = None,
    ) -> bool:
        return await QuotaService.check_quota(db, tenant_id, max_quota)

    @staticmethod
    async def get_monthly_usage(
        db: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> int:
        return await QuotaService.get_monthly_usage(db, tenant_id)

    # ── Usage Analytics ──────────────────────────────────────────────────────

    @staticmethod
    async def get_usage_stats(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        since: Optional[datetime] = None,
    ) -> dict:
        return await UsageAnalyticsService.get_usage_stats(
            db, tenant_id, since
        )

    @staticmethod
    async def get_endpoint_stats(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        endpoint: str,
        since: Optional[datetime] = None,
    ) -> dict:
        return await UsageAnalyticsService.get_endpoint_stats(
            db, tenant_id, endpoint, since
        )

    @staticmethod
    async def get_daily_usage(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        days: int = 30,
    ) -> list[dict]:
        return await UsageAnalyticsService.get_daily_usage(db, tenant_id, days)
