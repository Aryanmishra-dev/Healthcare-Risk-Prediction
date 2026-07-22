import gc
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = os.path.join(REPO_ROOT, "ml", "models")

_explainers = {}
_explainers_loaded = False


def load_explainers():
    global _explainers_loaded
    if _explainers_loaded:
        return
    import joblib
    import shap

    shap_path = os.path.join(MODEL_DIR, "shap_explainer.pkl")
    try:
        _explainers["diabetes"] = joblib.load(shap_path)
        logger.info("Diabetes SHAP explainer loaded from disk.")
    except Exception:
        try:
            model = joblib.load(
                os.path.join(MODEL_DIR, "diabetes_xgboost.pkl")
            )
            _explainers["diabetes"] = shap.TreeExplainer(model)
            del model
            logger.info("Diabetes SHAP explainer created from model.")
        except Exception as e:
            logger.warning("Could not create diabetes SHAP explainer: %s", e)

    try:
        model = joblib.load(
            os.path.join(MODEL_DIR, "heart_disease_xgboost.pkl")
        )
        _explainers["heart"] = shap.TreeExplainer(model)
        del model
        logger.info("Heart disease SHAP explainer created.")
    except Exception as e:
        logger.warning("Could not create heart disease SHAP explainer: %s", e)

    try:
        import numpy as np
        import pandas as pd

        model = joblib.load(os.path.join(MODEL_DIR, "lung_cancer_model.pkl"))
        scaler = joblib.load(os.path.join(MODEL_DIR, "lung_cancer_scaler.pkl"))
        features = joblib.load(
            os.path.join(MODEL_DIR, "lung_cancer_features.pkl")
        )

        rng = np.random.default_rng(42)
        n = 100
        bg_data = {
            "Age": scaler.transform(
                rng.integers(18, 101, size=(n, 1)).astype(float)
            ).ravel(),
            "Gender": rng.integers(0, 2, size=n).astype(float),
            "Smoking": rng.integers(0, 2, size=n).astype(float),
            "Yellow Fingers": rng.integers(0, 2, size=n).astype(float),
            "Chronic Disease": rng.integers(0, 2, size=n).astype(float),
            "Fatigue": rng.integers(0, 2, size=n).astype(float),
            "Wheezing": rng.integers(0, 2, size=n).astype(float),
            "Shortness of Breath": rng.integers(0, 2, size=n).astype(float),
        }
        bg_df = pd.DataFrame(bg_data)[features].astype(np.float64)
        _explainers["lung"] = shap.LinearExplainer(model, bg_df)
        del model, scaler, features, bg_data, bg_df
        logger.info("Lung cancer SHAP explainer created.")
    except Exception as e:
        logger.warning("Could not create lung cancer SHAP explainer: %s", e)

    _explainers_loaded = True
    gc.collect()


def _get_explainer(name):
    if not _explainers_loaded:
        import time as _time

        logger.info("lazy_loading_shap_explainers")
        t0 = _time.time()
        load_explainers()
        elapsed = _time.time() - t0
        logger.info("shap_explainers_loaded_in_%.2fs", elapsed)
    return _explainers.get(name)


def _compute_shap(explainer, feature_df):
    import numpy as np

    sv = explainer.shap_values(feature_df)
    if isinstance(sv, list):
        sv = sv[1]
    values = sv[0].tolist()
    base = float(explainer.expected_value)
    if isinstance(explainer.expected_value, np.ndarray):
        base = float(explainer.expected_value[1])
    return {
        "features": list(feature_df.columns),
        "shap_values": [round(v, 4) for v in values],
        "base_value": round(base, 4),
    }


def explain_diabetes(feature_df):
    explainer = _get_explainer("diabetes")
    if explainer is None:
        return {"features": [], "shap_values": [], "base_value": 0.0}
    return _compute_shap(explainer, feature_df)


def explain_heart(feature_df):
    explainer = _get_explainer("heart")
    if explainer is None:
        return {"features": [], "shap_values": [], "base_value": 0.0}
    return _compute_shap(explainer, feature_df)


def explain_lung(feature_df):
    explainer = _get_explainer("lung")
    if explainer is None:
        return {"features": [], "shap_values": [], "base_value": 0.0}
    return _compute_shap(explainer, feature_df)
