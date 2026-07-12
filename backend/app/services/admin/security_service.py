from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repositories.admin_audit_repo import AdminAuditRepository
from backend.app.schemas.security import (AdminActionResponse,
                                          LoginHistoryResponse,
                                          SecurityEventResponse)
from backend.app.services.cache_service import cached


class AdminSecurityService:

    @staticmethod
    async def get_recent_admin_actions(
        db: AsyncSession, limit: int = 50
    ) -> List[AdminActionResponse]:
        """Get recent actions performed by admins."""
        actions = await AdminAuditRepository.get_recent_admin_actions(db, limit)
        return actions

    @staticmethod
    async def get_recent_security_events(
        db: AsyncSession, limit: int = 50
    ) -> List[SecurityEventResponse]:
        """Get recent high-severity security events."""
        events = await AdminAuditRepository.get_recent_security_events(db, limit)
        return events

    @staticmethod
    async def get_recent_failed_logins(
        db: AsyncSession, limit: int = 50
    ) -> List[LoginHistoryResponse]:
        """Get recent failed login attempts."""
        logins = await AdminAuditRepository.get_recent_failed_logins(db, limit)
        return logins
