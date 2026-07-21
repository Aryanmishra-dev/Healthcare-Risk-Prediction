"""
Model prediction logic for the healthcare risk prediction API.

Delegates model loading and caching to ModelManager.
"""

import asyncio
import logging
import os

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from fastapi import HTTPException, Request

from backend.app.services.model_manager import model_manager

logger = logging.getLogger(__name__)


def load_models(app):
    """Load models synchronously for legacy callers and tests.
    NOTE: Kept for test compatibility — model_manager.load_all_models()
    is the preferred path.
    """
    app.state.models = {}
    model_manager.models["diabetes"].update(
        {
            "status": "ready",
            "version": "local",
            "stage": "Local",
            "latency_ms": 0.0,
            "deps": model_manager._fetch_diabetes_from_disk(),
        }
    )
    model_manager.models["heart_disease"].update(
        {
            "status": "ready",
            "version": "local",
            "stage": "Local",
            "latency_ms": 0.0,
            "deps": model_manager._fetch_heart_disease_from_disk(),
        }
    )
    model_manager.models["lung_cancer"].update(
        {
            "status": "ready",
            "version": "local",
            "stage": "Local",
            "latency_ms": 0.0,
            "deps": model_manager._fetch_lung_cancer_from_disk(),
        }
    )
    app.state.models.update(model_manager.export_app_state())
    logger.info("local_models_loaded")


# ── Dependency Injectors (Circuit Breaker) ──
def get_diabetes_deps(request: Request):
    try:
        return model_manager.get_diabetes_deps()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


def get_heart_deps(request: Request):
    try:
        return model_manager.get_heart_deps()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


def get_lung_deps(request: Request):
    try:
        return model_manager.get_lung_deps()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


PREDICTION_TIMEOUT = float(os.environ.get("PREDICTION_TIMEOUT_SECONDS", "5.0"))


async def _run_with_timeout(func, *args, **kwargs):
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(func, *args, **kwargs),
            timeout=PREDICTION_TIMEOUT,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=(
                "Model inference timed out "
                f"(exceeded {PREDICTION_TIMEOUT}s)"
            ),
        )


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


def _sync_predict_diabetes(
    m,
    c,
    age_group,
    bmi,
    high_bp,
    smoker,
    high_cholesterol,
    physical_activity,
    general_health,
    mental_health,
):
    df = build_diabetes_features(
        age_group,
        bmi,
        high_bp,
        smoker,
        high_cholesterol,
        physical_activity,
        general_health,
        mental_health,
    )
    raw_prob = m.predict_proba(df)[:, 1][0]
    cal_prob = float(np.clip(c.predict([raw_prob])[0], 0.0, 1.0))
    risk_pct = round(cal_prob * 100, 1)
    if risk_pct < 20:
        level = "Low"
    elif risk_pct < 45:
        level = "Moderate"
    else:
        level = "High"
    return {"risk_percentage": risk_pct, "risk_level": level}


async def predict_diabetes(
    request: Request,
    age_group,
    bmi,
    high_bp,
    smoker,
    high_cholesterol,
    physical_activity,
    general_health,
    mental_health,
):
    m, c = get_diabetes_deps(request)
    return await _run_with_timeout(
        _sync_predict_diabetes,
        m,
        c,
        age_group,
        bmi,
        high_bp,
        smoker,
        high_cholesterol,
        physical_activity,
        general_health,
        mental_health,
    )


# Backward compatibility aliases
build_feature_vector = build_diabetes_features
predict = predict_diabetes


# ══════════════════════════════════════════════════════════════════════════
#  Heart Disease Prediction
# ══════════════════════════════════════════════════════════════════════════


def _sync_predict_heart(
    m,
    c,
    f,
    age,
    sex,
    bmi,
    high_bp,
    high_chol,
    smoker,
    phys_activity,
    fruits,
    veggies,
    heavy_drinker,
    gen_health,
    ment_health,
    phys_health,
    diabetes,
):
    # BRFSS-derived columns _RFHYPE5, _RFCHOL, _RFDRHV5 use 1=Yes/2=No
    # encoding. Our inputs are 0/1 where 1=condition present.
    # --high_bp=1 → _RFHYPE5=0.0 (condition present, inverted indicator)
    # This inversion matches the encoding used during stub training.
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
    feature_order = f or list(row.keys())
    df = pd.DataFrame([row])[feature_order].astype(np.float64)
    raw_prob = m.predict_proba(df)[:, 1][0]
    cal_prob = float(np.clip(c.predict([raw_prob])[0], 0.0, 1.0))
    risk_pct = round(cal_prob * 100, 1)
    if risk_pct < 20:
        level = "Low"
    elif risk_pct < 45:
        level = "Moderate"
    else:
        level = "High"
    return {"risk_percentage": risk_pct, "risk_level": level}


async def predict_heart_disease(
    request: Request,
    age,
    sex,
    bmi,
    high_bp,
    high_chol,
    smoker,
    phys_activity,
    fruits,
    veggies,
    heavy_drinker,
    gen_health,
    ment_health,
    phys_health,
    diabetes,
):
    m, c, f = get_heart_deps(request)
    return await _run_with_timeout(
        _sync_predict_heart,
        m,
        c,
        f,
        age,
        sex,
        bmi,
        high_bp,
        high_chol,
        smoker,
        phys_activity,
        fruits,
        veggies,
        heavy_drinker,
        gen_health,
        ment_health,
        phys_health,
        diabetes,
    )


# ══════════════════════════════════════════════════════════════════════════
#  Lung Cancer Prediction
# ══════════════════════════════════════════════════════════════════════════


def _sync_predict_lung(
    m,
    s,
    f,
    c,
    age,
    gender,
    smoking,
    yellow_fingers,
    chronic_disease,
    fatigue,
    wheezing,
    shortness_of_breath,
):
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
    feature_order = f or list(row.keys())
    df = pd.DataFrame([row])[feature_order].copy()
    if s is not None and "Age" in df:
        df["Age"] = s.transform(df[["Age"]])
    df = df.astype(np.float64)

    raw_prob = float(np.clip(m.predict_proba(df)[:, 1][0], 0.0, 1.0))
    if c is not None:
        raw_prob = float(np.clip(c.predict([raw_prob])[0], 0.0, 1.0))
    risk_pct = round(raw_prob * 100, 1)

    if risk_pct < 30:
        level = "Low"
    elif risk_pct < 60:
        level = "Moderate"
    else:
        level = "High"

    return {"risk_percentage": risk_pct, "risk_level": level}


async def predict_lung_cancer(
    request: Request,
    age,
    gender,
    smoking,
    yellow_fingers,
    chronic_disease,
    fatigue,
    wheezing,
    shortness_of_breath,
):
    m, s, f, c = get_lung_deps(request)
    return await _run_with_timeout(
        _sync_predict_lung,
        m,
        s,
        f,
        c,
        age,
        gender,
        smoking,
        yellow_fingers,
        chronic_disease,
        fatigue,
        wheezing,
        shortness_of_breath,
    )
