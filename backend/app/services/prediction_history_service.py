import asyncio
import math
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.prediction import PredictionAuditLog
from backend.app.schemas.prediction import (
    PredictionHistoryPaginated,
    PredictionHistoryParams,
)
from backend.app.services.notifications.notification_service import (
    notification_dispatcher,
)


async def save_prediction(
    db: AsyncSession,
    user_id: Optional[UUID],
    disease_model: str,
    source: str,
    risk_percentage: float,
    risk_level: str,
    input_json: Optional[dict] = None,
    report_id: Optional[UUID] = None,
    confidence_score: float = 0.0,
    model_version: str = "local",
    shap_values: Optional[dict] = None,
    processing_time_ms: int = 0,
    prediction_status: str = "success",
    request_id: Optional[str] = None,
    tenant_id: Optional[UUID] = None,
) -> PredictionAuditLog:
    """Save a prediction to the database."""
    log_entry = PredictionAuditLog(
        user_id=user_id,
        tenant_id=tenant_id,
        disease_model=disease_model,
        source=source,
        risk_percentage=risk_percentage,
        risk_level=risk_level,
        input_json=input_json,
        report_id=report_id,
        confidence_score=confidence_score,
        model_version=model_version,
        shap_values=shap_values,
        processing_time_ms=processing_time_ms,
        prediction_status=prediction_status,
        request_id=request_id,
    )
    db.add(log_entry)
    try:
        await db.commit()
        await db.refresh(log_entry)

        if user_id:
            status_text = (
                "successfully" if prediction_status == "success" else "failed"
            )
            asyncio.create_task(
                notification_dispatcher.dispatch(
                    user_id=user_id,
                    notification_type=f"prediction_{prediction_status}",
                    category="Prediction",
                    priority="NORMAL",
                    title=f"Prediction {prediction_status.capitalize()}",
                    message=(
                        f"Your {disease_model} prediction has "
                        f"{status_text} completed."
                    ),
                )
            )

        return log_entry
    except Exception as e:
        await db.rollback()
        raise e


async def get_history(
    db: AsyncSession,
    user_id: UUID,
    params: PredictionHistoryParams,
) -> PredictionHistoryPaginated:
    """Get paginated prediction history with filters."""
    query = select(PredictionAuditLog).where(
        PredictionAuditLog.user_id == user_id
    )

    if params.disease:
        query = query.where(PredictionAuditLog.disease_model == params.disease)
    if params.risk_level:
        query = query.where(PredictionAuditLog.risk_level == params.risk_level)
    if params.favorite is not None:
        query = query.where(PredictionAuditLog.favorite == params.favorite)
    if params.report_id:
        query = query.where(PredictionAuditLog.report_id == params.report_id)
    if params.start_date:
        query = query.where(PredictionAuditLog.created_at >= params.start_date)
    if params.end_date:
        query = query.where(PredictionAuditLog.created_at <= params.end_date)
    if params.search:
        search_term = f"%{params.search}%"
        # Search in disease model, risk level, or notes
        query = query.where(
            or_(
                PredictionAuditLog.disease_model.ilike(search_term),
                PredictionAuditLog.risk_level.ilike(search_term),
                PredictionAuditLog.notes.ilike(search_term),
            )
        )

    # Do not show archived unless specifically requested (or never)
    # We will exclude archived by default for history
    query = query.where(PredictionAuditLog.archived.is_(False))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Pagination
    offset = (params.page - 1) * params.size
    query = (
        query.order_by(desc(PredictionAuditLog.created_at))
        .offset(offset)
        .limit(params.size)
    )

    result = await db.execute(query)
    items = result.scalars().all()

    pages = math.ceil(total / params.size) if total > 0 else 0

    return PredictionHistoryPaginated(
        items=items,  # type: ignore[arg-type]
        total=total,
        page=params.page,
        size=params.size,
        pages=pages,
    )


async def get_prediction_by_id(
    db: AsyncSession,
    prediction_id: int,
    user_id: UUID,
) -> PredictionAuditLog:
    """Get a single prediction and verify ownership."""
    query = select(PredictionAuditLog).where(
        PredictionAuditLog.id == prediction_id,
        PredictionAuditLog.user_id == user_id,
    )
    result = await db.execute(query)
    prediction = result.scalar_one_or_none()

    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found or you don't have access to it.",
        )
    return prediction


async def delete_prediction(
    db: AsyncSession,
    prediction_id: int,
    user_id: UUID,
) -> None:
    """Soft delete (archive) a prediction."""
    prediction = await get_prediction_by_id(db, prediction_id, user_id)
    prediction.archived = True
    await db.commit()


async def toggle_favorite(
    db: AsyncSession,
    prediction_id: int,
    user_id: UUID,
    is_favorite: bool,
) -> PredictionAuditLog:
    """Set the favorite status of a prediction."""
    prediction = await get_prediction_by_id(db, prediction_id, user_id)
    prediction.favorite = is_favorite
    await db.commit()
    await db.refresh(prediction)
    return prediction
