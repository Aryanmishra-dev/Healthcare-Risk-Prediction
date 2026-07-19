import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID

from backend.app.models.base import Base, utc_now


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: uuid.UUID = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    tenant_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    api_key_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    endpoint: str = Column(String(255), nullable=False)
    method: str = Column(String(10), nullable=False, default="GET")
    status_code: int = Column(Integer, nullable=True)
    recorded_at: datetime = Column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )


class TenantQuota(Base):
    __tablename__ = "tenant_quotas"

    id: uuid.UUID = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    tenant_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    rate_limit_per_minute: int = Column(Integer, nullable=False, default=100)
    monthly_quota: int = Column(BigInteger, nullable=False, default=10000)
    created_at: datetime = Column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
