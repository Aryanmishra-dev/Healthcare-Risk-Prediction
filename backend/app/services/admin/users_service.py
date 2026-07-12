import math
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.enums import UserRole
from backend.app.models.user import User
from backend.app.repositories.admin_users_repo import AdminUsersRepository
from backend.app.schemas.admin_user import (AdminUserUpdate,
                                            PaginatedUserResponse)


class AdminUsersService:

    @staticmethod
    async def list_users(
        db: AsyncSession, query: str = "", page: int = 1, size: int = 50
    ) -> PaginatedUserResponse:
        offset = (page - 1) * size
        users = await AdminUsersRepository.search_users(
            db, query, limit=size, offset=offset
        )
        total = await AdminUsersRepository.get_total_users(db, query)

        pages = math.ceil(total / size) if size > 0 else 0

        return PaginatedUserResponse(
            items=users, total=total, page=page, size=size, pages=pages
        )

    @staticmethod
    async def update_user(
        db: AsyncSession,
        target_user_id: uuid.UUID,
        update_data: AdminUserUpdate,
        current_admin_id: uuid.UUID,
    ) -> User:
        user = await AdminUsersRepository.get_user_by_id(db, target_user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Super admin check? We will do basic role updates.
        if update_data.role is not None:
            # Ensure valid role
            try:
                role_enum = UserRole(update_data.role)
                user.role = role_enum.value
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role"
                )

        if update_data.is_active is not None:
            user.is_active = update_data.is_active

        await db.commit()
        await db.refresh(user)

        return user

    @staticmethod
    async def revoke_user_sessions(db: AsyncSession, target_user_id: uuid.UUID):
        sessions = await AdminUsersRepository.get_active_sessions(db, target_user_id)
        for session in sessions:
            session.is_revoked = True

        await db.commit()
        return {"detail": f"Revoked {len(sessions)} active sessions."}
