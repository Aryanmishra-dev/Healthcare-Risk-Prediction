import logging
from typing import Dict, Any
from uuid import UUID
from backend.app.services.notifications.providers.base import NotificationProvider
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.user import User

logger = logging.getLogger(__name__)

class EmailProvider(NotificationProvider):
    """Development email provider that logs to console."""
    
    async def send(
        self,
        user_id: UUID,
        notification_type: str,
        category: str,
        priority: str,
        title: str,
        message: str,
        metadata_payload: Dict[str, Any] = None
    ) -> bool:
        # Fetch the user's email address
        async with AsyncSessionLocal() as db:
            user = await db.get(User, user_id)
            if not user or not user.email:
                return False
            
            email_address = user.email
            
        # Development: Log the email instead of actually sending
        logger.info(f"--- EMAIL NOTIFICATION ---")
        logger.info(f"To: {email_address}")
        logger.info(f"Subject: {title}")
        logger.info(f"Body: {message}")
        logger.info(f"Metadata: {metadata_payload}")
        logger.info(f"--------------------------")
        
        return True
