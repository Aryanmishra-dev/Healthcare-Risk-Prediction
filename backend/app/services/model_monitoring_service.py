import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ModelMonitoringService:
    def __init__(self):
        self.metrics = {
            "diabetes": {"prediction_count": 0, "errors": 0, "latency_sum_ms": 0},
            "heart_disease": {"prediction_count": 0, "errors": 0, "latency_sum_ms": 0},
            "lung_cancer": {"prediction_count": 0, "errors": 0, "latency_sum_ms": 0},
        }

    def record_prediction(self, disease: str, latency_ms: int, success: bool):
        if disease not in self.metrics:
            self.metrics[disease] = {"prediction_count": 0, "errors": 0, "latency_sum_ms": 0}
            
        self.metrics[disease]["prediction_count"] += 1
        self.metrics[disease]["latency_sum_ms"] += latency_ms
        if not success:
            self.metrics[disease]["errors"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        result = {}
        for disease, stats in self.metrics.items():
            count = stats["prediction_count"]
            avg_latency = stats["latency_sum_ms"] / count if count > 0 else 0
            error_rate = stats["errors"] / count if count > 0 else 0
            result[disease] = {
                "prediction_count": count,
                "average_inference_time_ms": round(avg_latency, 2),
                "error_rate": round(error_rate, 4),
            }
        return result

model_monitoring_service = ModelMonitoringService()
