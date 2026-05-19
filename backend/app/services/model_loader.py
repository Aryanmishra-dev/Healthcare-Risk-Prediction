"""
Model loading and prediction logic for the healthcare risk prediction API.

Supports multiple disease models (diabetes, heart disease, etc.).
Each disease has its own load/predict functions.
"""

import logging
import os
import asyncio
import tempfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)

# ── Paths & S3 Initialization ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[3]
LOCAL_MODEL_DIR = REPO_ROOT / "ml" / "models"

S3_MODEL_BUCKET = os.environ.get("S3_MODEL_BUCKET")
if S3_MODEL_BUCKET:
    import boto3
    MODEL_DIR = os.path.join(tempfile.gettempdir(), "healthcare_models")
    os.makedirs(MODEL_DIR, exist_ok=True)
    try:
        s3 = boto3.client('s3')
        logger.info(f"Downloading models from S3 bucket: {S3_MODEL_BUCKET}")
        expected_keys = [
            "diabetes_xgboost.pkl", "isotonic_calibrator.pkl", "shap_explainer.pkl",
            "heart_disease_xgboost.pkl", "heart_disease_calibrator.pkl", "heart_disease_features.pkl",
            "lung_cancer_model.pkl", "lung_cancer_scaler.pkl", "lung_cancer_features.pkl", "lung_cancer_calibrator.pkl",
            "model_registry.json"
        ]
        for key in expected_keys:
            target_path = os.path.join(MODEL_DIR, key)
            if not os.path.exists(target_path):
                logger.info(f"Downloading {key}...")
                s3.download_file(S3_MODEL_BUCKET, key, target_path)
    except Exception as e:
        logger.error(f"Failed to download models from S3: {e}")
        MODEL_DIR = str(LOCAL_MODEL_DIR)
else:
    MODEL_DIR = str(LOCAL_MODEL_DIR)

# ── Module-level model singletons ─────────────────────────────────────────
_diabetes_model = None
_diabetes_calibrator = None

_heart_model = None
_heart_calibrator = None
_heart_features = None

_lung_model = None
_lung_scaler = None
_lung_features = None
_lung_calibrator = None


# ══════════════════════════════════════════════════════════════════════════
#  Loaders
# ══════════════════════════════════════════════════════════════════════════

# WHY: If pre-loaded stub models already exist (e.g. from test fixtures),
# skip disk loading entirely. In production, missing weights raise RuntimeError.
_IS_PRODUCTION = os.environ.get("APP_ENV") == "production"


def load_models(app):
    """Load all disease models at startup.

    If app.state.models is already populated (e.g. by test stubs), skip loading.
    In production (APP_ENV=production), missing weights cause a hard crash.
    """
    if getattr(app.state, "models", None) and any(v is not None for v in app.state.models.values()):
        logger.info("Models already loaded (likely from test stubs), skipping disk load.")
        return
    app.state.models = {}
    _load_diabetes_models(app)
    _load_heart_disease_models(app)
    _load_lung_cancer_models(app)


def _load_diabetes_models(app):
    try:
        app.state.models["diabetes_model"] = joblib.load(os.path.join(MODEL_DIR, "diabetes_xgboost.pkl"))
        app.state.models["diabetes_calibrator"] = joblib.load(os.path.join(MODEL_DIR, "isotonic_calibrator.pkl"))
        logger.info("Diabetes models loaded successfully.")
    except FileNotFoundError as e:
        # WHY: In production, missing weights must crash — silent None causes KeyError at inference time
        if _IS_PRODUCTION:
            raise RuntimeError(f"Diabetes model weights missing — cannot start in production: {e}") from e
        logger.warning("Diabetes model files missing (dev/test mode): %s", e)
        app.state.models["diabetes_model"] = None
        app.state.models["diabetes_calibrator"] = None


def _load_heart_disease_models(app):
    try:
        app.state.models["heart_model"] = joblib.load(os.path.join(MODEL_DIR, "heart_disease_xgboost.pkl"))
        app.state.models["heart_calibrator"] = joblib.load(os.path.join(MODEL_DIR, "heart_disease_calibrator.pkl"))
        app.state.models["heart_features"] = joblib.load(os.path.join(MODEL_DIR, "heart_disease_features.pkl"))
        logger.info("Heart disease models loaded successfully.")
    except Exception as e:
        # WHY: In production, missing weights must crash — silent None causes KeyError at inference time
        if _IS_PRODUCTION:
            raise RuntimeError(f"Heart disease model weights missing — cannot start in production: {e}") from e
        logger.warning("Heart disease model files missing (dev/test mode): %s", e)
        app.state.models["heart_model"] = None
        app.state.models["heart_calibrator"] = None
        app.state.models["heart_features"] = None


