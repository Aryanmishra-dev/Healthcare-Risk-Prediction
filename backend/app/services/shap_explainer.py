"""
SHAP explainability module — provides feature-importance explanations for all models.

Generates per-prediction SHAP values so users can understand *why* a model
produced a specific risk score.
"""

import os
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = os.path.join(REPO_ROOT, "ml", "models")

# ── Module-level SHAP explainers ──────────────────────────────────────────
_diabetes_explainer = None
_heart_explainer = None
_lung_explainer = None


def load_explainers():
    """Load or create SHAP explainers for all models."""
    global _diabetes_explainer, _heart_explainer, _lung_explainer

    # Diabetes — TreeExplainer (pre-saved or create from model)
    shap_path = os.path.join(MODEL_DIR, "shap_explainer.pkl")
    try:
        _diabetes_explainer = joblib.load(shap_path)
        logger.info("Diabetes SHAP explainer loaded from disk.")
    except Exception:
        try:
            model = joblib.load(os.path.join(MODEL_DIR, "diabetes_xgboost.pkl"))
            _diabetes_explainer = shap.TreeExplainer(model)
            logger.info("Diabetes SHAP explainer created from model.")
        except Exception as e:
            logger.warning("Could not create diabetes SHAP explainer: %s", e)

    # Heart disease — TreeExplainer
    try:
        model = joblib.load(os.path.join(MODEL_DIR, "heart_disease_xgboost.pkl"))
        _heart_explainer = shap.TreeExplainer(model)
        logger.info("Heart disease SHAP explainer created.")
    except Exception as e:
        logger.warning("Could not create heart disease SHAP explainer: %s", e)

    # Lung cancer — LinearExplainer (LogisticRegression)
    try:
        model = joblib.load(os.path.join(MODEL_DIR, "lung_cancer_model.pkl"))
        scaler = joblib.load(os.path.join(MODEL_DIR, "lung_cancer_scaler.pkl"))
        features = joblib.load(os.path.join(MODEL_DIR, "lung_cancer_features.pkl"))

        # Create a background dataset for the linear explainer
        rng = np.random.default_rng(42)
        n = 100
        bg_data = {
            "Age": scaler.transform(rng.integers(18, 101, size=(n, 1)).astype(float)).ravel(),
            "Gender": rng.integers(0, 2, size=n).astype(float),
            "Smoking": rng.integers(0, 2, size=n).astype(float),
            "Yellow Fingers": rng.integers(0, 2, size=n).astype(float),
            "Chronic Disease": rng.integers(0, 2, size=n).astype(float),
            "Fatigue": rng.integers(0, 2, size=n).astype(float),
            "Wheezing": rng.integers(0, 2, size=n).astype(float),
            "Shortness of Breath": rng.integers(0, 2, size=n).astype(float),
        }
        bg_df = pd.DataFrame(bg_data)[features].astype(np.float64)
        _lung_explainer = shap.LinearExplainer(model, bg_df)
        logger.info("Lung cancer SHAP explainer created.")
    except Exception as e:
        logger.warning("Could not create lung cancer SHAP explainer: %s", e)


def explain_diabetes(feature_df: pd.DataFrame) -> dict:
    """Return SHAP feature importances for a diabetes prediction."""
    if _diabetes_explainer is None:
        return {"features": [], "shap_values": [], "base_value": 0.0}

    sv = _diabetes_explainer.shap_values(feature_df)
    if isinstance(sv, list):
        sv = sv[1]  # positive class
    values = sv[0].tolist()
    base = float(_diabetes_explainer.expected_value)
    if isinstance(_diabetes_explainer.expected_value, np.ndarray):
        base = float(_diabetes_explainer.expected_value[1])

    return {
        "features": list(feature_df.columns),
        "shap_values": [round(v, 4) for v in values],
        "base_value": round(base, 4),
    }


def explain_heart(feature_df: pd.DataFrame) -> dict:
    """Return SHAP feature importances for a heart disease prediction."""
    if _heart_explainer is None:
        return {"features": [], "shap_values": [], "base_value": 0.0}

    sv = _heart_explainer.shap_values(feature_df)
    if isinstance(sv, list):
        sv = sv[1]
    values = sv[0].tolist()
    base = float(_heart_explainer.expected_value)
    if isinstance(_heart_explainer.expected_value, np.ndarray):
        base = float(_heart_explainer.expected_value[1])

    return {
        "features": list(feature_df.columns),
        "shap_values": [round(v, 4) for v in values],
        "base_value": round(base, 4),
    }


def explain_lung(feature_df: pd.DataFrame) -> dict:
    """Return SHAP feature importances for a lung cancer prediction."""
    if _lung_explainer is None:
        return {"features": [], "shap_values": [], "base_value": 0.0}

    sv = _lung_explainer.shap_values(feature_df)
    values = sv[0].tolist()
    base = float(_lung_explainer.expected_value)
    if isinstance(_lung_explainer.expected_value, np.ndarray):
        base = float(_lung_explainer.expected_value[1])

    return {
        "features": list(feature_df.columns),
        "shap_values": [round(v, 4) for v in values],
        "base_value": round(base, 4),
    }
