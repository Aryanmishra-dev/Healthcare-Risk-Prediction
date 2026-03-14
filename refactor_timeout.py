import re

with open("fastapi_backend/model_loader.py", "r") as f:
    loader_code = f.read()

new_imports = """
import logging
import os
import asyncio
import joblib
import numpy as np
import pandas as pd
from fastapi import Request, HTTPException
"""
loader_code = loader_code.replace("import logging\nimport os\n\nimport joblib\nimport numpy as np\nimport pandas as pd", new_imports.strip())

# Change load_models to accept app
loader_code = loader_code.replace("def load_models():", "def load_models(app):\n    app.state.models = {}")
loader_code = loader_code.replace("_load_diabetes_models()", "_load_diabetes_models(app)")
loader_code = loader_code.replace("_load_heart_disease_models()", "_load_heart_disease_models(app)")
loader_code = loader_code.replace("_load_lung_cancer_models()", "_load_lung_cancer_models(app)")

# Rewrite _load_diabetes_models
diab_old = """def _load_diabetes_models():
    global _diabetes_model, _diabetes_calibrator
    try:
        _diabetes_model = joblib.load(os.path.join(MODEL_DIR, "diabetes_xgboost.pkl"))
        _diabetes_calibrator = joblib.load(os.path.join(MODEL_DIR, "isotonic_calibrator.pkl"))
        logger.info("Diabetes models loaded successfully.")
    except FileNotFoundError as e:
        logger.error("Diabetes model files not found: %s", e)
        raise"""

diab_new = """def _load_diabetes_models(app):
    try:
        app.state.models["diabetes_model"] = joblib.load(os.path.join(MODEL_DIR, "diabetes_xgboost.pkl"))
        app.state.models["diabetes_calibrator"] = joblib.load(os.path.join(MODEL_DIR, "isotonic_calibrator.pkl"))
        logger.info("Diabetes models loaded successfully.")
    except FileNotFoundError as e:
        logger.error("Diabetes model files missing: %s", e)
        app.state.models["diabetes_model"] = None"""
loader_code = loader_code.replace(diab_old, diab_new)

# Rewrite _load_heart_disease_models
heart_old = """def _load_heart_disease_models():
    global _heart_model, _heart_calibrator, _heart_features
    try:
        _heart_model = joblib.load(os.path.join(MODEL_DIR, "heart_disease_xgboost.pkl"))
        _heart_calibrator = joblib.load(os.path.join(MODEL_DIR, "heart_disease_calibrator.pkl"))
        _heart_features = joblib.load(os.path.join(MODEL_DIR, "heart_disease_features.pkl"))
        logger.info("Heart disease models loaded successfully. Features: %s", _heart_features)
    except FileNotFoundError as e:
        logger.error("Heart disease model files not found: %s", e)
        raise"""

heart_new = """def _load_heart_disease_models(app):
    try:
        app.state.models["heart_model"] = joblib.load(os.path.join(MODEL_DIR, "heart_disease_xgboost.pkl"))
        app.state.models["heart_calibrator"] = joblib.load(os.path.join(MODEL_DIR, "heart_disease_calibrator.pkl"))
        app.state.models["heart_features"] = joblib.load(os.path.join(MODEL_DIR, "heart_disease_features.pkl"))
        logger.info("Heart disease models loaded successfully.")
    except FileNotFoundError as e:
        logger.error("Heart disease model files missing: %s", e)
        app.state.models["heart_model"] = None"""
loader_code = loader_code.replace(heart_old, heart_new)

# Rewrite _load_lung_cancer_models
lung_old = """def _load_lung_cancer_models():
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
        raise"""

lung_new = """def _load_lung_cancer_models(app):
    try:
        app.state.models["lung_model"] = joblib.load(os.path.join(MODEL_DIR, "lung_cancer_model.pkl"))
        app.state.models["lung_scaler"] = joblib.load(os.path.join(MODEL_DIR, "lung_cancer_scaler.pkl"))
        app.state.models["lung_features"] = joblib.load(os.path.join(MODEL_DIR, "lung_cancer_features.pkl"))
        cal_path = os.path.join(MODEL_DIR, "lung_cancer_calibrator.pkl")
        app.state.models["lung_calibrator"] = joblib.load(cal_path) if os.path.exists(cal_path) else None
        logger.info("Lung cancer models loaded successfully.")
    except FileNotFoundError as e:
        logger.error("Lung cancer files missing: %s", e)
        app.state.models["lung_model"] = None"""
loader_code = loader_code.replace(lung_old, lung_new)

# Define Dependency Injectors & Async run Wrappers
deps_code = """
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

"""
loader_code = loader_code.replace("# ══════════════════════════════════════════════════════════════════════════\n#  Diabetes Prediction", deps_code + "# ══════════════════════════════════════════════════════════════════════════\n#  Diabetes Prediction")

# Refactor the sync predict methods to accept deps
p_diabetes_old = """def predict_diabetes(
    age_group: float,
    bmi: float,
    high_bp: float,
    smoker: float,
    high_cholesterol: float,
    physical_activity: float,
    general_health: float,
    mental_health: float,
) -> dict:
    \"\"\"Run diabetes inference and return risk percentage + level.\"\"\"
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

    return {"risk_percentage": risk_pct, "risk_level": level}"""

p_diabetes_new = """def _sync_predict_diabetes(m, c, age_group, bmi, high_bp, smoker, high_cholesterol, physical_activity, general_health, mental_health):
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
"""
loader_code = loader_code.replace(p_diabetes_old, p_diabetes_new)

p_heart_old = """def predict_heart_disease(
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
    \"\"\"Run heart disease inference and return risk percentage + level.\"\"\"
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

    return {"risk_percentage": risk_pct, "risk_level": level}"""

p_heart_new = """def _sync_predict_heart(m, c, f, age, sex, bmi, high_bp, high_chol, smoker, phys_activity, fruits, veggies, heavy_drinker, gen_health, ment_health, phys_health, diabetes):
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
"""
loader_code = loader_code.replace(p_heart_old, p_heart_new)

p_lung_old = """def predict_lung_cancer(
    age: int,
    gender: int,
    smoking: int,
    yellow_fingers: int,
    chronic_disease: int,
    fatigue: int,
    wheezing: int,
    shortness_of_breath: int,
) -> dict:
    \"\"\"Run lung cancer inference and return risk percentage + level.\"\"\"
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

    return {"risk_percentage": risk_pct, "risk_level": level}"""

p_lung_new = """def _sync_predict_lung(m, s, f, c, age, gender, smoking, yellow_fingers, chronic_disease, fatigue, wheezing, shortness_of_breath):
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
"""
loader_code = loader_code.replace(p_lung_old, p_lung_new)

with open("fastapi_backend/model_loader.py", "w") as f:
    f.write(loader_code)
