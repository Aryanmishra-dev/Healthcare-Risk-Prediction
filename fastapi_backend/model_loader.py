"""
Model loading and prediction logic for the healthcare risk prediction API.

Supports multiple disease models (diabetes, heart disease, etc.).
Each disease has its own load/predict functions.
"""

import logging
import os

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(ROOT, "models")

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

def load_models():
    """Load all disease models at startup."""
    _load_diabetes_models()
    _load_heart_disease_models()
    _load_lung_cancer_models()


def _load_diabetes_models():
    global _diabetes_model, _diabetes_calibrator
    try:
        _diabetes_model = joblib.load(os.path.join(MODEL_DIR, "diabetes_xgboost.pkl"))
        _diabetes_calibrator = joblib.load(os.path.join(MODEL_DIR, "isotonic_calibrator.pkl"))
        logger.info("Diabetes models loaded successfully.")
    except FileNotFoundError as e:
        logger.error("Diabetes model files not found: %s", e)
        raise


def _load_heart_disease_models():
    global _heart_model, _heart_calibrator, _heart_features
    try:
        _heart_model = joblib.load(os.path.join(MODEL_DIR, "heart_disease_xgboost.pkl"))
        _heart_calibrator = joblib.load(os.path.join(MODEL_DIR, "heart_disease_calibrator.pkl"))
        _heart_features = joblib.load(os.path.join(MODEL_DIR, "heart_disease_features.pkl"))
        logger.info("Heart disease models loaded successfully. Features: %s", _heart_features)
    except FileNotFoundError as e:
        logger.error("Heart disease model files not found: %s", e)
        raise


def _load_lung_cancer_models():
    global _lung_model, _lung_scaler, _lung_features, _lung_calibrator
    try:
        _lung_model = joblib.load(os.path.join(MODEL_DIR, "lung_cancer_model.pkl"))
        _lung_scaler = joblib.load(os.path.join(MODEL_DIR, "lung_cancer_scaler.pkl"))
        _lung_features = joblib.load(os.path.join(MODEL_DIR, "lung_cancer_features.pkl"))
        # Optional isotonic calibrator
        cal_path = os.path.join(MODEL_DIR, "lung_cancer_calibrator.pkl")
        if os.path.exists(cal_path):
            _lung_calibrator = joblib.load(cal_path)
            logger.info("Lung cancer calibrator loaded.")
        logger.info("Lung cancer models loaded successfully. Features: %s", _lung_features)
    except FileNotFoundError as e:
        logger.error("Lung cancer model files not found: %s", e)
        raise


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


def predict_diabetes(
    age_group: float,
    bmi: float,
    high_bp: float,
    smoker: float,
    high_cholesterol: float,
    physical_activity: float,
    general_health: float,
    mental_health: float,
) -> dict:
    """Run diabetes inference and return risk percentage + level."""
    if _diabetes_model is None or _diabetes_calibrator is None:
        raise RuntimeError("Diabetes model not loaded. Restart the server.")
    df = build_diabetes_features(
        age_group, bmi, high_bp, smoker, high_cholesterol,
        physical_activity, general_health, mental_health,
    )

    raw_prob = _diabetes_model.predict_proba(df)[:, 1][0]
    cal_prob = float(np.clip(_diabetes_calibrator.predict([raw_prob])[0], 0.0, 1.0))
    risk_pct = round(cal_prob * 100, 1)

    if risk_pct < 20:
        level = "Low"
    elif risk_pct < 45:
        level = "Moderate"
    else:
        level = "High"

    return {"risk_percentage": risk_pct, "risk_level": level}


# Backward compatibility aliases
build_feature_vector = build_diabetes_features
predict = predict_diabetes


# ══════════════════════════════════════════════════════════════════════════
#  Heart Disease Prediction
# ══════════════════════════════════════════════════════════════════════════

def predict_heart_disease(
    age: float,
    sex: int,
    bmi: float,
    high_bp: int,
    high_chol: int,
    smoker: int,
    phys_activity: int,
    fruits: int,
    veggies: int,
    heavy_drinker: int,
    gen_health: int,
    ment_health: int,
    phys_health: int,
    diabetes: int,
) -> dict:
    """Run heart disease inference and return risk percentage + level."""
    if _heart_model is None or _heart_calibrator is None or _heart_features is None:
        raise RuntimeError("Heart disease model not loaded. Restart the server.")
    # Build DataFrame with columns in the exact order the model expects
    # The heart disease model was trained with BRFSS calculated-variable encoding
    # where _RFHYPE5, _RFCHOL, _RFDRHV5 use 1=No-risk, 0=Has-risk (inverted).
    # Flip user-friendly 1=Yes/0=No to match the model's learned encoding.
    row = {
        "_AGEG5YR": float(age),
        "SEX": float(sex),
        "_BMI5": float(bmi),
        "_RFHYPE5": float(1 - high_bp),
        "_RFCHOL": float(1 - high_chol),
        "SMOKE100": float(smoker),
        "_TOTINDA": float(phys_activity),
        "_FRTLT1": float(fruits),
        "_VEGLT1": float(veggies),
        "_RFDRHV5": float(1 - heavy_drinker),
        "GENHLTH": float(gen_health),
        "MENTHLTH": float(ment_health),
        "PHYSHLTH": float(phys_health),
        "DIABETE3": float(diabetes),
    }
    df = pd.DataFrame([row])[_heart_features].astype(np.float64)

    raw_prob = _heart_model.predict_proba(df)[:, 1][0]
    cal_prob = float(np.clip(_heart_calibrator.predict([raw_prob])[0], 0.0, 1.0))
    risk_pct = round(cal_prob * 100, 1)

    if risk_pct < 20:
        level = "Low"
    elif risk_pct < 45:
        level = "Moderate"
    else:
        level = "High"

    return {"risk_percentage": risk_pct, "risk_level": level}


# ══════════════════════════════════════════════════════════════════════════
#  Lung Cancer Prediction
# ══════════════════════════════════════════════════════════════════════════

def predict_lung_cancer(
    age: int,
    gender: int,
    smoking: int,
    yellow_fingers: int,
    chronic_disease: int,
    fatigue: int,
    wheezing: int,
    shortness_of_breath: int,
) -> dict:
    """Run lung cancer inference and return risk percentage + level."""
    if _lung_model is None or _lung_scaler is None or _lung_features is None:
        raise RuntimeError("Lung cancer model not loaded. Restart the server.")
    row = {
        "Age": float(age),
        "Gender": float(gender),
        "Smoking": float(smoking),
        "Yellow Fingers": float(yellow_fingers),
        "Chronic Disease": float(chronic_disease),
        "Fatigue": float(fatigue),
        "Wheezing": float(wheezing),
        "Shortness of Breath": float(shortness_of_breath),
    }
    df = pd.DataFrame([row])[_lung_features].copy()
    df["Age"] = _lung_scaler.transform(df[["Age"]])
    df = df.astype(np.float64)

    raw_prob = float(np.clip(_lung_model.predict_proba(df)[:, 1][0], 0.0, 1.0))
    if _lung_calibrator is not None:
        raw_prob = float(np.clip(_lung_calibrator.predict([raw_prob])[0], 0.0, 1.0))
    risk_pct = round(raw_prob * 100, 1)

    if risk_pct < 30:
        level = "Low"
    elif risk_pct < 60:
        level = "Moderate"
    else:
        level = "High"

    return {"risk_percentage": risk_pct, "risk_level": level}
