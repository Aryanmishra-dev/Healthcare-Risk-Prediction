from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AuditEventResponse(BaseModel):
    id: UUID
    tenant_id: Optional[UUID] = None
    actor_id: Optional[UUID] = None
    actor_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    before_snapshot: Optional[Dict[str, Any]] = None
    after_snapshot: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    metadata_payload: Optional[Dict[str, Any]] = None
    severity: str
    outcome: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditEventPaginated(BaseModel):
    items: List[AuditEventResponse]
    total: int
    page: int
    size: int
    pages: int


class AuditStatsResponse(BaseModel):
    total_events: int
    date_range_days: int
    by_action: Dict[str, int]
    by_severity: Dict[str, int]
    by_resource_type: Dict[str, int]
    by_date: Dict[str, int]


class RetentionPolicyResponse(BaseModel):
    id: UUID
    action_pattern: str
    retention_days: int

    model_config = {"from_attributes": True}


class RetentionPolicyUpdate(BaseModel):
    action_pattern: str = Field(..., max_length=100)
    retention_days: int = Field(365, ge=1, le=3650)
