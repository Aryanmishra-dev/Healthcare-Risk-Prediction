"""
ModelManager for handling MLflow-based model loading, caching, and health reporting.
Implements the Singleton pattern and ensures robust lazy-loading with retries.
"""

import asyncio
import logging
import os
import resource
import time
from pathlib import Path

import joblib
import mlflow

# Standard Python logging
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
MLRUNS_DIR = REPO_ROOT / "mlruns"
MODEL_DIR = REPO_ROOT / "ml" / "models"
MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", f"file://{MLRUNS_DIR}")
MODEL_SOURCE = os.environ.get("MODEL_SOURCE", "local").lower()
_IS_PRODUCTION = os.environ.get("APP_ENV") == "production"

# Configure MLflow
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


class ModelManager:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.models = {
            "diabetes": {
                "status": "unloaded",
                "version": None,
                "stage": None,
                "latency_ms": 0.0,
                "deps": {},
            },
            "heart_disease": {
                "status": "unloaded",
                "version": None,
                "stage": None,
                "latency_ms": 0.0,
                "deps": {},
            },
            "lung_cancer": {
                "status": "unloaded",
                "version": None,
                "stage": None,
                "latency_ms": 0.0,
                "deps": {},
            },
        }
        self.startup_diagnostics = {}
        self._initialized = True

    async def load_all_models(self):
        """Warm up all models in the background."""
        logger.info("Starting background model warmup...")
        start_time = time.time()

        # We use asyncio.gather for parallel loading
        await asyncio.gather(
            self._load_diabetes(),
            self._load_heart_disease(),
            self._load_lung_cancer(),
            return_exceptions=True,
        )

        max_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        memory_mb = max_rss / 1024
        if os.uname().sysname == "Darwin":
            memory_mb = max_rss / 1024 / 1024

        self.startup_diagnostics = {
            "startup_time_seconds": round(time.time() - start_time, 2),
            "memory_usage_mb": round(memory_mb, 2),
            "models_loaded": {
                k: v["status"] == "ready" for k, v in self.models.items()
            },
        }
        logger.info(f"Model warmup complete. Diagnostics: {self.startup_diagnostics}")

    async def _load_model_with_retry(self, model_name, load_func, max_retries=3):
        """Retry logic for loading models from MLflow."""
        for attempt in range(1, max_retries + 1):
            try:
                # Running blocking load operations in thread
                return await asyncio.to_thread(load_func)
            except Exception as e:
                logger.error(
                    f"Failed to load {model_name} (Attempt {attempt}/{max_retries}): {e}"
                )
                if attempt == max_retries:
                    if _IS_PRODUCTION:
                        raise RuntimeError(
                            f"Failed to load {model_name} in production after {max_retries} attempts."
                        ) from e
                    else:
                        logger.warning(
                            f"Could not load {model_name}. Proceeding in degraded mode."
                        )
                        return None
                await asyncio.sleep(2**attempt)

    def _fetch_diabetes_from_mlflow(self):
        model_uri = "models:/diabetes_xgboost/latest"
        calibrator_uri = "models:/diabetes_calibrator/latest"

        m = mlflow.sklearn.load_model(model_uri)
        c = mlflow.sklearn.load_model(calibrator_uri)

        return {"model": m, "calibrator": c, "version": "latest", "stage": "Production"}

    def _fetch_diabetes_from_disk(self):
        return {
            "model": joblib.load(MODEL_DIR / "diabetes_xgboost.pkl"),
            "calibrator": joblib.load(MODEL_DIR / "isotonic_calibrator.pkl"),
            "version": "local",
            "stage": "Local",
        }

    def _fetch_diabetes(self):
        if MODEL_SOURCE != "mlflow":
            return self._fetch_diabetes_from_disk()
        try:
            return self._fetch_diabetes_from_mlflow()
        except Exception as exc:
            logger.warning("diabetes_mlflow_load_failed_falling_back_to_disk: %s", exc)
            return self._fetch_diabetes_from_disk()

    async def _load_diabetes(self):
        start_t = time.time()
        result = await self._load_model_with_retry("diabetes", self._fetch_diabetes)
        latency = round((time.time() - start_t) * 1000, 2)

        if result:
            self.models["diabetes"].update(
                {
                    "status": "ready",
                    "version": result["version"],
                    "stage": result["stage"],
                    "latency_ms": latency,
                    "deps": result,
                }
            )
        else:
            self.models["diabetes"]["status"] = "failed"

    def _fetch_heart_disease_from_mlflow(self):
        model_uri = "models:/heart_disease_xgboost/latest"
        calibrator_uri = "models:/heart_disease_calibrator/latest"

        m = mlflow.sklearn.load_model(model_uri)
        c = mlflow.sklearn.load_model(calibrator_uri)

        # Features are artifacts, download them locally
        client = mlflow.tracking.MlflowClient()
        latest_versions = client.get_latest_versions("heart_disease_xgboost", stages=[])
        if not latest_versions:
            raise ValueError("No versions found for heart_disease_xgboost")
        run_id = latest_versions[0].run_id

        import joblib

        features_path = client.download_artifacts(run_id, "heart_features")
        f = joblib.load(features_path)

        return {
            "model": m,
            "calibrator": c,
            "features": f,
            "version": "latest",
            "stage": "Production",
        }

    def _fetch_heart_disease_from_disk(self):
        return {
            "model": joblib.load(MODEL_DIR / "heart_disease_xgboost.pkl"),
            "calibrator": joblib.load(MODEL_DIR / "heart_disease_calibrator.pkl"),
            "features": joblib.load(MODEL_DIR / "heart_disease_features.pkl"),
            "version": "local",
            "stage": "Local",
        }

    def _fetch_heart_disease(self):
        if MODEL_SOURCE != "mlflow":
            return self._fetch_heart_disease_from_disk()
        try:
            return self._fetch_heart_disease_from_mlflow()
        except Exception as exc:
            logger.warning("heart_mlflow_load_failed_falling_back_to_disk: %s", exc)
            return self._fetch_heart_disease_from_disk()

    async def _load_heart_disease(self):
        start_t = time.time()
        result = await self._load_model_with_retry(
            "heart_disease", self._fetch_heart_disease
        )
        latency = round((time.time() - start_t) * 1000, 2)

        if result:
            self.models["heart_disease"].update(
                {
                    "status": "ready",
                    "version": result["version"],
                    "stage": result["stage"],
                    "latency_ms": latency,
                    "deps": result,
                }
            )
        else:
            self.models["heart_disease"]["status"] = "failed"

    def _fetch_lung_cancer_from_mlflow(self):
        model_uri = "models:/lung_cancer_model/latest"
        scaler_uri = "models:/lung_cancer_scaler/latest"
        calibrator_uri = "models:/lung_cancer_calibrator/latest"

        m = mlflow.sklearn.load_model(model_uri)
        try:
            s = mlflow.sklearn.load_model(scaler_uri)
        except Exception:
            s = None

        try:
            c = mlflow.sklearn.load_model(calibrator_uri)
        except Exception:
            c = None

        # Features
        client = mlflow.tracking.MlflowClient()
        latest_versions = client.get_latest_versions("lung_cancer_model", stages=[])
        if latest_versions:
            run_id = latest_versions[0].run_id
            import joblib

            try:
                features_path = client.download_artifacts(run_id, "lung_features")
                f = joblib.load(features_path)
            except Exception:
                f = None
        else:
            f = None

        return {
            "model": m,
            "scaler": s,
            "calibrator": c,
            "features": f,
            "version": "latest",
            "stage": "Production",
        }

    def _fetch_lung_cancer_from_disk(self):
        calibrator_path = MODEL_DIR / "lung_cancer_calibrator.pkl"
        return {
            "model": joblib.load(MODEL_DIR / "lung_cancer_model.pkl"),
            "scaler": joblib.load(MODEL_DIR / "lung_cancer_scaler.pkl"),
            "calibrator": (
                joblib.load(calibrator_path) if calibrator_path.exists() else None
            ),
            "features": joblib.load(MODEL_DIR / "lung_cancer_features.pkl"),
            "version": "local",
            "stage": "Local",
        }

    def _fetch_lung_cancer(self):
        if MODEL_SOURCE != "mlflow":
            return self._fetch_lung_cancer_from_disk()
        try:
            return self._fetch_lung_cancer_from_mlflow()
        except Exception as exc:
            logger.warning("lung_mlflow_load_failed_falling_back_to_disk: %s", exc)
            return self._fetch_lung_cancer_from_disk()

    async def _load_lung_cancer(self):
        start_t = time.time()
        result = await self._load_model_with_retry(
            "lung_cancer", self._fetch_lung_cancer
        )
        latency = round((time.time() - start_t) * 1000, 2)

        if result:
            self.models["lung_cancer"].update(
                {
                    "status": "ready",
                    "version": result["version"],
                    "stage": result["stage"],
                    "latency_ms": latency,
                    "deps": result,
                }
            )
        else:
            self.models["lung_cancer"]["status"] = "failed"

    def get_diabetes_deps(self):
        if self.models["diabetes"]["status"] != "ready":
            raise Exception("Diabetes model temporarily offline.")
        d = self.models["diabetes"]["deps"]
        return d["model"], d["calibrator"]

    def get_heart_deps(self):
        if self.models["heart_disease"]["status"] != "ready":
            raise Exception("Heart disease model temporarily offline.")
        d = self.models["heart_disease"]["deps"]
        return d["model"], d["calibrator"], d.get("features")

    def get_lung_deps(self):
        if self.models["lung_cancer"]["status"] != "ready":
            raise Exception("Lung cancer model temporarily offline.")
        d = self.models["lung_cancer"]["deps"]
        return d["model"], d.get("scaler"), d.get("features"), d.get("calibrator")

    def get_health_status(self):
        return {
            "models": {
                k: {
                    "status": v["status"],
                    "version": v["version"],
                    "stage": v["stage"],
                    "latency_ms": v["latency_ms"],
                }
                for k, v in self.models.items()
            },
            "diagnostics": self.startup_diagnostics,
        }

    def export_app_state(self):
        """Return the legacy app.state model mapping used by older tests/routes."""
        state = {}
        if self.models["diabetes"]["status"] == "ready":
            d = self.models["diabetes"]["deps"]
            state["diabetes_model"] = d["model"]
            state["diabetes_calibrator"] = d["calibrator"]
        if self.models["heart_disease"]["status"] == "ready":
            d = self.models["heart_disease"]["deps"]
            state["heart_model"] = d["model"]
            state["heart_calibrator"] = d["calibrator"]
            state["heart_features"] = d.get("features")
        if self.models["lung_cancer"]["status"] == "ready":
            d = self.models["lung_cancer"]["deps"]
            state["lung_model"] = d["model"]
            state["lung_scaler"] = d.get("scaler")
            state["lung_features"] = d.get("features")
            state["lung_calibrator"] = d.get("calibrator")
        return state


model_manager = ModelManager()
