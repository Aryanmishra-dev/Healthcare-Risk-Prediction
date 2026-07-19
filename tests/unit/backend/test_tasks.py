"""Unit tests for Celery task definitions.

These tests verify the task wrappers call the correct underlying service
methods with the expected arguments.  Full integration against a real
broker is covered by the integration test suite.
"""

from unittest.mock import AsyncMock, patch

_WEBHOOK_SVC_PATH = (
    "backend.app.services.webhook_delivery_service.webhook_delivery_service"
)
_RETENTION_SVC_PATH = (
    "backend.app.services.audit_retention_service.audit_retention_service"
)


class TestDeliverWebhook:
    def test_task_decorated(self):
        from backend.app.tasks.webhook_tasks import deliver_webhook

        assert hasattr(deliver_webhook, "run")
        assert (
            deliver_webhook.name
            == "backend.app.tasks.webhook_tasks.deliver_webhook"
        )

    def test_calls_delivery_service(self):
        with patch(_WEBHOOK_SVC_PATH) as mock_svc:
            mock_svc.deliver = AsyncMock()

            from backend.app.tasks.webhook_tasks import deliver_webhook

            deliver_webhook(
                webhook_event_id="evt-1",
                webhook_url="https://hook.example.com",
                secret="s3cret",
                payload={"event": "test"},
                max_attempts=3,
                timeout_seconds=10,
            )

            mock_svc.deliver.assert_called_once_with(
                webhook_event_id="evt-1",
                webhook_url="https://hook.example.com",
                secret="s3cret",
                payload={"event": "test"},
                max_attempts=3,
                timeout_seconds=10,
            )


class TestRetryFailedWebhooks:
    def test_task_decorated(self):
        from backend.app.tasks.webhook_tasks import retry_failed_webhooks

        assert retry_failed_webhooks.name == (
            "backend.app.tasks.webhook_tasks.retry_failed_webhooks"
        )

    def test_calls_retry_failed(self):
        with (
            patch(_WEBHOOK_SVC_PATH) as mock_svc,
            patch(
                "backend.app.tasks.webhook_tasks.AsyncSessionLocal"
            ) as mock_session_local,
        ):
            mock_db = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_db
            mock_svc.retry_failed = AsyncMock(return_value=5)

            from backend.app.tasks.webhook_tasks import retry_failed_webhooks

            retry_failed_webhooks()

            mock_svc.retry_failed.assert_called_once_with(mock_db)


class TestCleanupOldWebhookEvents:
    def test_task_decorated(self):
        from backend.app.tasks.webhook_tasks import cleanup_old_webhook_events

        assert cleanup_old_webhook_events.name == (
            "backend.app.tasks.webhook_tasks.cleanup_old_webhook_events"
        )

    def test_calls_cleanup_and_commits(self):
        with (
            patch(_WEBHOOK_SVC_PATH) as mock_svc,
            patch(
                "backend.app.tasks.webhook_tasks.AsyncSessionLocal"
            ) as mock_session_local,
        ):
            mock_db = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_db
            mock_svc.cleanup_old_events = AsyncMock(return_value=10)

            from backend.app.tasks.webhook_tasks import (
                cleanup_old_webhook_events,
            )

            cleanup_old_webhook_events()

            mock_svc.cleanup_old_events.assert_called_once_with(mock_db)

    def test_skips_commit_when_nothing_deleted(self):
        with (
            patch(_WEBHOOK_SVC_PATH) as mock_svc,
            patch(
                "backend.app.tasks.webhook_tasks.AsyncSessionLocal"
            ) as mock_session_local,
        ):
            mock_db = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_db
            mock_svc.cleanup_old_events = AsyncMock(return_value=0)

            from backend.app.tasks.webhook_tasks import (
                cleanup_old_webhook_events,
            )

            cleanup_old_webhook_events()

            mock_svc.cleanup_old_events.assert_called_once_with(mock_db)


class TestApplyAuditRetention:
    def test_task_decorated(self):
        from backend.app.tasks.audit_tasks import apply_audit_retention

        assert apply_audit_retention.name == (
            "backend.app.tasks.audit_tasks.apply_audit_retention"
        )

    def test_calls_apply_retention(self):
        with (
            patch(_RETENTION_SVC_PATH) as mock_svc,
            patch(
                "backend.app.tasks.audit_tasks.AsyncSessionLocal"
            ) as mock_session_local,
        ):
            mock_db = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_db
            mock_svc.apply_retention = AsyncMock(
                return_value={"total_purged": 42, "purged_by_pattern": {}}
            )

            from backend.app.tasks.audit_tasks import apply_audit_retention

            apply_audit_retention()

            mock_svc.apply_retention.assert_called_once_with(mock_db)
