import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ModelDriftService:
    def __init__(self):
        self.drift_history = []

    def record_drift(
        self,
        disease: str,
        feature_drift: bool,
        prediction_drift: bool,
        data_drift: bool,
    ):
        drift_record = {
            "disease": disease,
            "feature_drift": feature_drift,
            "prediction_drift": prediction_drift,
            "data_drift": data_drift,
        }
        self.drift_history.append(drift_record)

        if feature_drift or prediction_drift or data_drift:
            logger.warning(f"Drift detected for {disease}: {drift_record}")
            # Generate alerts here if necessary (e.g. using NotificationService)

    def get_recent_drift(self) -> list:
        return self.drift_history[-100:]


model_drift_service = ModelDriftService()
