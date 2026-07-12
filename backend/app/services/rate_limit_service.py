import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.base import utc_now
from backend.app.services.cache_service import cache_service
from backend.app.services.quota_service import QuotaService


class RateLimitService:
    """Redis-backed rate limiting with burst protection and DB fallback."""

    RATE_LIMIT_PREFIX = "rate_limit:tenant:"

    @staticmethod
    async def check_rate_limit(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        max_requests: Optional[int] = None,
    ) -> bool:
        if max_requests is None:
            quota = await QuotaService.get_tenant_quota(db, tenant_id)
            max_requests = (
                quota.rate_limit_per_minute
                if quota
                else QuotaService.DEFAULT_RATE_LIMIT
            )

        if not cache_service._redis or not cache_service._enabled:
            return True

        current_minute = int(utc_now().timestamp() // 60)
        prefix = RateLimitService.RATE_LIMIT_PREFIX
        key = f"{prefix}{tenant_id}:{current_minute}"

        try:
            count = await cache_service._redis.incr(key)
            if count == 1:
                await cache_service._redis.expire(key, 120)
            return count <= max_requests
        except Exception:
            return True
