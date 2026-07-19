import uuid
from typing import Dict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import RequireRole
from backend.app.core.database import get_db
from backend.app.core.enums import UserRole
from backend.app.models.user import User
from backend.app.schemas.admin_user import (
    AdminUserUpdate,
    PaginatedUserResponse,
)
from backend.app.schemas.user import UserResponse
from backend.app.services.admin.users_service import AdminUsersService

router = APIRouter(prefix="/users", tags=["Admin Users"])


@router.get("", response_model=PaginatedUserResponse)
async def list_users(
    query: str = Query("", description="Search by email or name"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """List and search all users with pagination."""
    return await AdminUsersService.list_users(db, query, page, size)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    update_data: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(
        RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])
    ),
):
    """Update a user's role or status."""
    # Ensure SUPER_ADMIN if trying to make someone SUPER_ADMIN or change
    # another SUPER_ADMIN
    if (
        update_data.role == UserRole.SUPER_ADMIN.value
        and current_admin.role != UserRole.SUPER_ADMIN.value
    ):
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SUPER_ADMIN can assign SUPER_ADMIN role",
        )

    return await AdminUsersService.update_user(
        db, user_id, update_data, current_admin.id
    )


@router.post("/{user_id}/revoke-sessions", response_model=Dict[str, str])
async def revoke_user_sessions(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(
        RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])
    ),
):
    """Revoke all active sessions for a user (force logout)."""
    return await AdminUsersService.revoke_user_sessions(db, user_id)
