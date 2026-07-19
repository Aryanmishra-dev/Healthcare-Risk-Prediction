from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.router import get_current_user
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.prediction import (
    PredictionHistoryPaginated,
    PredictionHistoryParams,
    PredictionHistoryResponse,
)
from backend.app.services import prediction_history_service

router = APIRouter(prefix="/predictions", tags=["Prediction History"])


@router.get("/history", response_model=PredictionHistoryPaginated)
async def get_history(
    params: PredictionHistoryParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated prediction history with filters."""
    return await prediction_history_service.get_history(
        db, current_user.id, params
    )


@router.get("/{prediction_id}", response_model=PredictionHistoryResponse)
async def get_prediction(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single prediction by ID."""
    return await prediction_history_service.get_prediction_by_id(
        db, prediction_id, current_user.id
    )


@router.delete("/{prediction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prediction(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete (archive) a prediction."""
    await prediction_history_service.delete_prediction(
        db, prediction_id, current_user.id
    )
    return None


@router.post(
    "/{prediction_id}/favorite", response_model=PredictionHistoryResponse
)
async def favorite_prediction(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a prediction as favorite."""
    return await prediction_history_service.toggle_favorite(
        db, prediction_id, current_user.id, True
    )


@router.delete(
    "/{prediction_id}/favorite", response_model=PredictionHistoryResponse
)
async def unfavorite_prediction(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove favorite status from a prediction."""
    return await prediction_history_service.toggle_favorite(
        db, prediction_id, current_user.id, False
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Phase 3.4 — SHAP Explainability
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/{prediction_id}/explanation")
async def get_prediction_explanation(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get the SHAP explanation for a specific prediction.

    Returns:
    - feature names and their SHAP values
    - base model value (expected output)
    - ranked feature importances with human-readable descriptions
    - waterfall/force plot metadata
    """
    prediction = await prediction_history_service.get_prediction_by_id(
        db, prediction_id, current_user.id
    )

    shap_values = prediction.shap_values
    if not shap_values or not shap_values.get("features"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "SHAP explanation not available for this prediction. "
                "It may have been made before Phase 3 was deployed."
            ),
        )

    features: List[str] = shap_values.get("features", [])
    values: List[float] = shap_values.get("shap_values", [])
    base_value: float = shap_values.get("base_value", 0.0)

    # Build ranked feature importance list
    ranked = sorted(
        [
            {
                "feature": f,
                "shap_value": v,
                "impact": "increases_risk" if v > 0 else "decreases_risk",
                "magnitude": abs(v),
            }
            for f, v in zip(features, values)
        ],
        key=lambda x: x["magnitude"],
        reverse=True,
    )

    # Human-readable summary of top factors
    top_factors: list[str] = [str(r["feature"]) for r in ranked[:3]]
    summary = (
        f"The top factors influencing this "
        f"{prediction.disease_model} risk prediction were: "
        + ", ".join(top_factors)
        + f". The model baseline risk is {base_value:.2%}."
    )

    # Waterfall plot data (cumulative SHAP values)
    waterfall = []
    running = base_value
    for r in ranked:
        waterfall.append(
            {
                "feature": r["feature"],
                "value": r["shap_value"],
                "cumulative": float(running) + float(r["shap_value"]),
            }
        )
        running = float(running) + float(r["shap_value"])

    return {
        "prediction_id": prediction_id,
        "disease_model": prediction.disease_model,
        "risk_percentage": prediction.risk_percentage,
        "risk_level": prediction.risk_level,
        "model_version": prediction.model_version,
        "explanation": {
            "features": features,
            "shap_values": values,
            "base_value": base_value,
            "ranked_importances": ranked,
            "waterfall_data": waterfall,
            "human_readable_summary": summary,
        },
    }
