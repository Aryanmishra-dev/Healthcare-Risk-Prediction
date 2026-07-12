import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from backend.app.models.base import Base, TimestampMixin


class ModelVersion(Base, TimestampMixin):
    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String(255), index=True)
    model_version: Mapped[str] = mapped_column(String(50))
    disease: Mapped[str] = mapped_column(String(100), index=True)
    framework: Mapped[str] = mapped_column(String(50))
    algorithm: Mapped[str] = mapped_column(String(100))

    training_dataset: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dataset_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    feature_schema_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    hyperparameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    training_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deployed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    model_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mlflow_model_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Status: Training, Staging, Production, Archived, Deprecated
    status: Mapped[str] = mapped_column(String(50), default="Training", index=True)
