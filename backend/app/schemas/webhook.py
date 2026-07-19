from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WebhookCreate(BaseModel):
    url: str = Field(..., max_length=1024)
    events: List[str] = Field(..., min_length=1)
    secret: Optional[str] = None
    is_active: bool = True
    retry_count: int = Field(3, ge=0, le=10)
    timeout_seconds: int = Field(10, ge=1, le=60)
    description: Optional[str] = Field(None, max_length=255)


class WebhookUpdate(BaseModel):
    url: Optional[str] = Field(None, max_length=1024)
    events: Optional[List[str]] = None
    secret: Optional[str] = None
    is_active: Optional[bool] = None
    retry_count: Optional[int] = Field(None, ge=0, le=10)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=60)
    description: Optional[str] = Field(None, max_length=255)


class WebhookResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    url: str
    events: List[Any]
    is_active: bool
    retry_count: int
    timeout_seconds: int
    description: Optional[str] = None
    last_triggered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebhookEventResponse(BaseModel):
    id: UUID
    webhook_id: UUID
    event_type: str
    payload: Dict[str, Any]
    status: str
    request_url: str
    response_status_code: Optional[int] = None
    response_body: Optional[str] = None
    attempt_count: int
    max_attempts: int
    next_retry_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookPaginated(BaseModel):
    items: List[WebhookResponse]
    total: int
    page: int
    size: int
    pages: int


class WebhookEventPaginated(BaseModel):
    items: List[WebhookEventResponse]
    total: int
    page: int
    size: int
    pages: int
