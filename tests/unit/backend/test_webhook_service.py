import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.webhook import Webhook, WebhookEvent
from backend.app.services.webhook_delivery_service import (
    webhook_delivery_service,
)
from backend.app.services.webhook_security_service import (
    webhook_security_service,
)
from backend.app.services.webhook_service import webhook_service


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def webhook(tenant_id):
    return Webhook(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        url="https://example.com/webhook",
        secret="test-secret-32-chars-long-for-hmac",
        events=["prediction.completed", "report.ready"],
        is_active=True,
        retry_count=3,
        timeout_seconds=10,
        description="Test webhook",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


# ── WebhookService (CRUD) ──────────────────────────────────────────────


@pytest.mark.anyio
async def test_create_webhook(mock_db, tenant_id):
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    result = await webhook_service.create_webhook(
        db=mock_db,
        tenant_id=tenant_id,
        url="https://example.com/webhook",
        events=["prediction.completed"],
    )

    assert result.tenant_id == tenant_id
    assert result.url == "https://example.com/webhook"
    assert result.events == ["prediction.completed"]
    assert result.is_active is True
    assert result.retry_count == 3
    assert len(result.secret) == 64
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_get_webhook_owned_by_tenant(mock_db, webhook, tenant_id):
    mock_db.get = AsyncMock(return_value=webhook)

    result = await webhook_service.get_webhook(mock_db, webhook.id, tenant_id)

    assert result is not None
    assert result.id == webhook.id


@pytest.mark.anyio
async def test_get_webhook_wrong_tenant(mock_db, webhook):
    mock_db.get = AsyncMock(return_value=webhook)
    wrong_tenant = uuid.uuid4()

    result = await webhook_service.get_webhook(
        mock_db, webhook.id, wrong_tenant
    )

    assert result is None


@pytest.mark.anyio
async def test_get_webhook_not_found(mock_db):
    mock_db.get = AsyncMock(return_value=None)

    result = await webhook_service.get_webhook(
        mock_db, uuid.uuid4(), uuid.uuid4()
    )

    assert result is None


@pytest.mark.anyio
async def test_list_webhooks(mock_db, tenant_id):
    mock_db.scalar = AsyncMock(return_value=2)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        MagicMock(spec=Webhook),
        MagicMock(spec=Webhook),
    ]
    mock_db.execute = AsyncMock(return_value=mock_result)

    items, total = await webhook_service.list_webhooks(mock_db, tenant_id)

    assert total == 2
    assert len(items) == 2


@pytest.mark.anyio
async def test_update_webhook(mock_db, webhook, tenant_id):
    mock_db.get = AsyncMock(return_value=webhook)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    result = await webhook_service.update_webhook(
        mock_db,
        webhook.id,
        tenant_id,
        {"url": "https://new-url.com/hook"},
    )

    assert result is not None
    assert result.url == "https://new-url.com/hook"


@pytest.mark.anyio
async def test_update_webhook_not_found(mock_db):
    mock_db.get = AsyncMock(return_value=None)

    result = await webhook_service.update_webhook(
        mock_db, uuid.uuid4(), uuid.uuid4(), {"url": "test"}
    )

    assert result is None


@pytest.mark.anyio
async def test_delete_webhook(mock_db, webhook, tenant_id):
    mock_db.get = AsyncMock(return_value=webhook)
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    result = await webhook_service.delete_webhook(
        mock_db, webhook.id, tenant_id
    )

    assert result is True
    mock_db.delete.assert_awaited_once_with(webhook)


@pytest.mark.anyio
async def test_delete_webhook_not_found(mock_db):
    mock_db.get = AsyncMock(return_value=None)

    result = await webhook_service.delete_webhook(
        mock_db, uuid.uuid4(), uuid.uuid4()
    )

    assert result is False


# ── WebhookSecurityService ─────────────────────────────────────────────


class TestWebhookSecurityService:
    def test_generate_secret_length(self):
        secret = webhook_security_service.generate_secret()
        assert len(secret) == 64

    def test_generate_secret_uniqueness(self):
        s1 = webhook_security_service.generate_secret()
        s2 = webhook_security_service.generate_secret()
        assert s1 != s2

    def test_sign_and_verify(self):
        payload = b'{"event": "test"}'
        secret = webhook_security_service.generate_secret()
        signature = webhook_security_service.sign_payload(payload, secret)
        assert len(signature) == 64

        assert webhook_security_service.verify_signature(
            payload, secret, signature
        )

    def test_verify_wrong_secret(self):
        payload = b'{"event": "test"}'
        sig = webhook_security_service.sign_payload(payload, "secret-a")
        assert not webhook_security_service.verify_signature(
            payload, "secret-b", sig
        )

    def test_verify_wrong_payload(self):
        secret = webhook_security_service.generate_secret()
        sig = webhook_security_service.sign_payload(b'{"a": 1}', secret)
        assert not webhook_security_service.verify_signature(
            b'{"a": 2}', secret, sig
        )

    @pytest.mark.anyio
    async def test_rotate_secret(self, mock_db, webhook, tenant_id):
        mock_db.get = AsyncMock(return_value=webhook)
        mock_db.commit = AsyncMock()

        new_secret = await webhook_security_service.rotate_secret(
            mock_db, webhook.id, tenant_id
        )

        assert new_secret is not None
        assert len(new_secret) == 64
        assert new_secret != "test-secret-32-chars-long-for-hmac"

    @pytest.mark.anyio
    async def test_rotate_secret_not_found(self, mock_db):
        mock_db.get = AsyncMock(return_value=None)

        result = await webhook_security_service.rotate_secret(
            mock_db, uuid.uuid4(), uuid.uuid4()
        )

        assert result is None


