"""
Database configuration for prediction audit logging.
Uses a lightweight SQLite database to meet healthcare compliance
without requiring external infrastructure changes.
"""

import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# ── Configuration ──────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(ROOT, "data")
os.makedirs(DB_DIR, exist_ok=True)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'audit_log.db')}"

# ── Database Setup ─────────────────────────────────────────────────────────
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── Models ─────────────────────────────────────────────────────────────────
class PredictionAuditLog(Base):
    __tablename__ = "prediction_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    request_id = Column(String, index=True)
    client_ip = Column(String, index=True)
    disease_model = Column(String, index=True)
    
    # Store the input parameters as a JSON string to keep the schema simple
    input_features = Column(String)
    
    # The result
    risk_percentage = Column(Float)
    risk_level = Column(String)
    
    # How was this requested? (e.g. "ui" vs "api")
    source = Column(String, index=True)


# Create tables on import
Base.metadata.create_all(bind=engine)


# ── Dependency ─────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
