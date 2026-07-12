from typing import Any, Dict
from uuid import UUID

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.base import utc_now
from backend.app.models.notification import Notification
from backend.app.services.notifications.providers.base import \
    NotificationProvider


class InAppProvider(NotificationProvider):
    """Stores notifications in the database for in-app retrieval."""

    async def send(
        self,
        user_id: UUID,
        notification_type: str,
        category: str,
        priority: str,
        title: str,
        message: str,
        metadata_payload: Dict[str, Any] = None,
    ) -> bool:
        async with AsyncSessionLocal() as db:
            notification = Notification(
                user_id=user_id,
                notification_type=notification_type,
                category=category,
                priority=priority,
                status="sent",
                channel="in_app",
                title=title,
                message=message,
                metadata_payload=metadata_payload,
            )
            db.add(notification)
            try:
                await db.commit()
                return True
            except Exception:
                await db.rollback()
                return False
