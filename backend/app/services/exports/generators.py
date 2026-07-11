import json
import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.models.user import User, UserProfile, UserSettings, UserSession, LoginHistory, SecurityEvent
from backend.app.models.prediction import PredictionAuditLog
from backend.app.models.report import UserReport
from backend.app.models.notification import Notification

async def generate_user_data_json(db: AsyncSession, user_id: uuid.UUID) -> bytes:
    """Extracts all user data from the database and returns a JSON byte string."""
    
    # User Profile & Settings
    result = await db.execute(
        select(User)
        .options(selectinload(User.profile), selectinload(User.settings))
        .where(User.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise ValueError("User not found")
        
    export_data: Dict[str, Any] = {
        "account": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "profile": {},
        "settings": {},
        "predictions": [],
        "reports": [],
        "notifications": [],
        "security": {
            "sessions": [],
            "login_history": [],
            "events": []
        }
    }
    
    if user.profile:
        export_data["profile"] = {
            "avatar_url": user.profile.avatar_url,
            "timezone": user.profile.timezone,
            "language": user.profile.language,
        }
        
    if user.settings:
        export_data["settings"] = {
            "theme": user.settings.theme,
            "language": user.settings.language,
            "email_notifications": user.settings.email_notifications,
            "push_notifications": user.settings.push_notifications,
        }
        
    # Predictions
    pred_result = await db.execute(select(PredictionAuditLog).where(PredictionAuditLog.user_id == user_id))
    for p in pred_result.scalars().all():
        export_data["predictions"].append({
            "id": str(p.id),
            "disease_type": p.disease_type,
            "prediction_label": p.prediction_label,
            "probability": p.probability,
            "confidence_score": p.confidence_score,
            "model_version": p.model_version,
            "shap_values": p.shap_values,
            "input_payload": p.input_payload,
            "processing_time_ms": p.processing_time_ms,
            "prediction_status": p.prediction_status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })
        
    # Reports
    rep_result = await db.execute(select(UserReport).where(UserReport.user_id == user_id, UserReport.deleted_at.is_(None)))
    for r in rep_result.scalars().all():
        export_data["reports"].append({
            "id": str(r.id),
            "filename": r.filename,
            "status": r.status,
            "content_type": r.content_type,
            "file_size": r.file_size,
            "parsed_text": r.parsed_text,
            "structured_data": r.structured_data,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
        
    # Notifications
    notif_result = await db.execute(select(Notification).where(Notification.user_id == user_id))
    for n in notif_result.scalars().all():
        export_data["notifications"].append({
            "id": str(n.id),
            "type": n.notification_type,
            "category": n.category,
            "priority": n.priority,
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        })
        
    # Security: Sessions
    sess_result = await db.execute(select(UserSession).where(UserSession.user_id == user_id))
    for s in sess_result.scalars().all():
        export_data["security"]["sessions"].append({
            "id": str(s.id),
            "ip_address": s.ip_address,
            "device_name": s.device_name,
            "browser": s.browser,
            "operating_system": s.operating_system,
            "login_method": s.login_method,
            "is_revoked": s.is_revoked,
            "last_activity": s.last_activity.isoformat() if s.last_activity else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })
        
    # Security: Login History
    lh_result = await db.execute(select(LoginHistory).where(LoginHistory.user_id == user_id))
    for lh in lh_result.scalars().all():
        export_data["security"]["login_history"].append({
            "id": str(lh.id),
            "ip_address": lh.ip_address,
            "device_name": lh.device_name,
            "browser": lh.browser,
            "operating_system": lh.operating_system,
            "login_method": lh.login_method,
            "status": lh.status,
            "login_time": lh.login_time.isoformat() if lh.login_time else None,
        })
        
    # Security: Events
    se_result = await db.execute(select(SecurityEvent).where(SecurityEvent.user_id == user_id))
    for se in se_result.scalars().all():
        export_data["security"]["events"].append({
            "id": str(se.id),
            "event_type": se.event_type,
            "severity": se.severity,
            "description": se.description,
            "metadata": se.metadata_payload,
            "created_at": se.created_at.isoformat() if se.created_at else None,
        })

    # Return as JSON bytes
    return json.dumps(export_data, indent=2).encode('utf-8')
