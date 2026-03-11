"""
MLflow experiment tracking configuration.

Sets up MLflow tracking for model training runs. Logs parameters, metrics,
and artifacts for reproducibility and comparison.

Usage:
    from scripts.mlflow_config import init_tracking, log_training_run
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MLFLOW_DIR = os.path.join(ROOT, "mlruns")


def init_tracking(experiment_name: str = "healthcare_risk_prediction"):
    """Initialize MLflow tracking with a local file store."""
    import mlflow

    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", f"file://{MLFLOW_DIR}")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)
    return mlflow


def log_training_run(
    model_name: str,
    params: dict,
    metrics: dict,
    artifacts: list[str] | None = None,
    tags: dict | None = None,
):
    """
    Log a complete training run to MLflow.

    Args:
        model_name: Name of the model (e.g. "diabetes_xgboost")
        params: Hyperparameters dict
        metrics: Evaluation metrics dict
        artifacts: List of file paths to log as artifacts
        tags: Optional dict of tags
    """
    import mlflow

    with mlflow.start_run(run_name=model_name) as run:
        mlflow.set_tag("model_name", model_name)
        if tags:
            for k, v in tags.items():
                mlflow.set_tag(k, v)

        mlflow.log_params(params)
        mlflow.log_metrics(metrics)

        if artifacts:
            for path in artifacts:
                if os.path.exists(path):
                    mlflow.log_artifact(path)

        print(f"  MLflow run logged: {run.info.run_id}")
        return run.info.run_id