# ── WebhookDeliveryService ─────────────────────────────────────────────


@pytest.mark.anyio
async def test_trigger_no_webhooks(mock_db, tenant_id):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    count = await webhook_delivery_service.trigger_webhook_event(
        mock_db, tenant_id, "prediction.completed", {"key": "value"}
    )

    assert count == 0


@pytest.mark.anyio
async def test_get_webhook_events(mock_db, webhook, tenant_id):
    mock_db.get = AsyncMock(return_value=webhook)
    mock_db.scalar = AsyncMock(return_value=5)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        MagicMock(spec=WebhookEvent) for _ in range(3)
    ]
    mock_db.execute = AsyncMock(return_value=mock_result)

    items, total = await webhook_delivery_service.get_webhook_events(
        mock_db, webhook.id, tenant_id
    )

    assert total == 5
    assert len(items) == 3


@pytest.mark.anyio
async def test_get_webhook_events_wrong_tenant(mock_db, webhook, tenant_id):
    mock_db.get = AsyncMock(return_value=webhook)
    wrong_tenant = uuid.uuid4()

    items, total = await webhook_delivery_service.get_webhook_events(
        mock_db, webhook.id, wrong_tenant
    )

    assert total == 0
    assert items == []


@pytest.mark.anyio
async def test_replay_webhook_event(mock_db, tenant_id):
    webhook_id = uuid.uuid4()
    event_id = uuid.uuid4()
    webhook = Webhook(
        id=webhook_id,
        tenant_id=tenant_id,
        url="https://example.com/webhook",
        secret="test-secret",
        events=["prediction.completed"],
        is_active=True,
        retry_count=3,
        timeout_seconds=10,
    )
    event = WebhookEvent(
        id=event_id,
        webhook_id=webhook_id,
        event_type="prediction.completed",
        payload={"key": "value"},
        status="delivered",
        request_url="https://example.com/webhook",
        max_attempts=3,
    )

    mock_db.get = AsyncMock()
    mock_db.get.side_effect = lambda model, id_val: (
        event
        if model == WebhookEvent and id_val == event_id
        else webhook if model == Webhook and id_val == webhook_id else None
    )
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    with patch.object(
        webhook_delivery_service.__class__, "_dispatch_delivery"
    ) as mock_dispatch:
        result = await webhook_delivery_service.replay_webhook_event(
            mock_db, event_id, tenant_id
        )

    assert result is not None
    assert result.webhook_id == webhook_id
    assert result.event_type == "prediction.completed"
    assert result.payload == {"key": "value"}
    mock_dispatch.assert_called_once()


@pytest.mark.anyio
async def test_compute_retry_delay():
    assert webhook_delivery_service.compute_retry_delay(1) == 60
    assert webhook_delivery_service.compute_retry_delay(2) == 120
    assert webhook_delivery_service.compute_retry_delay(3) == 240
    assert webhook_delivery_service.compute_retry_delay(4) == 480
    assert webhook_delivery_service.compute_retry_delay(12) == 86400


@pytest.mark.anyio
async def test_trigger_webhook_filters_by_event_type(mock_db, tenant_id):
    webhook_a = MagicMock(
        spec=Webhook,
        id=uuid.uuid4(),
        events=["prediction.completed"],
        secret="s1",
        retry_count=3,
        timeout_seconds=10,
        url="https://a.com",
    )
    webhook_b = MagicMock(
        spec=Webhook,
        id=uuid.uuid4(),
        events=["report.ready"],
        secret="s2",
        retry_count=5,
        timeout_seconds=15,
        url="https://b.com",
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        webhook_a,
        webhook_b,
    ]
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    with patch.object(
        webhook_delivery_service.__class__, "_dispatch_delivery"
    ) as mock_dispatch:
        count = await webhook_delivery_service.trigger_webhook_event(
            mock_db,
            tenant_id,
            "prediction.completed",
            {"key": "value"},
        )

    assert count == 1
    mock_dispatch.assert_called_once()
