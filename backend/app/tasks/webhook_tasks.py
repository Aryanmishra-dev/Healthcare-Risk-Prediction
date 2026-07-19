import asyncio
import logging

from backend.app.celery_app import celery_app
from backend.app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=0,
    acks_late=True,
    autoretry_for=(),
    soft_time_limit=25,
    time_limit=50,
)
def deliver_webhook(
    self,
    webhook_event_id: str,
    webhook_url: str,
    secret: str,
    payload: dict,
    max_attempts: int,
    timeout_seconds: int,
):
    from backend.app.services.webhook_delivery_service import (
        webhook_delivery_service,
    )

    async def _deliver():
        await webhook_delivery_service.deliver(
            webhook_event_id=webhook_event_id,
            webhook_url=webhook_url,
            secret=secret,
            payload=payload,
            max_attempts=max_attempts,
            timeout_seconds=timeout_seconds,
        )

    asyncio.run(_deliver())


@celery_app.task(acks_late=True)
def retry_failed_webhooks():
    from backend.app.services.webhook_delivery_service import (
        webhook_delivery_service,
    )

    async def _retry():
        async with AsyncSessionLocal() as db:
            count = await webhook_delivery_service.retry_failed(db)
            if count:
                logger.info("retry_failed_webhooks count=%d", count)

    asyncio.run(_retry())


@celery_app.task(acks_late=True)
def cleanup_old_webhook_events():
    from backend.app.services.webhook_delivery_service import (
        webhook_delivery_service,
    )

    async def _cleanup():
        async with AsyncSessionLocal() as db:
            deleted = await webhook_delivery_service.cleanup_old_events(db)
            if deleted:
                await db.commit()
                logger.info("cleanup_old_webhook_events deleted=%d", deleted)

    asyncio.run(_cleanup())
