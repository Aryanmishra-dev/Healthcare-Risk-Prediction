import math
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import RequireRole
from backend.app.auth.router import get_current_user
from backend.app.core.database import get_db
from backend.app.core.enums import UserRole
from backend.app.models.audit_event import AuditEvent
from backend.app.models.tenant import Membership
from backend.app.models.user import User
from backend.app.schemas.audit import (
    AuditEventPaginated,
    AuditEventResponse,
    AuditStatsResponse,
    RetentionPolicyResponse,
    RetentionPolicyUpdate,
)
from backend.app.services.audit_retention_service import (
    audit_retention_service,
)
from backend.app.services.audit_service import audit_service

router = APIRouter(prefix="/audit", tags=["Audit"])


async def _get_tenant_id(user: User, db: AsyncSession) -> Optional[UUID]:
    if user.role in ("admin", "super_admin"):
        return None
    result = await db.execute(
        select(Membership.tenant_id)
        .where(Membership.user_id == user.id)
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get("", response_model=AuditEventPaginated)
async def list_audit_events(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    severity: Optional[str] = None,
    outcome: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await _get_tenant_id(current_user, db)
    items, total = await audit_service.query(
        db=db,
        tenant_id=tenant_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        severity=severity,
        outcome=outcome,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
    )
    pages = math.ceil(total / size) if total > 0 else 0
    return AuditEventPaginated(
        items=items, total=total, page=page, size=size, pages=pages
    )


@router.get("/export")
async def export_audit_events(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await _get_tenant_id(current_user, db)
    csv_content = await audit_service.export_csv(
        db=db,
        tenant_id=tenant_id,
        action=action,
        resource_type=resource_type,
        date_from=date_from,
        date_to=date_to,
    )
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": ("attachment; filename=audit_export.csv"),
        },
    )


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await _get_tenant_id(current_user, db)
    return await audit_service.get_stats(db=db, tenant_id=tenant_id, days=days)


@router.get("/{event_id}", response_model=AuditEventResponse)
async def get_audit_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(AuditEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Audit event not found")
    return event


@router.get(
    "/retention/policies", response_model=list[RetentionPolicyResponse]
)
async def list_retention_policies(
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await audit_retention_service.get_policies(db)


@router.put(
    "/retention/policies",
    response_model=RetentionPolicyResponse,
)
async def set_retention_policy(
    body: RetentionPolicyUpdate,
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await audit_retention_service.set_policy(
        db, body.action_pattern, body.retention_days
    )


@router.delete(
    "/retention/policies/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_retention_policy(
    policy_id: UUID,
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await audit_retention_service.delete_policy(db, policy_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail="Retention policy not found"
        )
    return None


@router.post("/retention/apply")
async def apply_retention(
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await audit_retention_service.apply_retention(db)
    return result
