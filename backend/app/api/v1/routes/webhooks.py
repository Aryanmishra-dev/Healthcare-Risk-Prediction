import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.router import get_current_user
from backend.app.core.database import get_db
from backend.app.models.tenant import Membership
from backend.app.models.user import User
from backend.app.schemas.webhook import (
    WebhookCreate,
    WebhookEventPaginated,
    WebhookEventResponse,
    WebhookPaginated,
    WebhookResponse,
    WebhookUpdate,
)
from backend.app.services.audit_service import audit_service
from backend.app.services.webhook_delivery_service import (
    webhook_delivery_service,
)
from backend.app.services.webhook_security_service import (
    webhook_security_service,
)
from backend.app.services.webhook_service import webhook_service

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def _get_tenant_id(current_user: User, db: AsyncSession) -> UUID:
    result = await db.execute(
        select(Membership.tenant_id)
        .where(Membership.user_id == current_user.id)
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any tenant",
        )
    return row


@router.get("", response_model=WebhookPaginated)
async def list_webhooks(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await _get_tenant_id(current_user, db)
    items, total = await webhook_service.list_webhooks(
        db, tenant_id, page=page, size=size, is_active=is_active
    )
    pages = math.ceil(total / size) if total > 0 else 0
    return WebhookPaginated(
        items=items, total=total, page=page, size=size, pages=pages
    )


@router.post(
    "", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED
)
async def create_webhook(
    body: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    tenant_id = await _get_tenant_id(current_user, db)
    webhook = await webhook_service.create_webhook(
        db=db,
        tenant_id=tenant_id,
        url=body.url,
        events=body.events,
        secret=body.secret,
        is_active=body.is_active,
        retry_count=body.retry_count,
        timeout_seconds=body.timeout_seconds,
        description=body.description,
    )
    await audit_service.log(
        db=db,
        action="webhook.created",
        resource_type="webhook",
        resource_id=str(webhook.id),
        tenant_id=tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        after_snapshot={
            "url": webhook.url,
            "events": webhook.events,
            "is_active": webhook.is_active,
        },
        severity="info",
        outcome="success",
        request=request,
    )
    return webhook


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await _get_tenant_id(current_user, db)
    webhook = await webhook_service.get_webhook(db, webhook_id, tenant_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: UUID,
    body: WebhookUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    tenant_id = await _get_tenant_id(current_user, db)
    before = await webhook_service.get_webhook(db, webhook_id, tenant_id)
    if not before:
        raise HTTPException(status_code=404, detail="Webhook not found")
    before_snapshot = {
        "url": before.url,
        "events": before.events,
        "is_active": before.is_active,
        "description": before.description,
    }
    updates = body.model_dump(exclude_none=True)
    webhook = await webhook_service.update_webhook(
        db, webhook_id, tenant_id, updates
    )
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await audit_service.log_mutation(
        db=db,
        action="webhook.updated",
        resource_type="webhook",
        resource_id=str(webhook_id),
        tenant_id=tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        before=before_snapshot,
        after={
            "url": webhook.url,
            "events": webhook.events,
            "is_active": webhook.is_active,
            "description": webhook.description,
        },
        request=request,
    )
    return webhook


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    tenant_id = await _get_tenant_id(current_user, db)
    before = await webhook_service.get_webhook(db, webhook_id, tenant_id)
    if not before:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await webhook_service.delete_webhook(db, webhook_id, tenant_id)
    await audit_service.log(
        db=db,
        action="webhook.deleted",
        resource_type="webhook",
        resource_id=str(webhook_id),
        tenant_id=tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        before_snapshot={
            "url": before.url,
            "events": before.events,
            "is_active": before.is_active,
        },
        severity="warning",
        outcome="success",
        request=request,
    )
    return None


@router.post("/{webhook_id}/rotate-secret")
async def rotate_webhook_secret(
    webhook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    tenant_id = await _get_tenant_id(current_user, db)
    new_secret = await webhook_security_service.rotate_secret(
        db, webhook_id, tenant_id
    )
    if not new_secret:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await audit_service.log(
        db=db,
        action="webhook.secret_rotated",
        resource_type="webhook",
        resource_id=str(webhook_id),
        tenant_id=tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        severity="warning",
        outcome="success",
        request=request,
    )
    return {"secret": new_secret}


@router.get("/{webhook_id}/events", response_model=WebhookEventPaginated)
async def list_webhook_events(
    webhook_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await _get_tenant_id(current_user, db)
    items, total = await webhook_delivery_service.get_webhook_events(
        db, webhook_id, tenant_id, page=page, size=size, status=status
    )
    pages = math.ceil(total / size) if total > 0 else 0
    return WebhookEventPaginated(
        items=items, total=total, page=page, size=size, pages=pages
    )


@router.post("/events/{event_id}/replay", response_model=WebhookEventResponse)
async def replay_webhook_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    tenant_id = await _get_tenant_id(current_user, db)
    new_event = await webhook_delivery_service.replay_webhook_event(
        db, event_id, tenant_id
    )
    if not new_event:
        raise HTTPException(
            status_code=404, detail="Event not found or webhook inactive"
        )
    await audit_service.log(
        db=db,
        action="webhook.event_replayed",
        resource_type="webhook_event",
        resource_id=str(event_id),
        tenant_id=tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        severity="info",
        outcome="success",
        request=request,
    )
    return new_event
