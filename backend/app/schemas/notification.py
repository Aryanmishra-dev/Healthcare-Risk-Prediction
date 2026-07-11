from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field

class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    notification_type: str
    category: str
    priority: str
    status: str
    channel: str
    title: str
    message: str
    is_read: bool
    read_at: Optional[datetime] = None
    metadata_payload: Optional[Dict[str, Any]] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NotificationPaginated(BaseModel):
    items: List[NotificationResponse]
    total: int
    page: int
    size: int
    pages: int


class NotificationQueryParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)
    is_read: Optional[bool] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    search: Optional[str] = None


class UnreadCountResponse(BaseModel):
    unread_count: int
