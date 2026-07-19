import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.usage import TenantQuota
from backend.app.services.quota_service import QuotaService


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


def _make_db_result(value):
    """Create a mock execute result with scalar_one_or_none returning value."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalar.return_value = value
    result.all.return_value = value or []
    return result


class TestQuotaService:

    @pytest.mark.anyio
    async def test_initialize_tenant_quota_creates_new(
        self, mock_db, tenant_id
    ):
        mock_db.execute = AsyncMock(return_value=_make_db_result(None))

        result = await QuotaService.initialize_tenant_quota(
            mock_db, tenant_id, rate_limit_per_minute=50, monthly_quota=5000
        )

        assert result.tenant_id == tenant_id
        assert result.rate_limit_per_minute == 50
        assert result.monthly_quota == 5000
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.anyio
    async def test_initialize_tenant_quota_returns_existing(
        self, mock_db, tenant_id
    ):
        existing = TenantQuota(
            tenant_id=tenant_id,
            rate_limit_per_minute=100,
            monthly_quota=10000,
        )
        mock_db.execute = AsyncMock(return_value=_make_db_result(existing))

        result = await QuotaService.initialize_tenant_quota(mock_db, tenant_id)

        assert result == existing
        mock_db.add.assert_not_called()

    @pytest.mark.anyio
    async def test_get_tenant_quota_returns_none_when_missing(
        self, mock_db, tenant_id
    ):
        mock_db.execute = AsyncMock(return_value=_make_db_result(None))

        result = await QuotaService.get_tenant_quota(mock_db, tenant_id)

        assert result is None

    @pytest.mark.anyio
    async def test_set_tenant_quota_updates_existing(self, mock_db, tenant_id):
        existing = TenantQuota(
            tenant_id=tenant_id,
            rate_limit_per_minute=100,
            monthly_quota=10000,
        )
        mock_db.execute = AsyncMock(return_value=_make_db_result(existing))

        result = await QuotaService.set_tenant_quota(
            mock_db,
            tenant_id,
            rate_limit_per_minute=200,
            monthly_quota=20000,
        )

        assert result.rate_limit_per_minute == 200
        assert result.monthly_quota == 20000
        mock_db.commit.assert_called_once()

    @pytest.mark.anyio
    async def test_check_quota_within_limit(self, mock_db, tenant_id):
        quota = TenantQuota(
            tenant_id=tenant_id,
            rate_limit_per_minute=100,
            monthly_quota=10000,
        )
        db_result = _make_db_result(quota)
        db_result.scalar.return_value = 50

        async def execute_side_effect(*args, **kwargs):
            return db_result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)

        result = await QuotaService.check_quota(mock_db, tenant_id)

        assert result is True

    @pytest.mark.anyio
    async def test_check_quota_exceeds_limit(self, mock_db, tenant_id):
        quota = TenantQuota(
            tenant_id=tenant_id,
            rate_limit_per_minute=100,
            monthly_quota=10000,
        )
        db_result = _make_db_result(quota)
        db_result.scalar.return_value = 10000

        async def execute_side_effect(*args, **kwargs):
            return db_result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)

        result = await QuotaService.check_quota(mock_db, tenant_id)

        assert result is False

    @pytest.mark.anyio
    async def test_increment_monthly_counter_no_redis(self, tenant_id):
        with patch(
            "backend.app.services.quota_service.cache_service"
        ) as mock_cache:
            mock_cache._redis = None
            mock_cache._enabled = False
            await QuotaService.increment_monthly_counter(tenant_id)

    @pytest.mark.anyio
    async def test_get_monthly_usage(self, mock_db, tenant_id):
        db_result = _make_db_result(None)
        db_result.scalar.return_value = 500

        async def execute_side_effect(*args, **kwargs):
            return db_result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)

        result = await QuotaService.get_monthly_usage(mock_db, tenant_id)

        assert result == 500
