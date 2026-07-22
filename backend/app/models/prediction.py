import uuid

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from backend.app.models.base import Base, TimestampMixin


class PredictionAuditLog(Base, TimestampMixin):
    __tablename__ = "prediction_audit_logs"

    __table_args__ = (
        # Performance index for user history queries
        __import__("sqlalchemy").Index(
            "ix_prediction_audit_logs_user_id", "user_id"
        ),
        __import__("sqlalchemy").Index(
            "ix_prediction_audit_logs_tenant_id", "tenant_id"
        ),
        __import__("sqlalchemy").Index(
            "ix_prediction_audit_logs_created_at", "created_at"
        ),
    )

    # We use Integer as primary key to match the legacy SQLite schema that
    # used AUTOINCREMENT.
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # User ID is UUID but stored as string in legacy. We will use UUID type.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )

    disease_model: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(255))
    risk_percentage: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(50))
    input_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Phase 2.3: Prediction History & Persistence
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("user_reports.id", ondelete="SET NULL"), nullable=True
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    model_version: Mapped[str] = mapped_column(String(50), default="local")
    shap_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    prediction_status: Mapped[str] = mapped_column(
        String(50), default="success"
    )
    favorite: Mapped[bool] = mapped_column(default=False)
    archived: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Phase 3: MLOps and Model Lifecycle
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("model_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_calibrated: Mapped[bool] = mapped_column(default=False)
    ab_test_group: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    drift_detected: Mapped[bool] = mapped_column(default=False)
