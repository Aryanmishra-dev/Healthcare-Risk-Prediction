import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime, Uuid

from backend.app.models.base import Base, TimestampMixin, UUIDMixin, utc_now


class UserReport(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_reports"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # File Metadata
    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(
        String(100), default="application/pdf"
    )
    extension: Mapped[str] = mapped_column(String(20), nullable=True)
    file_size: Mapped[int] = mapped_column(default=0)

    # Storage
    storage_path: Mapped[str] = mapped_column(String(500))
    checksum: Mapped[str] = mapped_column(String(64), index=True)

    # Processing state
    upload_status: Mapped[str] = mapped_column(String(50), default="uploaded")
    processing_status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )
    parser_version: Mapped[str] = mapped_column(String(50), default="1.0")

    # Extracted data
    extracted_entities: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    prediction_count: Mapped[int] = mapped_column(default=0)

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("User", back_populates="reports")
    # Removed implicit back_populates to avoid requiring a backref on
    # PredictionAuditLog if it doesn't exist yet
