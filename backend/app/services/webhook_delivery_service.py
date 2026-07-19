import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import httpx
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.celery_app import celery_app
from backend.app.models.base import utc_now
from backend.app.models.webhook import Webhook, WebhookEvent
from backend.app.services.webhook_security_service import (
    webhook_security_service,
)

logger = logging.getLogger(__name__)

MAX_RETRY_DELAY = 86400


class WebhookDeliveryService:
    @staticmethod
    def compute_retry_delay(attempt: int, base_delay: int = 60) -> int:
        delay = base_delay * (2 ** (attempt - 1))
        return int(min(delay, MAX_RETRY_DELAY))

    @staticmethod
    async def trigger_webhook_event(
        db,
        tenant_id: UUID,
        event_type: str,
        payload: Dict[str, Any],
    ) -> int:
        result = await db.execute(
            select(Webhook).where(
                Webhook.tenant_id == tenant_id,
                Webhook.is_active.is_(True),
            )
        )
        webhooks = result.scalars().all()

        triggered = 0
        for webhook in webhooks:
            if event_type not in webhook.events:
                continue

            event = WebhookEvent(
                webhook_id=webhook.id,
                event_type=event_type,
                payload=payload,
                status="pending",
                request_url=webhook.url,
                max_attempts=webhook.retry_count,
            )
            db.add(event)
            await db.flush()

            webhook.last_triggered_at = utc_now()

            WebhookDeliveryService._dispatch_delivery(event, webhook, payload)

            triggered += 1

        if triggered:
            await db.commit()
        return triggered

    @staticmethod
    def _dispatch_delivery(
        event: WebhookEvent,
        webhook: Webhook,
        payload: Dict[str, Any],
    ) -> None:
        deliver = celery_app.tasks.get(
            "backend.app.tasks.webhook_tasks.deliver_webhook"
        )
        if deliver:
            deliver.delay(
                webhook_event_id=str(event.id),
                webhook_url=webhook.url,
                secret=webhook.secret,
                payload=payload,
                max_attempts=webhook.retry_count,
                timeout_seconds=webhook.timeout_seconds,
            )

    @staticmethod
    async def get_webhook_events(
        db,
        webhook_id: UUID,
        tenant_id: UUID,
        page: int = 1,
        size: int = 20,
        status: Optional[str] = None,
    ) -> Tuple[List[WebhookEvent], int]:
        from backend.app.services.webhook_service import WebhookService

        webhook = await WebhookService.get_webhook(db, webhook_id, tenant_id)
        if not webhook:
            return [], 0

        query = select(WebhookEvent).where(
            WebhookEvent.webhook_id == webhook_id
        )
        count_query = select(func.count()).where(
            WebhookEvent.webhook_id == webhook_id
        )

        if status:
            query = query.where(WebhookEvent.status == status)
            count_query = count_query.where(WebhookEvent.status == status)

        total = await db.scalar(count_query) or 0
        offset = (page - 1) * size
        result = await db.execute(
            query.order_by(desc(WebhookEvent.created_at))
            .offset(offset)
            .limit(size)
        )
        items = list(result.scalars().all())
        return items, total

    @staticmethod
    async def replay_webhook_event(
        db, event_id: UUID, tenant_id: UUID
    ) -> Optional[WebhookEvent]:
        from backend.app.services.webhook_service import WebhookService

        event = await db.get(WebhookEvent, event_id)
        if not event:
            return None

        webhook = await WebhookService.get_webhook(
            db, event.webhook_id, tenant_id
        )
        if not webhook or not webhook.is_active:
            return None

        new_event = WebhookEvent(
            webhook_id=webhook.id,
            event_type=event.event_type,
            payload=event.payload,
            status="pending",
            request_url=webhook.url,
            max_attempts=webhook.retry_count,
        )
        db.add(new_event)
        await db.commit()
        await db.refresh(new_event)

        WebhookDeliveryService._dispatch_delivery(
            new_event, webhook, event.payload
        )

        return new_event

    @staticmethod
    async def deliver(
        webhook_event_id: str,
        webhook_url: str,
        secret: str,
        payload: Dict[str, Any],
        max_attempts: int,
        timeout_seconds: int,
    ) -> None:
        from backend.app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            event = await db.get(WebhookEvent, UUID(webhook_event_id))
            if not event:
                logger.warning(
                    "webhook_event_not_found id=%s", webhook_event_id
                )
                return

            body = json.dumps(payload, default=str).encode("utf-8")
            signature = webhook_security_service.sign_payload(body, secret)

            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Signature": f"sha256={signature}",
                "X-Webhook-Event": event.event_type,
                "X-Webhook-Delivery": str(event.id),
                "User-Agent": "HealthPredict-Webhook/1.0",
            }

            event.attempt_count += 1
            event.request_headers = headers

            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(timeout_seconds)
                ) as client:
                    resp = await client.post(
                        webhook_url, content=body, headers=headers
                    )
                    event.response_status_code = resp.status_code
                    event.response_body = resp.text[:10000]

                    if 200 <= resp.status_code < 300:
                        event.status = "delivered"
                        event.delivered_at = datetime.now(timezone.utc)
                        await db.commit()
                        logger.info(
                            "webhook_delivered event_id=%s status=%d",
                            webhook_event_id,
                            resp.status_code,
                        )
                        return
                    else:
                        event.error_message = (
                            f"HTTP {resp.status_code}: {resp.text[:500]}"
                        )
            except httpx.TimeoutException:
                event.error_message = "Request timed out"
                event.response_status_code = None
            except Exception as e:
                event.error_message = str(e)[:1000]
                event.response_status_code = None

            WebhookDeliveryService._finalize_failed(event, max_attempts)
            await db.commit()

    @staticmethod
    def _finalize_failed(event: WebhookEvent, max_attempts: int) -> None:
        if event.attempt_count >= max_attempts:
            event.status = "dead_letter"
            logger.warning(
                "webhook_dead_letter event_id=%s attempts=%d",
                event.id,
                event.attempt_count,
            )
        else:
            event.status = "failed"
            delay = WebhookDeliveryService.compute_retry_delay(
                event.attempt_count
            )
            event.next_retry_at = datetime.now(timezone.utc) + timedelta(
                seconds=delay
            )
            logger.info(
                "webhook_retry_scheduled event_id=%s attempt=%d delay=%ds",
                event.id,
                event.attempt_count,
                delay,
            )

    @staticmethod
    async def retry_failed(db: AsyncSession) -> int:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(WebhookEvent, Webhook)
            .join(Webhook, WebhookEvent.webhook_id == Webhook.id)
            .where(
                WebhookEvent.status == "failed",
                WebhookEvent.next_retry_at <= now,
                Webhook.is_active.is_(True),
            )
        )
        rows = result.all()

        for event, webhook in rows:
            deliver = celery_app.tasks.get(
                "backend.app.tasks.webhook_tasks.deliver_webhook"
            )
            if deliver:
                deliver.delay(
                    webhook_event_id=str(event.id),
                    webhook_url=webhook.url,
                    secret=webhook.secret,
                    payload=event.payload,
                    max_attempts=webhook.retry_count,
                    timeout_seconds=webhook.timeout_seconds,
                )

        return len(rows)

    @staticmethod
    async def cleanup_old_events(db) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        result = await db.execute(
            delete(WebhookEvent).where(
                WebhookEvent.created_at < cutoff,
                WebhookEvent.status.in_(["delivered", "dead_letter"]),
            )
        )
        return result.rowcount


webhook_delivery_service = WebhookDeliveryService()
