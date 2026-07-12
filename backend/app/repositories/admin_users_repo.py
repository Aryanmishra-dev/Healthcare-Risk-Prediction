from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User, UserSession


class AdminUsersRepository:

    @staticmethod
    async def search_users(
        db: AsyncSession, query: str = "", limit: int = 50, offset: int = 0
    ) -> List[User]:
        """Search users by email or name."""
        stmt = select(User)
        if query:
            search = f"%{query}%"
            stmt = stmt.where(
                (User.email.ilike(search)) | (User.full_name.ilike(search))
            )

        stmt = stmt.order_by(desc(User.created_at)).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_total_users(db: AsyncSession, query: str = "") -> int:
        """Get total count for pagination."""
        stmt = select(func.count(User.id))
        if query:
            search = f"%{query}%"
            stmt = stmt.where(
                (User.email.ilike(search)) | (User.full_name.ilike(search))
            )
        return await db.scalar(stmt) or 0

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
        return await db.get(User, user_id)

    @staticmethod
    async def get_active_sessions(db: AsyncSession, user_id: UUID) -> List[UserSession]:
        """Get all unrevoked active sessions for a user."""
        stmt = (
            select(UserSession)
            .where(UserSession.user_id == user_id, UserSession.is_revoked == False)
            .order_by(desc(UserSession.last_activity))
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