def _load_lung_cancer_models(app):
    try:
        app.state.models["lung_model"] = joblib.load(os.path.join(MODEL_DIR, "lung_cancer_model.pkl"))
        app.state.models["lung_scaler"] = joblib.load(os.path.join(MODEL_DIR, "lung_cancer_scaler.pkl"))
        app.state.models["lung_features"] = joblib.load(os.path.join(MODEL_DIR, "lung_cancer_features.pkl"))
        cal_path = os.path.join(MODEL_DIR, "lung_cancer_calibrator.pkl")
        app.state.models["lung_calibrator"] = joblib.load(cal_path) if os.path.exists(cal_path) else None
        logger.info("Lung cancer models loaded successfully.")
    except Exception as e:
        # WHY: In production, missing weights must crash — silent None causes KeyError at inference time
        if _IS_PRODUCTION:
            raise RuntimeError(f"Lung cancer model weights missing — cannot start in production: {e}") from e
        logger.warning("Lung cancer model files missing (dev/test mode): %s", e)
        app.state.models["lung_model"] = None
        app.state.models["lung_scaler"] = None
        app.state.models["lung_features"] = None
        app.state.models["lung_calibrator"] = None



# ── Dependency Injectors (Circuit Breaker) ──
def get_diabetes_deps(request: Request):
    m = request.app.state.models.get("diabetes_model")
    c = request.app.state.models.get("diabetes_calibrator")
    if not m or not c:
        raise HTTPException(status_code=503, detail="Diabetes model temporarily offline.")
    return m, c

def get_heart_deps(request: Request):
    m = request.app.state.models.get("heart_model")
    c = request.app.state.models.get("heart_calibrator")
    f = request.app.state.models.get("heart_features")
    if not m or not c or not f:
        raise HTTPException(status_code=503, detail="Heart disease model temporarily offline.")
    return m, c, f

def get_lung_deps(request: Request):
    m = request.app.state.models.get("lung_model")
    s = request.app.state.models.get("lung_scaler")
    f = request.app.state.models.get("lung_features")
    c = request.app.state.models.get("lung_calibrator")
    if not m or not s or not f:
        raise HTTPException(status_code=503, detail="Lung cancer model temporarily offline.")
    return m, s, f, c

async def _run_with_timeout(func, *args, **kwargs):
    try:
        return await asyncio.wait_for(asyncio.to_thread(func, *args, **kwargs), timeout=5.0)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Model inference timed out (exceeded 5s)")

# ══════════════════════════════════════════════════════════════════════════
#  Diabetes Prediction
# ══════════════════════════════════════════════════════════════════════════

def build_diabetes_features(
    age_group: float,
    bmi: float,
    high_bp: float,
    smoker: float,
    high_cholesterol: float,
    physical_activity: float,
    general_health: float,
    mental_health: float,
) -> pd.DataFrame:
    """Build a single-row DataFrame with all 13 diabetes features."""
    features = {
        "bmi": bmi,
        "age_group": age_group,
        "high_bp": high_bp,
        "smoker": smoker,
        "high_cholesterol": high_cholesterol,
        "physical_activity": physical_activity,
        "general_health": general_health,
        "mental_health": mental_health,
        "bmi_age": bmi * age_group,
        "bmi_bp": bmi * high_bp,
        "age_bp": age_group * high_bp,
        "chol_bmi": high_cholesterol * bmi,
        "health_bmi": general_health * bmi,
    }
    return pd.DataFrame([features]).astype(np.float64)


def _sync_predict_diabetes(m, c, age_group, bmi, high_bp, smoker, high_cholesterol, physical_activity, general_health, mental_health):
    df = build_diabetes_features(age_group, bmi, high_bp, smoker, high_cholesterol, physical_activity, general_health, mental_health)
    raw_prob = m.predict_proba(df)[:, 1][0]
    cal_prob = float(np.clip(c.predict([raw_prob])[0], 0.0, 1.0))
    risk_pct = round(cal_prob * 100, 1)
    if risk_pct < 20: level = "Low"
    elif risk_pct < 45: level = "Moderate"
    else: level = "High"
    return {"risk_percentage": risk_pct, "risk_level": level}

