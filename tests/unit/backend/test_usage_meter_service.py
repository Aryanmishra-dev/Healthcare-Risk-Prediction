import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.usage_meter_service import UsageMeterService


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


class TestUsageMeterService:

    @pytest.mark.anyio
    async def test_initialize_tenant_quota(self, mock_db, tenant_id):
        with patch(
            "backend.app.services.usage_meter_service.QuotaService"
        ) as mock_quota:
            mock_quota.initialize_tenant_quota = AsyncMock()
            mock_quota.DEFAULT_RATE_LIMIT = 100
            mock_quota.DEFAULT_MONTHLY_QUOTA = 10000

            await UsageMeterService.initialize_tenant_quota(mock_db, tenant_id)

            mock_quota.initialize_tenant_quota.assert_called_once_with(
                mock_db, tenant_id, 100, 10000
            )

    @pytest.mark.anyio
    async def test_get_tenant_quota(self, mock_db, tenant_id):
        with patch(
            "backend.app.services.usage_meter_service.QuotaService"
        ) as mock_quota:
            mock_quota.get_tenant_quota = AsyncMock(return_value=None)

            result = await UsageMeterService.get_tenant_quota(
                mock_db, tenant_id
            )

            assert result is None
            mock_quota.get_tenant_quota.assert_called_once_with(
                mock_db, tenant_id
            )

    @pytest.mark.anyio
    async def test_set_tenant_quota(self, mock_db, tenant_id):
        with patch(
            "backend.app.services.usage_meter_service.QuotaService"
        ) as mock_quota:
            mock_quota.set_tenant_quota = AsyncMock()

            await UsageMeterService.set_tenant_quota(
                mock_db, tenant_id, rate_limit_per_minute=200
            )

            mock_quota.set_tenant_quota.assert_called_once_with(
                mock_db, tenant_id, 200, None
            )

    @pytest.mark.anyio
    async def test_check_rate_limit(self, mock_db, tenant_id):
        with patch(
            "backend.app.services.usage_meter_service.RateLimitService"
        ) as mock_rl:
            mock_rl.check_rate_limit = AsyncMock(return_value=True)
            mock_rl.STRATEGY_TOKEN_BUCKET = "token_bucket"

            result = await UsageMeterService.check_rate_limit(
                mock_db, tenant_id, max_requests=100
            )

            assert result is True
            mock_rl.check_rate_limit.assert_called_once_with(
                mock_db, tenant_id, 100, strategy="token_bucket"
            )

    @pytest.mark.anyio
    async def test_get_remaining_tokens(self, mock_db, tenant_id):
        with patch(
            "backend.app.services.usage_meter_service.RateLimitService"
        ) as mock_rl:
            mock_rl.get_remaining_tokens = AsyncMock(return_value=50)

            result = await UsageMeterService.get_remaining_tokens(
                mock_db, tenant_id
            )

            assert result == 50

    @pytest.mark.anyio
    async def test_track_usage(self, mock_db, tenant_id):
        with patch(
            "backend.app.services.usage_meter_service.UsageAnalyticsService"
        ) as mock_analytics:
            mock_analytics.track_usage = AsyncMock()

            await UsageMeterService.track_usage(
                mock_db, tenant_id, endpoint="/api/test"
            )

            mock_analytics.track_usage.assert_called_once_with(
                mock_db, tenant_id, "/api/test", "GET", None, None
            )

    @pytest.mark.anyio
    async def test_check_quota(self, mock_db, tenant_id):
        with patch(
            "backend.app.services.usage_meter_service.QuotaService"
        ) as mock_quota:
            mock_quota.check_quota = AsyncMock(return_value=True)

            result = await UsageMeterService.check_quota(mock_db, tenant_id)

            assert result is True
            mock_quota.check_quota.assert_called_once_with(
                mock_db, tenant_id, None
            )

    @pytest.mark.anyio
    async def test_get_monthly_usage(self, mock_db, tenant_id):
        with patch(
            "backend.app.services.usage_meter_service.QuotaService"
        ) as mock_quota:
            mock_quota.get_monthly_usage = AsyncMock(return_value=500)

            result = await UsageMeterService.get_monthly_usage(
                mock_db, tenant_id
            )

            assert result == 500

    @pytest.mark.anyio
    async def test_get_usage_stats(self, mock_db, tenant_id):
        with patch(
            "backend.app.services.usage_meter_service.UsageAnalyticsService"
        ) as mock_analytics:
            mock_analytics.get_usage_stats = AsyncMock(
                return_value={"total_requests": 100}
            )

            result = await UsageMeterService.get_usage_stats(
                mock_db, tenant_id
            )

            assert result["total_requests"] == 100

    @pytest.mark.anyio
    async def test_get_endpoint_stats(self, mock_db, tenant_id):
        with patch(
            "backend.app.services.usage_meter_service.UsageAnalyticsService"
        ) as mock_analytics:
            mock_analytics.get_endpoint_stats = AsyncMock(
                return_value={"endpoint": "/api/test", "total_requests": 50}
            )

            result = await UsageMeterService.get_endpoint_stats(
                mock_db, tenant_id, endpoint="/api/test"
            )

            assert result["total_requests"] == 50

    @pytest.mark.anyio
    async def test_get_daily_usage(self, mock_db, tenant_id):
        with patch(
            "backend.app.services.usage_meter_service.UsageAnalyticsService"
        ) as mock_analytics:
            mock_analytics.get_daily_usage = AsyncMock(return_value=[])

            result = await UsageMeterService.get_daily_usage(
                mock_db, tenant_id, days=7
            )

            assert result == []
            mock_analytics.get_daily_usage.assert_called_once_with(
                mock_db, tenant_id, 7
            )

    @pytest.mark.anyio
    async def test_class_constants_match_sub_services(
        self, mock_db, tenant_id
    ):
        assert UsageMeterService.DEFAULT_RATE_LIMIT == 100
        assert UsageMeterService.DEFAULT_MONTHLY_QUOTA == 10000
