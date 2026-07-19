from celery import Celery  # type: ignore[import-untyped]
from kombu import Queue  # type: ignore[import-untyped]

from config.settings import settings

celery_app = Celery(
    "healthpredict",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Named queues for workload isolation.
# Start workers with:
#   celery -A backend.app.celery_app worker --queues=default,webhooks,audit
DEFAULT_QUEUE = "default"
WEBHOOK_QUEUE = "webhooks"
AUDIT_QUEUE = "audit"

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=30,
    task_time_limit=60,
    task_default_queue=DEFAULT_QUEUE,
    task_queues=(
        Queue(DEFAULT_QUEUE),
        Queue(WEBHOOK_QUEUE),
        Queue(AUDIT_QUEUE),
    ),
    worker_hijack_root_logger=False,
    beat_schedule={
        "retry-failed-webhooks": {
            "task": "backend.app.tasks.webhook_tasks.retry_failed_webhooks",
            "schedule": 60.0,
            "options": {"queue": WEBHOOK_QUEUE},
        },
        "cleanup-old-webhook-events": {
            "task": (
                "backend.app.tasks.webhook_tasks.cleanup_old_webhook_events"
            ),
            "schedule": 3600.0,
            "options": {"queue": WEBHOOK_QUEUE},
        },
        "apply-audit-retention": {
            "task": ("backend.app.tasks.audit_tasks.apply_audit_retention"),
            "schedule": 86400.0,
            "options": {"queue": AUDIT_QUEUE},
        },
    },
)
