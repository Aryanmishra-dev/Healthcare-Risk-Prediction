import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.base import utc_now
from backend.app.services.cache_service import cache_service

TOKEN_BUCKET_SCRIPT = """
-- KEYS[1] = bucket key (e.g. "rate_limit:tenant:<uuid>")
-- ARGV[1] = burst capacity (max tokens)
-- ARGV[2] = refill rate (tokens per second)
-- ARGV[3] = current timestamp in seconds

local bucket = redis.call('HMGET', KEYS[1], 'tokens', 'last_refill')
local tokens = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])

if tokens == nil then
    tokens = tonumber(ARGV[1])
    last_refill = tonumber(ARGV[3])
end

local elapsed = tonumber(ARGV[3]) - last_refill
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])

-- Refill tokens proportionally to elapsed time, capped at capacity
local new_tokens = math.min(capacity, tokens + elapsed * refill_rate)

if new_tokens >= 1 then
    local remaining = new_tokens - 1
    redis.call('HMSET', KEYS[1], 'tokens', remaining, 'last_refill', ARGV[3])
    redis.call('EXPIRE', KEYS[1], 3600)
    return {1, remaining, capacity}
else
    redis.call('HMSET', KEYS[1], 'tokens', new_tokens, 'last_refill', ARGV[3])
    redis.call('EXPIRE', KEYS[1], 3600)
    return {0, 0, capacity}
end
"""

SLIDING_WINDOW_SCRIPT = """
-- KEYS[1] = window key (e.g. "rate_limit:sliding:<tenant_id>")
-- ARGV[1] = window size in seconds
-- ARGV[2] = max requests per window
-- ARGV[3] = current timestamp in milliseconds

local window_size = tonumber(ARGV[1]) * 1000  -- convert to ms
local max_reqs = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local window_start = now - window_size

-- Remove expired entries
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, window_start)

-- Count remaining entries
local count = redis.call('ZCARD', KEYS[1])

if count < max_reqs then
    redis.call('ZADD', KEYS[1], now, now)
    redis.call('EXPIRE', KEYS[1], tonumber(ARGV[1]) + 1)
    return {1, max_reqs - count - 1}
else
    return {0, 0}
end
"""


class RateLimitService:
    """Redis-backed rate limiting with token bucket + sliding window algorithms
    and burst protection. Gracefully degrades to permissive mode when Redis is
    unavailable."""

    RATE_LIMIT_PREFIX = "rate_limit:tenant:"
    SLIDING_PREFIX = "rate_limit:sliding:"

    _bucket_sha: Optional[str] = None
    _window_sha: Optional[str] = None

    STRATEGY_TOKEN_BUCKET = "token_bucket"
    STRATEGY_SLIDING_WINDOW = "sliding_window"

    @classmethod
    async def _load_scripts(cls) -> None:
        if not cache_service._redis or not cache_service._enabled:
            return
        try:
            if cls._bucket_sha is None:
                cls._bucket_sha = await cache_service._redis.script_load(
                    TOKEN_BUCKET_SCRIPT
                )
            if cls._window_sha is None:
                cls._window_sha = await cache_service._redis.script_load(
                    SLIDING_WINDOW_SCRIPT
                )
        except Exception:
            pass

    @classmethod
    async def check_rate_limit(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        max_requests: Optional[int] = None,
        strategy: str = STRATEGY_TOKEN_BUCKET,
    ) -> bool:
        from backend.app.services.quota_service import QuotaService

        if max_requests is None:
            quota = await QuotaService.get_tenant_quota(db, tenant_id)
            max_requests = (
                quota.rate_limit_per_minute
                if quota
                else QuotaService.DEFAULT_RATE_LIMIT
            )

        if not cache_service._redis or not cache_service._enabled:
            return True

        if strategy == cls.STRATEGY_SLIDING_WINDOW:
            return await cls._check_sliding_window(tenant_id, max_requests)

        return await cls._check_token_bucket(tenant_id, max_requests)

    @classmethod
    async def _check_token_bucket(
        cls,
        tenant_id: uuid.UUID,
        max_requests: int,
    ) -> bool:
        capacity = max(1, max_requests)
        refill_rate = max_requests / 60.0  # refill over 60s

        key = f"{cls.RATE_LIMIT_PREFIX}{tenant_id}"
        now = int(utc_now().timestamp())

        try:
            await cls._load_scripts()
            if cls._bucket_sha:
                result = await cache_service._redis.evalsha(
                    cls._bucket_sha,
                    1,
                    key,
                    str(capacity),
                    str(refill_rate),
                    str(now),
                )
                allowed = result[0] == 1
                return allowed

            legacy_key = f"{key}:{now // 60}"
            count = await cache_service._redis.incr(legacy_key)
            if count == 1:
                await cache_service._redis.expire(legacy_key, 120)
            return count <= max_requests
        except Exception:
            return True

    @classmethod
    async def _check_sliding_window(
        cls,
        tenant_id: uuid.UUID,
        max_requests: int,
        window_seconds: int = 60,
    ) -> bool:
        key = f"{cls.SLIDING_PREFIX}{tenant_id}"
        now_ms = int(utc_now().timestamp() * 1000)

        try:
            await cls._load_scripts()
            if cls._window_sha:
                result = await cache_service._redis.evalsha(
                    cls._window_sha,
                    1,
                    key,
                    str(window_seconds),
                    str(max_requests),
                    str(now_ms),
                )
                return result[0] == 1

            minute = now_ms // 60000
            legacy_key = f"{cls.RATE_LIMIT_PREFIX}{tenant_id}:{minute}"
            count = await cache_service._redis.incr(legacy_key)
            if count == 1:
                await cache_service._redis.expire(legacy_key, 120)
            return count <= max_requests
        except Exception:
            return True

    @classmethod
    async def get_remaining_tokens(
        cls,
        tenant_id: uuid.UUID,
        max_requests: Optional[int] = None,
        db: Optional[AsyncSession] = None,
    ) -> int:
        from backend.app.services.quota_service import QuotaService

        if max_requests is None and db is not None:
            quota = await QuotaService.get_tenant_quota(db, tenant_id)
            max_requests = (
                quota.rate_limit_per_minute
                if quota
                else QuotaService.DEFAULT_RATE_LIMIT
            )
        if max_requests is None:
            max_requests = QuotaService.DEFAULT_RATE_LIMIT

        if not cache_service._redis or not cache_service._enabled:
            return max_requests

        key = f"{cls.RATE_LIMIT_PREFIX}{tenant_id}"
        now = int(utc_now().timestamp())

        try:
            bucket = await cache_service._redis.hmget(
                key, "tokens", "last_refill"
            )
            if bucket[0] is None:
                return min(max_requests, max_requests)

            tokens = float(bucket[0])
            last_refill = float(bucket[1]) if bucket[1] else now
            elapsed = now - last_refill
            refill_rate = max_requests / 60.0
            effective = min(max_requests, tokens + elapsed * refill_rate)
            return int(effective)
        except Exception:
            return max_requests
