"""Prediction audit log ORM model."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String

from backend.app.db.base import Base


class PredictionAuditLog(Base):
    __tablename__ = "prediction_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    request_id = Column(String, index=True)
    client_ip = Column(String, index=True)
    disease_model = Column(String, index=True)
    input_features = Column(String)
    risk_percentage = Column(Float)
    risk_level = Column(String)
    source = Column(String, index=True)
