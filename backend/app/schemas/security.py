from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SessionResponse(BaseModel):
    id: UUID
    device_name: Optional[str] = None
    browser: Optional[str] = None
    operating_system: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    ip_address: Optional[str] = None
    login_method: str
    last_activity: datetime
    is_active: bool
    created_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class LoginHistoryResponse(BaseModel):
    id: UUID
    device_name: Optional[str] = None
    browser: Optional[str] = None
    operating_system: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    ip_address: Optional[str] = None
    login_method: str
    status: str
    login_time: datetime

    model_config = {"from_attributes": True}


class SecurityEventResponse(BaseModel):
    id: UUID
    event_type: str
    severity: str
    description: str
    metadata_payload: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminActionResponse(BaseModel):
    id: UUID
    admin_id: Optional[UUID] = None
    target_user_id: Optional[UUID] = None
    target_resource: str
    action_type: str
    metadata_payload: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DeviceResponse(BaseModel):
    device_name: str
    browser: str
    operating_system: str
    last_active: datetime


class PaginatedSessionResponse(BaseModel):
    items: List[SessionResponse]
    total: int
    page: int
    size: int
    pages: int


class PaginatedLoginHistoryResponse(BaseModel):
    items: List[LoginHistoryResponse]
    total: int
    page: int
    size: int
    pages: int


class PaginatedSecurityEventResponse(BaseModel):
    items: List[SecurityEventResponse]
    total: int
    page: int
    size: int
    pages: int


class SecurityQueryParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)
    search: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
