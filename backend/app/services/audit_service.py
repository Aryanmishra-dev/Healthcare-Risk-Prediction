import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import Request
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_event import AuditEvent

logger = logging.getLogger(__name__)

DEFAULT_RETENTION_DAYS = 365


class AuditService:
    @staticmethod
    def _extract_request_meta(
        request: Optional[Request] = None,
    ) -> Dict[str, Optional[str]]:
        if not request:
            return {"ip": None, "ua": None, "rid": None}
        ip = request.headers.get("x-forwarded-for", "").split(",")[
            0
        ].strip() or (request.client.host if request.client else None)
        ua = request.headers.get("user-agent")
        rid = getattr(
            request.state, "request_id", None
        ) or request.headers.get("x-request-id")
        return {"ip": ip, "ua": ua, "rid": rid}

    @staticmethod
    async def log(
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        tenant_id: Optional[UUID] = None,
        actor_id: Optional[UUID] = None,
        actor_email: Optional[str] = None,
        before_snapshot: Optional[Dict[str, Any]] = None,
        after_snapshot: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        metadata_payload: Optional[Dict[str, Any]] = None,
        severity: str = "info",
        outcome: str = "success",
    ) -> AuditEvent:
        meta = AuditService._extract_request_meta(request)
        event = AuditEvent(
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            ip_address=meta["ip"],
            user_agent=meta["ua"],
            request_id=meta["rid"],
            metadata_payload=metadata_payload,
            severity=severity,
            outcome=outcome,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def log_mutation(
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        tenant_id: Optional[UUID] = None,
        actor_id: Optional[UUID] = None,
        actor_email: Optional[str] = None,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        metadata_payload: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        return await AuditService.log(
            db=db,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            before_snapshot=before,
            after_snapshot=after,
            request=request,
            metadata_payload=metadata_payload,
            severity="info",
            outcome="success",
        )

    @staticmethod
    async def query(
        db: AsyncSession,
        tenant_id: Optional[UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        actor_id: Optional[UUID] = None,
        severity: Optional[str] = None,
        outcome: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        size: int = 50,
    ) -> Tuple[List[AuditEvent], int]:
        query = select(AuditEvent)
        count_query = select(func.count(AuditEvent.id))

        if tenant_id:
            query = query.where(AuditEvent.tenant_id == tenant_id)
            count_query = count_query.where(AuditEvent.tenant_id == tenant_id)
        if action:
            query = query.where(AuditEvent.action == action)
            count_query = count_query.where(AuditEvent.action == action)
        if resource_type:
            query = query.where(AuditEvent.resource_type == resource_type)
            count_query = count_query.where(
                AuditEvent.resource_type == resource_type
            )
        if resource_id:
            query = query.where(AuditEvent.resource_id == resource_id)
            count_query = count_query.where(
                AuditEvent.resource_id == resource_id
            )
        if actor_id:
            query = query.where(AuditEvent.actor_id == actor_id)
            count_query = count_query.where(AuditEvent.actor_id == actor_id)
        if severity:
            query = query.where(AuditEvent.severity == severity)
            count_query = count_query.where(AuditEvent.severity == severity)
        if outcome:
            query = query.where(AuditEvent.outcome == outcome)
            count_query = count_query.where(AuditEvent.outcome == outcome)
        if date_from:
            query = query.where(AuditEvent.created_at >= date_from)
            count_query = count_query.where(AuditEvent.created_at >= date_from)
        if date_to:
            query = query.where(AuditEvent.created_at <= date_to)
            count_query = count_query.where(AuditEvent.created_at <= date_to)

        total = await db.scalar(count_query) or 0
        offset = (page - 1) * size
        result = await db.execute(
            query.order_by(desc(AuditEvent.created_at))
            .offset(offset)
            .limit(size)
        )
        items = list(result.scalars().all())
        return items, total

    @staticmethod
    async def export_csv(
        db: AsyncSession,
        tenant_id: Optional[UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> str:
        items, _ = await AuditService.query(
            db=db,
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            date_from=date_from,
            date_to=date_to,
            page=1,
            size=10000,
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "timestamp",
                "tenant_id",
                "actor_id",
                "actor_email",
                "action",
                "resource_type",
                "resource_id",
                "severity",
                "outcome",
                "ip_address",
                "user_agent",
                "request_id",
            ]
        )
        for e in items:
            writer.writerow(
                [
                    str(e.id),
                    e.created_at.isoformat() if e.created_at else "",
                    str(e.tenant_id) if e.tenant_id else "",
                    str(e.actor_id) if e.actor_id else "",
                    e.actor_email or "",
                    e.action,
                    e.resource_type,
                    e.resource_id or "",
                    e.severity,
                    e.outcome,
                    e.ip_address or "",
                    e.user_agent or "",
                    e.request_id or "",
                ]
            )
        return output.getvalue()

    @staticmethod
    async def get_stats(
        db: AsyncSession,
        tenant_id: Optional[UUID] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        def _maybe_filter(q):
            if tenant_id:
                return q.where(AuditEvent.tenant_id == tenant_id)
            return q

        total_result = await db.execute(
            _maybe_filter(select(func.count()).select_from(AuditEvent)).where(
                AuditEvent.created_at >= cutoff
            )
        )
        total = total_result.scalar() or 0

        action_rows = await db.execute(
            _maybe_filter(select(AuditEvent.action, func.count()))
            .where(AuditEvent.created_at >= cutoff)
            .group_by(AuditEvent.action)
        )
        by_action: Dict[str, int] = dict(
            action_rows.all()  # type: ignore[arg-type]
        )

        severity_rows = await db.execute(
            _maybe_filter(select(AuditEvent.severity, func.count()))
            .where(AuditEvent.created_at >= cutoff)
            .group_by(AuditEvent.severity)
        )
        by_severity: Dict[str, int] = dict(
            severity_rows.all()  # type: ignore[arg-type]
        )

        type_rows = await db.execute(
            _maybe_filter(select(AuditEvent.resource_type, func.count()))
            .where(AuditEvent.created_at >= cutoff)
            .group_by(AuditEvent.resource_type)
        )
        by_type: Dict[str, int] = dict(
            type_rows.all()  # type: ignore[arg-type]
        )

        date_rows = await db.execute(
            _maybe_filter(
                select(
                    func.date(AuditEvent.created_at).label("day"),
                    func.count(),
                )
            )
            .where(AuditEvent.created_at >= cutoff)
            .group_by(func.date(AuditEvent.created_at))
            .order_by(func.date(AuditEvent.created_at))
        )
        by_date = {
            str(row[0]) if row[0] else "unknown": row[1]
            for row in date_rows.all()
        }

        return {
            "total_events": total,
            "date_range_days": days,
            "by_action": by_action,
            "by_severity": by_severity,
            "by_resource_type": by_type,
            "by_date": by_date,
        }


audit_service = AuditService()
