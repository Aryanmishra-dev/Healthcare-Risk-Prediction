from abc import ABC, abstractmethod
from typing import Any, Dict
from uuid import UUID


class NotificationProvider(ABC):
    """Abstract interface for all notification providers."""

    @abstractmethod
    async def send(
        self,
        user_id: UUID,
        notification_type: str,
        category: str,
        priority: str,
        title: str,
        message: str,
        metadata_payload: Dict[str, Any] | None = None,
    ) -> bool:
        """Send a notification."""
        pass
