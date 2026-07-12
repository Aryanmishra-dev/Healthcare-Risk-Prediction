import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.router import get_current_user
from backend.app.core.database import get_db
from backend.app.models.base import utc_now
from backend.app.models.notification import Notification
from backend.app.models.user import User
from backend.app.schemas.notification import (NotificationPaginated,
                                              NotificationQueryParams,
                                              NotificationResponse,
                                              UnreadCountResponse)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationPaginated)
async def get_notifications(
    params: NotificationQueryParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Notification).where(Notification.user_id == current_user.id)

    if params.is_read is not None:
        query = query.where(Notification.is_read == params.is_read)
    if params.category:
        query = query.where(Notification.category == params.category)
    if params.priority:
        query = query.where(Notification.priority == params.priority)
    if params.search:
        search_term = f"%{params.search}%"
        query = query.where(
            or_(
                Notification.title.ilike(search_term),
                Notification.message.ilike(search_term),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Pagination
    offset = (params.page - 1) * params.size
    query = (
        query.order_by(desc(Notification.created_at)).offset(offset).limit(params.size)
    )

    result = await db.execute(query)
    items = result.scalars().all()

    pages = math.ceil(total / params.size) if total > 0 else 0

    return NotificationPaginated(
        items=items, total=total, page=params.page, size=params.size, pages=pages
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(func.count()).where(
        Notification.user_id == current_user.id, Notification.is_read == False
    )
    count = await db.scalar(query) or 0
    return UnreadCountResponse(unread_count=count)


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notification = await db.get(Notification, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notification = await db.get(Notification, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    notification.read_at = utc_now()
    await db.commit()
    await db.refresh(notification)
    return notification


@router.patch("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)
        .values(is_read=True, read_at=utc_now())
    )
    await db.commit()
    return {"status": "success"}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notification = await db.get(Notification, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")

    await db.delete(notification)
    await db.commit()
    return None
