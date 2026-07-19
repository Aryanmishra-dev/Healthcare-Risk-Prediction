import uuid
from typing import Any, Dict, Optional

from fastapi import Request
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal


async def _resolve_tenant_id(
    db, user_id: uuid.UUID | None
) -> uuid.UUID | None:
    if user_id is None:
        return None
    from backend.app.models.tenant import Membership

    result = await db.execute(
        select(Membership.tenant_id)
        .where(Membership.user_id == user_id)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def log_prediction_to_db(
    request: Request,
    disease_model: str,
    input_data: dict[str, Any],
    risk_percentage: float,
    risk_level: str,
    source: str,
    user_id: str | None = None,
    shap_values: Optional[Dict] = None,
    processing_time_ms: int = 0,
) -> None:
    request_id = (
        getattr(request.state, "request_id", None)
        or request.headers.get("x-request-id")
        or str(uuid.uuid4())
    )

    # Parse user_id from JWT state if available on the request
    parsed_user_id = None
    if user_id:
        try:
            parsed_user_id = uuid.UUID(user_id)
        except ValueError:
            parsed_user_id = None
    else:
        # Try to extract from request state (set by auth middleware)
        raw_uid = getattr(request.state, "user_id", None)
        if raw_uid:
            try:
                parsed_user_id = uuid.UUID(str(raw_uid))
            except (ValueError, AttributeError):
                pass

    from backend.app.services.prediction_history_service import save_prediction

    async with AsyncSessionLocal() as db:
        tenant_id = await _resolve_tenant_id(db, parsed_user_id)
        await save_prediction(
            db=db,
            user_id=parsed_user_id,
            tenant_id=tenant_id,
            disease_model=disease_model,
            source=source,
            risk_percentage=float(risk_percentage),
            risk_level=risk_level,
            input_json=input_data,
            request_id=request_id,
            shap_values=shap_values,
            processing_time_ms=processing_time_ms,
        )
