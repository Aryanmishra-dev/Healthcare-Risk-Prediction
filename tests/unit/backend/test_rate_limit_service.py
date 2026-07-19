import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.usage import TenantQuota
from backend.app.services.rate_limit_service import RateLimitService


@pytest.fixture
def mock_db():
    db = AsyncMock(spec=AsyncSession)
    db_result = MagicMock()
    db_result.scalar_one_or_none.return_value = TenantQuota(
        tenant_id=uuid.uuid4(),
        rate_limit_per_minute=100,
        monthly_quota=10000,
    )
    db.execute = AsyncMock(return_value=db_result)
    return db


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


class TestRateLimitService:

    @pytest.mark.anyio
    async def test_check_rate_limit_allows_first_request(
        self, mock_db, tenant_id
    ):
        with patch(
            "backend.app.services.rate_limit_service.cache_service"
        ) as mock_cache:
            mock_cache._redis = AsyncMock()
            mock_cache._enabled = True
            mock_cache._redis.evalsha = AsyncMock(return_value=[1, 99, 100])

            result = await RateLimitService.check_rate_limit(
                mock_db, tenant_id, max_requests=100
            )

            assert result is True

    @pytest.mark.anyio
    async def test_check_rate_limit_blocks_when_exhausted(
        self, mock_db, tenant_id
    ):
        with patch(
            "backend.app.services.rate_limit_service.cache_service"
        ) as mock_cache:
            mock_cache._redis = AsyncMock()
            mock_cache._enabled = True
            mock_cache._redis.evalsha = AsyncMock(return_value=[0, 0, 100])

            result = await RateLimitService.check_rate_limit(
                mock_db, tenant_id, max_requests=100
            )

            assert result is False

    @pytest.mark.anyio
    async def test_check_rate_limit_fallback_when_no_redis(
        self, mock_db, tenant_id
    ):
        with patch(
            "backend.app.services.rate_limit_service.cache_service"
        ) as mock_cache:
            mock_cache._redis = None
            mock_cache._enabled = False

            result = await RateLimitService.check_rate_limit(
                mock_db, tenant_id, max_requests=100
            )

            assert result is True

    @pytest.mark.anyio
    async def test_check_rate_limit_fallback_on_redis_error(
        self, mock_db, tenant_id
    ):
        with patch(
            "backend.app.services.rate_limit_service.cache_service"
        ) as mock_cache:
            mock_cache._redis = AsyncMock()
            mock_cache._enabled = True
            mock_cache._redis.evalsha = AsyncMock(
                side_effect=Exception("Redis down")
            )

            result = await RateLimitService.check_rate_limit(
                mock_db, tenant_id, max_requests=100
            )

            assert result is True

    @pytest.mark.anyio
    async def test_check_rate_limit_sliding_window(self, mock_db, tenant_id):
        with patch(
            "backend.app.services.rate_limit_service.cache_service"
        ) as mock_cache:
            mock_cache._redis = AsyncMock()
            mock_cache._enabled = True
            mock_cache._redis.evalsha = AsyncMock(return_value=[1, 99])

            result = await RateLimitService.check_rate_limit(
                mock_db,
                tenant_id,
                max_requests=100,
                strategy=RateLimitService.STRATEGY_SLIDING_WINDOW,
            )

            assert result is True

    @pytest.mark.anyio
    async def test_get_remaining_tokens(self, mock_db, tenant_id):
        with patch(
            "backend.app.services.rate_limit_service.cache_service"
        ) as mock_cache:
            mock_cache._redis = AsyncMock()
            mock_cache._enabled = True
            mock_cache._redis.hmget = AsyncMock(
                return_value=[b"50", b"1000000"]
            )

            remaining = await RateLimitService.get_remaining_tokens(
                tenant_id, max_requests=100, db=mock_db
            )

            assert remaining >= 0

    @pytest.mark.anyio
    async def test_legacy_counter_fallback(self, mock_db, tenant_id):
        RateLimitService._bucket_sha = None
        RateLimitService._window_sha = None
        with patch(
            "backend.app.services.rate_limit_service.cache_service"
        ) as mock_cache:
            mock_cache._redis = AsyncMock()
            mock_cache._enabled = True
            mock_cache._redis.script_load = AsyncMock(
                side_effect=Exception("No scripting")
            )
            mock_cache._redis.incr = AsyncMock(return_value=1)
            mock_cache._redis.expire = AsyncMock(return_value=True)

            result = await RateLimitService.check_rate_limit(
                mock_db, tenant_id, max_requests=100
            )

            assert result is True

    @pytest.mark.anyio
    async def test_load_scripts(self):
        with patch(
            "backend.app.services.rate_limit_service.cache_service"
        ) as mock_cache:
            mock_cache._redis = AsyncMock()
            mock_cache._enabled = True
            RateLimitService._bucket_sha = None
            RateLimitService._window_sha = None

            await RateLimitService._load_scripts()

            assert RateLimitService._bucket_sha is not None
            assert RateLimitService._window_sha is not None
