import re

with open("fastapi_backend/model_loader.py", "r") as f:
    code = f.read()

diab = """def _load_diabetes_models(app):
    try:
        app.state.models["diabetes_model"] = joblib.load(os.path.join(MODEL_DIR, "diabetes_xgboost.pkl"))
        app.state.models["diabetes_calibrator"] = joblib.load(os.path.join(MODEL_DIR, "isotonic_calibrator.pkl"))
        logger.info("Diabetes models loaded successfully.")
    except FileNotFoundError as e:
        logger.error("Diabetes model files missing: %s", e)
        app.state.models["diabetes_model"] = None
        app.state.models["diabetes_calibrator"] = None"""

heart = """def _load_heart_disease_models(app):
    try:
        app.state.models["heart_model"] = joblib.load(os.path.join(MODEL_DIR, "heart_disease_xgboost.pkl"))
        app.state.models["heart_calibrator"] = joblib.load(os.path.join(MODEL_DIR, "heart_disease_calibrator.pkl"))
        app.state.models["heart_features"] = joblib.load(os.path.join(MODEL_DIR, "heart_disease_features.pkl"))
        logger.info("Heart disease models loaded successfully.")
    except Exception as e:
        logger.error("Heart disease model files missing: %s", e)
        app.state.models["heart_model"] = None
        app.state.models["heart_calibrator"] = None
        app.state.models["heart_features"] = None"""

lung = """def _load_lung_cancer_models(app):
    try:
        app.state.models["lung_model"] = joblib.load(os.path.join(MODEL_DIR, "lung_cancer_model.pkl"))
        app.state.models["lung_scaler"] = joblib.load(os.path.join(MODEL_DIR, "lung_cancer_scaler.pkl"))
        app.state.models["lung_features"] = joblib.load(os.path.join(MODEL_DIR, "lung_cancer_features.pkl"))
        cal_path = os.path.join(MODEL_DIR, "lung_cancer_calibrator.pkl")
        app.state.models["lung_calibrator"] = joblib.load(cal_path) if os.path.exists(cal_path) else None
        logger.info("Lung cancer models loaded successfully.")
    except Exception as e:
        logger.error("Lung cancer model files missing: %s", e)
        app.state.models["lung_model"] = None
        app.state.models["lung_scaler"] = None
        app.state.models["lung_features"] = None
        app.state.models["lung_calibrator"] = None"""

# Replace diabetes
code = re.sub(r'def _load_diabetes_models\(app\):.*?raise', diab, code, flags=re.DOTALL)
# Replace heart
code = re.sub(r'def _load_heart_disease_models\(app\):.*?raise', heart, code, flags=re.DOTALL)
# Replace lung
code = re.sub(r'def _load_lung_cancer_models\(app\):.*?raise', lung, code, flags=re.DOTALL)

with open("fastapi_backend/model_loader.py", "w") as f:
    f.write(code)

