from typing import Any, Dict, List

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.admin_action import AdminAction
from backend.app.models.user import AuditLog, LoginHistory, SecurityEvent


class AdminAuditRepository:

    @staticmethod
    async def get_recent_admin_actions(
        db: AsyncSession, limit: int = 50
    ) -> List[AdminAction]:
        """Get recent actions performed by admins."""
        stmt = select(AdminAction).order_by(desc(AdminAction.created_at)).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_recent_security_events(
        db: AsyncSession, limit: int = 50
    ) -> List[SecurityEvent]:
        """Get recent high-severity security events."""
        stmt = (
            select(SecurityEvent).order_by(desc(SecurityEvent.created_at)).limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_recent_failed_logins(
        db: AsyncSession, limit: int = 50
    ) -> List[LoginHistory]:
        """Get recent failed login attempts."""
        stmt = (
            select(LoginHistory)
            .where(LoginHistory.status == "failed")
            .order_by(desc(LoginHistory.login_time))
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