async def predict_diabetes(request: Request, age_group, bmi, high_bp, smoker, high_cholesterol, physical_activity, general_health, mental_health):
    m, c = get_diabetes_deps(request)
    return await _run_with_timeout(_sync_predict_diabetes, m, c, age_group, bmi, high_bp, smoker, high_cholesterol, physical_activity, general_health, mental_health)



# Backward compatibility aliases
build_feature_vector = build_diabetes_features
predict = predict_diabetes


# ══════════════════════════════════════════════════════════════════════════
#  Heart Disease Prediction
# ══════════════════════════════════════════════════════════════════════════

def _sync_predict_heart(m, c, f, age, sex, bmi, high_bp, high_chol, smoker, phys_activity, fruits, veggies, heavy_drinker, gen_health, ment_health, phys_health, diabetes):
    row = {
        "_AGEG5YR": float(age), "SEX": float(sex), "_BMI5": float(bmi),
        "_RFHYPE5": float(1 - high_bp), "_RFCHOL": float(1 - high_chol),
        "SMOKE100": float(smoker), "_TOTINDA": float(phys_activity),
        "_FRTLT1": float(fruits), "_VEGLT1": float(veggies),
        "_RFDRHV5": float(1 - heavy_drinker), "GENHLTH": float(gen_health),
        "MENTHLTH": float(ment_health), "PHYSHLTH": float(phys_health), "DIABETE3": float(diabetes),
    }
    df = pd.DataFrame([row])[f].astype(np.float64)
    raw_prob = m.predict_proba(df)[:, 1][0]
    cal_prob = float(np.clip(c.predict([raw_prob])[0], 0.0, 1.0))
    risk_pct = round(cal_prob * 100, 1)
    if risk_pct < 20: level = "Low"
    elif risk_pct < 45: level = "Moderate"
    else: level = "High"
    return {"risk_percentage": risk_pct, "risk_level": level}

async def predict_heart_disease(request: Request, age, sex, bmi, high_bp, high_chol, smoker, phys_activity, fruits, veggies, heavy_drinker, gen_health, ment_health, phys_health, diabetes):
    m, c, f = get_heart_deps(request)
    return await _run_with_timeout(_sync_predict_heart, m, c, f, age, sex, bmi, high_bp, high_chol, smoker, phys_activity, fruits, veggies, heavy_drinker, gen_health, ment_health, phys_health, diabetes)



# ══════════════════════════════════════════════════════════════════════════
#  Lung Cancer Prediction
# ══════════════════════════════════════════════════════════════════════════

def _sync_predict_lung(m, s, f, c, age, gender, smoking, yellow_fingers, chronic_disease, fatigue, wheezing, shortness_of_breath):
    row = {
        "Age": float(age), "Gender": float(gender), "Smoking": float(smoking),
        "Yellow Fingers": float(yellow_fingers), "Chronic Disease": float(chronic_disease),
        "Fatigue": float(fatigue), "Wheezing": float(wheezing), "Shortness of Breath": float(shortness_of_breath),
    }
    df = pd.DataFrame([row])[f].copy()
    df["Age"] = s.transform(df[["Age"]])
    df = df.astype(np.float64)

    raw_prob = float(np.clip(m.predict_proba(df)[:, 1][0], 0.0, 1.0))
    if c is not None:
        raw_prob = float(np.clip(c.predict([raw_prob])[0], 0.0, 1.0))
    risk_pct = round(raw_prob * 100, 1)

    if risk_pct < 30: level = "Low"
    elif risk_pct < 60: level = "Moderate"
    else: level = "High"

    return {"risk_percentage": risk_pct, "risk_level": level}

async def predict_lung_cancer(request: Request, age, gender, smoking, yellow_fingers, chronic_disease, fatigue, wheezing, shortness_of_breath):
    m, s, f, c = get_lung_deps(request)
    return await _run_with_timeout(_sync_predict_lung, m, s, f, c, age, gender, smoking, yellow_fingers, chronic_disease, fatigue, wheezing, shortness_of_breath)
