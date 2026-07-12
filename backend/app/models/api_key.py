import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.app.models.base import Base, utc_now


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: uuid.UUID = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    tenant_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: uuid.UUID = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    name: str = Column(String(100), nullable=False)
    key_prefix: str = Column(String(8), nullable=False, index=True)
    hashed_key: str = Column(String(255), nullable=False, unique=True)

    scopes: List[str] = Column(JSON, nullable=False, default=list)

    is_active: bool = Column(Boolean, default=True, nullable=False)

    expires_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    last_used_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)

    created_at: datetime = Column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: datetime = Column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    tenant = relationship("Tenant", backref="api_keys")
    creator = relationship("User", foreign_keys=[created_by])
