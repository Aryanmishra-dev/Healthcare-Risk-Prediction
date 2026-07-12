import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ApiKeyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: Optional[List[str]] = Field(default=["read-only"])


class ApiKeyCreate(ApiKeyBase):
    expires_at: Optional[datetime] = None


class ApiKeyResponse(ApiKeyBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_by: Optional[uuid.UUID] = None
    key_prefix: str
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyCreateResponse(ApiKeyResponse):
    raw_key: str = Field(
        ...,
        description="The plaintext API key. Store this securely, it will never be shown again.",
    )


class ApiKeyRotateRequest(BaseModel):
    """Request body for rotating an API key (currently empty, reserved for future options)."""
