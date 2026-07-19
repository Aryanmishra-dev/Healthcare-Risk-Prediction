import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.usage import UsageRecord
from backend.app.services.usage_analytics_service import UsageAnalyticsService


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def api_key_id():
    return uuid.uuid4()


def _make_result(scalar_val=None, all_val=None):
    result = MagicMock()
    result.scalar.return_value = scalar_val
    all_list = all_val or []
    result.all.return_value = all_list
    result.__iter__.return_value = iter(all_list)
    return result


class TestUsageAnalyticsService:

    @pytest.mark.anyio
    async def test_track_usage_creates_record(
        self, mock_db, tenant_id, api_key_id
    ):
        await UsageAnalyticsService.track_usage(
            mock_db,
            tenant_id,
            endpoint="/api/predict",
            method="POST",
            status_code=200,
            api_key_id=api_key_id,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert isinstance(added, UsageRecord)
        assert added.tenant_id == tenant_id
        assert added.endpoint == "/api/predict"
        assert added.method == "POST"
        assert added.status_code == 200
        assert added.api_key_id == api_key_id

    @pytest.mark.anyio
    async def test_track_usage_minimal(self, mock_db, tenant_id):
        await UsageAnalyticsService.track_usage(
            mock_db, tenant_id, endpoint="/api/predict"
        )

        mock_db.add.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert added.method == "GET"
        assert added.status_code is None
        assert added.api_key_id is None

    @pytest.mark.anyio
    async def test_get_usage_stats(self, mock_db, tenant_id):
        db_result = _make_result(
            scalar_val=100,
            all_val=[("/api/predict", 60), ("/api/health", 40)],
        )

        async def exec_side(*args, **kwargs):
            return db_result

        mock_db.execute = AsyncMock(side_effect=exec_side)

        result = await UsageAnalyticsService.get_usage_stats(
            mock_db, tenant_id
        )

        assert result["total_requests"] == 100
        assert result["by_endpoint"]["/api/predict"] == 60
        assert result["by_endpoint"]["/api/health"] == 40
        assert "since" in result

    @pytest.mark.anyio
    async def test_get_endpoint_stats(self, mock_db, tenant_id):
        db_result = _make_result(
            all_val=[("GET", 200, 80), ("POST", 201, 15), ("GET", 500, 5)],
        )

        async def exec_side(*args, **kwargs):
            return db_result

        mock_db.execute = AsyncMock(side_effect=exec_side)

        result = await UsageAnalyticsService.get_endpoint_stats(
            mock_db, tenant_id, endpoint="/api/predict"
        )

        assert result["endpoint"] == "/api/predict"
        assert result["total_requests"] == 100
        assert result["error_count"] == 5
        assert result["error_rate"] == 0.05

    @pytest.mark.anyio
    async def test_get_daily_usage(self, mock_db, tenant_id):
        from datetime import date

        db_result = _make_result(
            all_val=[(date(2026, 7, 1), 10), (date(2026, 7, 2), 20)],
        )

        async def exec_side(*args, **kwargs):
            return db_result

        mock_db.execute = AsyncMock(side_effect=exec_side)

        result = await UsageAnalyticsService.get_daily_usage(
            mock_db, tenant_id, days=7
        )

        assert len(result) == 2
        assert result[0]["date"] == "2026-07-01"
        assert result[0]["count"] == 10
        assert result[1]["date"] == "2026-07-02"
        assert result[1]["count"] == 20

    @pytest.mark.anyio
    async def test_get_usage_by_api_key(self, mock_db, api_key_id):
        db_result = _make_result(
            all_val=[
                ("/api/predict", "POST", 50),
                ("/api/health", "GET", 100),
            ],
        )

        async def exec_side(*args, **kwargs):
            return db_result

        mock_db.execute = AsyncMock(side_effect=exec_side)

        result = await UsageAnalyticsService.get_usage_by_api_key(
            mock_db, api_key_id
        )

        assert len(result) == 2
        assert result[0]["endpoint"] == "/api/predict"
        assert result[0]["method"] == "POST"
        assert result[0]["count"] == 50
