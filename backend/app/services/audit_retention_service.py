import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_event import AuditEvent, AuditRetentionPolicy

logger = logging.getLogger(__name__)

DEFAULT_RETENTION_DAYS = 365


class AuditRetentionService:
    @staticmethod
    async def get_policies(
        db: AsyncSession,
    ) -> list[AuditRetentionPolicy]:
        result = await db.execute(
            select(AuditRetentionPolicy).order_by(
                AuditRetentionPolicy.action_pattern
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def set_policy(
        db: AsyncSession,
        action_pattern: str,
        retention_days: int,
    ) -> AuditRetentionPolicy:
        result = await db.execute(
            select(AuditRetentionPolicy).where(
                AuditRetentionPolicy.action_pattern == action_pattern
            )
        )
        policy = result.scalar_one_or_none()
        if policy:
            policy.retention_days = retention_days
        else:
            policy = AuditRetentionPolicy(
                action_pattern=action_pattern,
                retention_days=retention_days,
            )
            db.add(policy)
        await db.commit()
        await db.refresh(policy)
        return policy

    @staticmethod
    async def delete_policy(db: AsyncSession, policy_id: UUID) -> bool:
        policy = await db.get(AuditRetentionPolicy, policy_id)
        if not policy:
            return False
        await db.delete(policy)
        await db.commit()
        return True

    @staticmethod
    async def apply_retention(db: AsyncSession) -> Dict[str, Any]:
        total_purged = 0
        default_cutoff = datetime.now(timezone.utc) - timedelta(
            days=DEFAULT_RETENTION_DAYS
        )

        policies = await AuditRetentionService.get_policies(db)
        purged_by_pattern: Dict[str, int] = {}

        for policy in policies:
            cutoff = datetime.now(timezone.utc) - timedelta(
                days=policy.retention_days
            )
            result = await db.execute(
                delete(AuditEvent).where(
                    AuditEvent.action.like(policy.action_pattern),
                    AuditEvent.created_at < cutoff,
                )
            )
            count = result.rowcount  # type: ignore[attr-defined]
            if count:
                purged_by_pattern[policy.action_pattern] = count
                total_purged += count
                logger.info(
                    "audit_retention_purged pattern=%s count=%d",
                    policy.action_pattern,
                    count,
                )

        if not policies:
            result = await db.execute(
                delete(AuditEvent).where(
                    AuditEvent.created_at < default_cutoff
                )
            )
            count = result.rowcount  # type: ignore[attr-defined]
            if count:
                total_purged += count
                logger.info("audit_retention_default_purged count=%d", count)

        if total_purged:
            await db.commit()

        return {
            "total_purged": total_purged,
            "purged_by_pattern": purged_by_pattern,
        }


audit_retention_service = AuditRetentionService()
