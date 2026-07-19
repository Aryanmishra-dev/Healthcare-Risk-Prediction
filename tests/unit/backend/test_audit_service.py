import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_event import AuditEvent
from backend.app.services.audit_retention_service import (
    audit_retention_service,
)
from backend.app.services.audit_service import audit_service


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def actor_id():
    return uuid.uuid4()


# ── AuditService ───────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_log_creates_event(mock_db, tenant_id, actor_id):
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    event = await audit_service.log(
        db=mock_db,
        action="webhook.created",
        resource_type="webhook",
        resource_id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_email="admin@test.com",
        after_snapshot={"url": "https://example.com/hook"},
        severity="info",
        outcome="success",
    )

    assert event.action == "webhook.created"
    assert event.resource_type == "webhook"
    assert event.tenant_id == tenant_id
    assert event.actor_id == actor_id
    assert event.actor_email == "admin@test.com"
    assert event.after_snapshot == {"url": "https://example.com/hook"}
    assert event.severity == "info"
    assert event.outcome == "success"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_log_mutation(mock_db, tenant_id, actor_id):
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    before = {"is_active": True}
    after = {"is_active": False}

    event = await audit_service.log_mutation(
        db=mock_db,
        action="webhook.updated",
        resource_type="webhook",
        resource_id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        actor_id=actor_id,
        before=before,
        after=after,
    )

    assert event.before_snapshot == before
    assert event.after_snapshot == after
    assert event.action == "webhook.updated"
    assert event.severity == "info"
    assert event.outcome == "success"


@pytest.mark.anyio
async def test_query_filters_by_tenant(mock_db, tenant_id):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        MagicMock(spec=AuditEvent),
        MagicMock(spec=AuditEvent),
    ]
    mock_db.scalar = AsyncMock(return_value=5)
    mock_db.execute = AsyncMock(return_value=mock_result)

    items, total = await audit_service.query(
        db=mock_db, tenant_id=tenant_id, page=1, size=20
    )

    assert total == 5
    assert len(items) == 2


@pytest.mark.anyio
async def test_query_filters_by_action(mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        MagicMock(spec=AuditEvent),
    ]
    mock_db.scalar = AsyncMock(return_value=1)
    mock_db.execute = AsyncMock(return_value=mock_result)

    items, total = await audit_service.query(
        db=mock_db, action="webhook.created"
    )

    assert total == 1
    assert len(items) == 1


@pytest.mark.anyio
async def test_export_csv(mock_db, tenant_id):
    now = datetime.now(timezone.utc)
    mock_event = MagicMock(
        spec=AuditEvent,
        id=uuid.uuid4(),
        created_at=now,
        tenant_id=tenant_id,
        actor_id=uuid.uuid4(),
        actor_email="admin@test.com",
        action="webhook.created",
        resource_type="webhook",
        resource_id=str(uuid.uuid4()),
        severity="info",
        outcome="success",
        ip_address="127.0.0.1",
        user_agent="test-agent",
        request_id="req-123",
    )
    mock_db.scalar = AsyncMock(return_value=1)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_event]
    mock_db.execute = AsyncMock(return_value=mock_result)

    csv_output = await audit_service.export_csv(
        db=mock_db, tenant_id=tenant_id
    )

    assert "id,timestamp,tenant_id" in csv_output
    assert "webhook.created" in csv_output
    assert "admin@test.com" in csv_output


@pytest.mark.anyio
async def test_get_stats(mock_db, tenant_id):
    now = datetime.now(timezone.utc)

    def _make_result(value):
        r = MagicMock()
        r.scalar.return_value = value
        r.all.return_value = value
        return r

    mock_db.execute = AsyncMock(
        side_effect=[
            _make_result(2),  # count(*)
            _make_result([("webhook.created", 1)]),  # by_action
            _make_result([("info", 1)]),  # by_severity
            _make_result([("webhook", 2)]),  # by_type
            _make_result([(now, 2)]),  # by_date
        ]
    )

    stats = await audit_service.get_stats(db=mock_db, tenant_id=tenant_id)

    assert stats["total_events"] == 2
    assert stats["by_action"]["webhook.created"] == 1
    assert stats["by_severity"]["info"] == 1


@pytest.mark.anyio
async def test_log_with_request_meta(mock_db, tenant_id):
    mock_request = MagicMock()
    mock_request.headers = {
        "x-forwarded-for": "10.0.0.1, 10.0.0.2",
        "user-agent": "Mozilla/5.0",
        "x-request-id": "req-abc",
    }
    mock_request.client = None
    state = MagicMock()
    state.request_id = "req-abc"
    mock_request.state = state

    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    event = await audit_service.log(
        db=mock_db,
        action="user.login",
        resource_type="session",
        request=mock_request,
    )

    assert event.ip_address == "10.0.0.1"
    assert event.user_agent == "Mozilla/5.0"
    assert event.request_id == "req-abc"


# ── AuditRetentionService ──────────────────────────────────────────────


class TestAuditRetentionService:
    @pytest.mark.anyio
    async def test_get_policies_empty(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        policies = await audit_retention_service.get_policies(mock_db)
        assert policies == []

    @pytest.mark.anyio
    async def test_set_policy_creates_new(self, mock_db):
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        policy = await audit_retention_service.set_policy(
            mock_db, "webhook.*", 90
        )

        assert policy.action_pattern == "webhook.*"
        assert policy.retention_days == 90
        mock_db.add.assert_called_once()

    @pytest.mark.anyio
    async def test_set_policy_updates_existing(self, mock_db):
        existing = MagicMock(action_pattern="webhook.*", retention_days=365)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        policy = await audit_retention_service.set_policy(
            mock_db, "webhook.*", 90
        )

        assert policy.retention_days == 90
        assert policy.action_pattern == "webhook.*"

    @pytest.mark.anyio
    async def test_delete_policy(self, mock_db):
        policy = MagicMock()
        policy.id = uuid.uuid4()
        mock_db.get = AsyncMock(return_value=policy)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        result = await audit_retention_service.delete_policy(
            mock_db, policy.id
        )
        assert result is True
        mock_db.delete.assert_awaited_once_with(policy)

    @pytest.mark.anyio
    async def test_delete_policy_not_found(self, mock_db):
        mock_db.get = AsyncMock(return_value=None)

        result = await audit_retention_service.delete_policy(
            mock_db, uuid.uuid4()
        )
        assert result is False
