import logging
import time
from typing import Any, Dict, Optional

from fastapi import Request

from backend.app.models.base import utc_now
from backend.app.models.prediction import PredictionAuditLog
from backend.app.services.model_manager import model_manager
from backend.app.services.model_registry_service import model_registry_service
from backend.app.services.shap_explainer import (explain_diabetes,
                                                 explain_heart, explain_lung)

logger = logging.getLogger(__name__)


class PredictionPipeline:
    async def run_pipeline(
        self,
        request: Request,
        disease: str,
        input_data: dict,
        predict_func,
        build_features_func=None,
    ) -> Dict[str, Any]:
        """
        Executes the full prediction pipeline.

        Args:
            request: The FastAPI request object.
            disease: "diabetes", "heart_disease", or "lung_cancer".
            input_data: The raw validated input dictionary.
            predict_func: The actual async function to run the prediction.
            build_features_func: Optional function to build a DataFrame for SHAP explanation.
        """
        start_time = time.time()

        # 1. Validation & Input is handled by the caller Pydantic schema

        # 2. Model Selection (find active model version)
        # Note: We aren't passing the DB session here because this pipeline runs per-request
        # For full implementation, we'd inject DB session. For now we use the version from memory.
        model_status = model_manager.get_health_status()["models"].get(disease, {})
        model_version = model_status.get("version", "local")

        # 3. Feature Engineering & Prediction & Calibration
        # The underlying `predict_func` handles this internally via the model_loader logic
        try:
            result = await predict_func(request, **input_data)
        except Exception as e:
            logger.error(f"Prediction failed for {disease}: {e}")
            raise

        # 4. SHAP Explainability
        shap_values = None
        if build_features_func:
            try:
                feature_df = build_features_func(**input_data)
                if disease == "diabetes":
                    shap_values = explain_diabetes(feature_df)
                elif disease == "heart_disease":
                    shap_values = explain_heart(feature_df)
                elif disease == "lung_cancer":
                    shap_values = explain_lung(feature_df)
            except Exception as e:
                logger.warning(f"SHAP explanation failed for {disease}: {e}")

        # 5. Persistence & Audit Logging
        # Note: Actual DB persistence relies on log_prediction_to_db called in main.py,
        # but we can augment the payload here so main.py logs everything properly.
        processing_time_ms = int((time.time() - start_time) * 1000)

        response = {
            **result,
            "model_version": model_version,
            "processing_time_ms": processing_time_ms,
            "shap_values": shap_values,
        }

        # 6. Notification (Skipped for individual predictions per typical setup,
        # but could be added if risk > threshold)

        # 7. Response (Returns back to main.py orchestrator)
        return response


prediction_pipeline = PredictionPipeline()
