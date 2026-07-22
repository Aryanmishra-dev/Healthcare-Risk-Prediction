import asyncio
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
MLRUNS_DIR = REPO_ROOT / "mlruns"
MODEL_DIR = REPO_ROOT / "ml" / "models"
MLFLOW_TRACKING_URI = os.environ.get(
    "MLFLOW_TRACKING_URI", f"file://{MLRUNS_DIR}"
)
MODEL_SOURCE = os.environ.get("MODEL_SOURCE", "local").lower()
_IS_PRODUCTION = os.environ.get("APP_ENV") == "production"

_MLFLOW_DOWNLOAD_TIMEOUT = int(
    os.environ.get("MLFLOW_DOWNLOAD_TIMEOUT", "120")
)


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
        self._loaded = False
        self._initialized = True

    async def load_all_models(self):
        if self._loaded:
            return
        logger.info("Starting background model warmup...")
        start_time = time.time()

        await asyncio.gather(
            self._load_diabetes(),
            self._load_heart_disease(),
            self._load_lung_cancer(),
            return_exceptions=True,
        )

        warmup_results = {}
        for name in ("diabetes", "heart_disease", "lung_cancer"):
            model_entry = self.models.get(name)
            if model_entry and model_entry["status"] == "ready":
                pipeline = model_entry.get("pipeline")
                if pipeline and hasattr(pipeline, "predict_proba"):
                    try:
                        import numpy as np

                        n_features = getattr(pipeline, "n_features_in_", 5)
                        dummy = np.zeros((1, n_features), dtype=np.float32)
                        warmup_start = time.perf_counter()
                        _ = pipeline.predict_proba(dummy)[0]
                        elapsed = round(
                            (time.perf_counter() - warmup_start) * 1000, 1
                        )
                        warmup_results[name] = f"{elapsed}ms"
                    except Exception as exc:
                        warmup_results[name] = f"warmup_failed: {exc}"

        import resource

        max_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if os.uname().sysname == "Darwin":
            memory_mb = max_rss / 1024 / 1024
        else:
            memory_mb = max_rss / 1024

        self.startup_diagnostics = {
            "startup_time_seconds": round(time.time() - start_time, 2),
            "memory_usage_mb": round(memory_mb, 2),
            "models_loaded": {
                k: v["status"] == "ready" for k, v in self.models.items()
            },
            "warmup_latency_ms": warmup_results,
        }
        self._loaded = True
        logger.info(
            "Model warmup complete. Diagnostics: %s", self.startup_diagnostics
        )

    async def _load_model_with_retry(
        self, model_name, load_func, max_retries=3
    ):
        for attempt in range(1, max_retries + 1):
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(load_func),
                    timeout=_MLFLOW_DOWNLOAD_TIMEOUT,
                )
            except Exception as e:
                logger.error(
                    "Failed to load %s (Attempt %d/%d): %s",
                    model_name,
                    attempt,
                    max_retries,
                    e,
                )
                if attempt == max_retries:
                    if _IS_PRODUCTION:
                        raise RuntimeError(
                            f"Failed to load {model_name} in production "
                            f"after {max_retries} attempts."
                        ) from e
                    else:
                        logger.warning(
                            "Could not load %s. Proceeding in degraded mode.",
                            model_name,
                        )
                        return None
                await asyncio.sleep(2**attempt)

    def _fetch_diabetes_from_mlflow(self):
        import mlflow

        m = mlflow.sklearn.load_model("models:/diabetes_xgboost/latest")
        c = mlflow.sklearn.load_model("models:/diabetes_calibrator/latest")
        return {
            "model": m,
            "calibrator": c,
            "version": "latest",
            "stage": "Production",
        }

    def _fetch_diabetes_from_disk(self):
        import joblib

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
            logger.warning(
                "diabetes_mlflow_load_failed_falling_back_to_disk: %s", exc
            )
            return self._fetch_diabetes_from_disk()

    async def _load_diabetes(self):
        start_t = time.time()
        result = await self._load_model_with_retry(
            "diabetes", self._fetch_diabetes
        )
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
        import joblib
        import mlflow

        m = mlflow.sklearn.load_model("models:/heart_disease_xgboost/latest")
        c = mlflow.sklearn.load_model(
            "models:/heart_disease_calibrator/latest"
        )
        client = mlflow.tracking.MlflowClient()
        latest_versions = client.get_latest_versions(
            "heart_disease_xgboost", stages=[]
        )
        if not latest_versions:
            raise ValueError("No versions found for heart_disease_xgboost")
        run_id = latest_versions[0].run_id
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
        import joblib

        return {
            "model": joblib.load(MODEL_DIR / "heart_disease_xgboost.pkl"),
            "calibrator": joblib.load(
                MODEL_DIR / "heart_disease_calibrator.pkl"
            ),
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
            logger.warning(
                "heart_mlflow_load_failed_falling_back_to_disk: %s", exc
            )
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
        import joblib
        import mlflow

        m = mlflow.sklearn.load_model("models:/lung_cancer_model/latest")
        try:
            s = mlflow.sklearn.load_model("models:/lung_cancer_scaler/latest")
        except Exception:
            s = None
        try:
            c = mlflow.sklearn.load_model(
                "models:/lung_cancer_calibrator/latest"
            )
        except Exception:
            c = None
        client = mlflow.tracking.MlflowClient()
        latest_versions = client.get_latest_versions(
            "lung_cancer_model", stages=[]
        )
        f = None
        if latest_versions:
            run_id = latest_versions[0].run_id
            try:
                features_path = client.download_artifacts(
                    run_id, "lung_features"
                )
                f = joblib.load(features_path)
            except Exception:
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
        import joblib

        calibrator_path = MODEL_DIR / "lung_cancer_calibrator.pkl"
        return {
            "model": joblib.load(MODEL_DIR / "lung_cancer_model.pkl"),
            "scaler": joblib.load(MODEL_DIR / "lung_cancer_scaler.pkl"),
            "calibrator": (
                joblib.load(calibrator_path)
                if calibrator_path.exists()
                else None
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
            logger.warning(
                "lung_mlflow_load_failed_falling_back_to_disk: %s", exc
            )
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

    def _ensure_loaded(self, name):
        if self.models[name]["status"] != "ready":
            import time as _time

            start_t = _time.time()
            fetch_func = getattr(self, f"_fetch_{name}")
            result = fetch_func()
            latency = round((_time.time() - start_t) * 1000, 2)
            if result:
                self.models[name].update(
                    {
                        "status": "ready",
                        "version": result["version"],
                        "stage": result["stage"],
                        "latency_ms": latency,
                        "deps": result,
                    }
                )
        if self.models[name]["status"] != "ready":
            raise Exception(f"{name} model temporarily offline.")

    def get_diabetes_deps(self):
        self._ensure_loaded("diabetes")
        d = self.models["diabetes"]["deps"]
        return d["model"], d["calibrator"]

    def get_heart_deps(self):
        self._ensure_loaded("heart_disease")
        d = self.models["heart_disease"]["deps"]
        return d["model"], d["calibrator"], d.get("features")

    def get_lung_deps(self):
        self._ensure_loaded("lung_cancer")
        d = self.models["lung_cancer"]["deps"]
        return (
            d["model"],
            d.get("scaler"),
            d.get("features"),
            d.get("calibrator"),
        )

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
