"""
Email notification provider.

Delegates actual delivery to ``email_service.email_backend``, which is
configured via the ``EMAIL_BACKEND`` environment variable:

  ``development``  → logs to console (default)
  ``smtp``         → real SMTP delivery via aiosmtplib

This file remains backward-compatible with the ``NotificationProvider``
interface used by ``NotificationDispatcher``.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.user import User
from backend.app.services.notifications.providers.base import \
    NotificationProvider

logger = logging.getLogger(__name__)


class EmailProvider(NotificationProvider):
    """
    Notification provider that delivers via email.

    Routes each notification type to the appropriate HTML template and
    dispatches via the configured email backend (SMTP or development).
    """

    async def send(
        self,
        user_id: UUID,
        notification_type: str,
        category: str,
        priority: str,
        title: str,
        message: str,
        metadata_payload: dict[str, Any] | None = None,
    ) -> bool:
        # Resolve recipient address
        async with AsyncSessionLocal() as db:
            user = await db.get(User, user_id)
            if not user or not user.email:
                logger.warning(
                    "email_provider_skip | user_id=%s | reason=no_email_address",
                    user_id,
                )
                return False
            to_address = user.email

        # Build the email via the template router in email_service
        try:
            from backend.app.core.config import settings
            from backend.app.services.email_service import (build_email,
                                                            email_backend)

            base_url = getattr(settings, "app_base_url", "http://localhost:8000")
            subject, html_body = build_email(
                notification_type=notification_type,
                title=title,
                message=message,
                metadata=metadata_payload,
                base_url=base_url,
            )

            return await email_backend.send_email(
                to_address=to_address,
                subject=subject,
                html_body=html_body,
            )

        except Exception as exc:
            logger.error(
                "email_provider_error | user_id=%s | type=%s | error=%s",
                user_id,
                notification_type,
                exc,
            )
            return False
