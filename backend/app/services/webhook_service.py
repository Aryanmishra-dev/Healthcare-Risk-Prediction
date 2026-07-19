from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.webhook import Webhook
from backend.app.services.webhook_security_service import (
    webhook_security_service,
)


class WebhookService:
    @staticmethod
    async def create_webhook(
        db: AsyncSession,
        tenant_id: UUID,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
        is_active: bool = True,
        retry_count: int = 3,
        timeout_seconds: int = 10,
        description: Optional[str] = None,
    ) -> Webhook:
        webhook = Webhook(
            tenant_id=tenant_id,
            url=url,
            secret=secret or webhook_security_service.generate_secret(),
            events=events,
            is_active=is_active,
            retry_count=retry_count,
            timeout_seconds=timeout_seconds,
            description=description,
        )
        db.add(webhook)
        await db.commit()
        await db.refresh(webhook)
        return webhook

    @staticmethod
    async def get_webhook(
        db: AsyncSession, webhook_id: UUID, tenant_id: UUID
    ) -> Optional[Webhook]:
        webhook = await db.get(Webhook, webhook_id)
        if webhook and webhook.tenant_id == tenant_id:
            return webhook
        return None

    @staticmethod
    async def list_webhooks(
        db: AsyncSession,
        tenant_id: UUID,
        page: int = 1,
        size: int = 20,
        is_active: Optional[bool] = None,
    ) -> tuple[List[Webhook], int]:
        query = select(Webhook).where(Webhook.tenant_id == tenant_id)
        count_query = select(func.count()).where(
            Webhook.tenant_id == tenant_id
        )

        if is_active is not None:
            query = query.where(Webhook.is_active == is_active)
            count_query = count_query.where(Webhook.is_active == is_active)

        total = await db.scalar(count_query) or 0
        offset = (page - 1) * size
        result = await db.execute(
            query.order_by(desc(Webhook.created_at)).offset(offset).limit(size)
        )
        items = list(result.scalars().all())
        return items, total

    @staticmethod
    async def update_webhook(
        db: AsyncSession,
        webhook_id: UUID,
        tenant_id: UUID,
        updates: Dict[str, Any],
    ) -> Optional[Webhook]:
        webhook = await WebhookService.get_webhook(db, webhook_id, tenant_id)
        if not webhook:
            return None

        for key, value in updates.items():
            if value is not None and hasattr(webhook, key):
                setattr(webhook, key, value)

        await db.commit()
        await db.refresh(webhook)
        return webhook

    @staticmethod
    async def delete_webhook(
        db: AsyncSession, webhook_id: UUID, tenant_id: UUID
    ) -> bool:
        webhook = await WebhookService.get_webhook(db, webhook_id, tenant_id)
        if not webhook:
            return False
        await db.delete(webhook)
        await db.commit()
        return True


webhook_service = WebhookService()
