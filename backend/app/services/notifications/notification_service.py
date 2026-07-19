import logging
from typing import Any, Dict
from uuid import UUID

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.user import UserSettings
from backend.app.services.notifications.providers.email import EmailProvider
from backend.app.services.notifications.providers.in_app import InAppProvider

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    def __init__(self):
        self.in_app_provider = InAppProvider()
        self.email_provider = EmailProvider()

    async def dispatch(
        self,
        user_id: UUID,
        notification_type: str,
        category: str,
        priority: str,
        title: str,
        message: str,
        metadata_payload: Dict[str, Any] | None = None,
        force_email: bool = False,
    ):
        """
        Main entry point for dispatching notifications.
        Intended to be run via BackgroundTasks (or Celery in the future).
        """
        try:
            async with AsyncSessionLocal() as db:
                settings = await db.get(UserSettings, user_id)
                if not settings:
                    logger.warning(
                        f"No settings found for user {user_id}. "
                        "Using defaults."
                    )
                    settings = UserSettings(user_id=user_id)  # Using defaults

            # 1. Determine which channels to use based on preferences
            # and category
            send_in_app = settings.in_app_notifications
            send_email = settings.email_notifications or force_email

            # Override based on category
            if category == "Security" and not settings.security_alerts:
                send_in_app = False
                send_email = False
            if category == "Prediction" and not settings.prediction_alerts:
                send_in_app = False
                send_email = False
            if category == "System" and not settings.system_notifications:
                send_in_app = False
                send_email = False

            # 2. Dispatch
            if send_in_app:
                await self.in_app_provider.send(
                    user_id=user_id,
                    notification_type=notification_type,
                    category=category,
                    priority=priority,
                    title=title,
                    message=message,
                    metadata_payload=metadata_payload,
                )

            if send_email:
                await self.email_provider.send(
                    user_id=user_id,
                    notification_type=notification_type,
                    category=category,
                    priority=priority,
                    title=title,
                    message=message,
                    metadata_payload=metadata_payload,
                )
        except Exception as e:
            logger.error(f"Failed to dispatch notification: {e}")


notification_dispatcher = NotificationDispatcher()
