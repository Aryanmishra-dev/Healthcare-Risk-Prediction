import re

with open("app/main.py", "r") as f:
    code = f.read()

# Make the explain endpoints async
code = code.replace(
    'def v1_explain_diabetes(request: Request, data: PredictionRequest, db: Session = Depends(get_db)):',
    'async def v1_explain_diabetes(request: Request, data: PredictionRequest, db: Session = Depends(get_db)):',
)

old_heart_explain = """@v1.post("/explain/heart")
def v1_explain_heart(request: Request, data: HeartDiseasePredictionRequest, db: Session = Depends(get_db)):
    \"\"\"Return SHAP feature importances for a heart disease prediction.\"\"\"
    import pandas as pd, numpy as np
    row = {
        "_AGEG5YR": float(data.age), "SEX": float(data.sex),
        "_BMI5": float(data.bmi),
        "_RFHYPE5": float(1 - data.high_bp), "_RFCHOL": float(1 - data.high_chol),
        "SMOKE100": float(data.smoker), "_TOTINDA": float(data.phys_activity),
        "_FRTLT1": float(data.fruits), "_VEGLT1": float(data.veggies),
        "_RFDRHV5": float(1 - data.heavy_drinker),
        "GENHLTH": float(data.gen_health), "MENTHLTH": float(data.ment_health),
        "PHYSHLTH": float(data.phys_health), "DIABETE3": float(data.diabetes),
    }
    from fastapi_backend.model_loader import _heart_features
    df = pd.DataFrame([row])[_heart_features].astype(np.float64)"""

new_heart_explain = """@v1.post("/explain/heart")
async def v1_explain_heart(request: Request, data: HeartDiseasePredictionRequest, db: Session = Depends(get_db)):
    \"\"\"Return SHAP feature importances for a heart disease prediction.\"\"\"
    import pandas as pd, numpy as np
    row = {
        "_AGEG5YR": float(data.age), "SEX": float(data.sex),
        "_BMI5": float(data.bmi),
        "_RFHYPE5": float(1 - data.high_bp), "_RFCHOL": float(1 - data.high_chol),
        "SMOKE100": float(data.smoker), "_TOTINDA": float(data.phys_activity),
        "_FRTLT1": float(data.fruits), "_VEGLT1": float(data.veggies),
        "_RFDRHV5": float(1 - data.heavy_drinker),
        "GENHLTH": float(data.gen_health), "MENTHLTH": float(data.ment_health),
        "PHYSHLTH": float(data.phys_health), "DIABETE3": float(data.diabetes),
    }
    f = request.app.state.models.get("heart_features")
    df = pd.DataFrame([row])[f].astype(np.float64)"""
code = code.replace(old_heart_explain, new_heart_explain)

old_lung_explain = """@v1.post("/explain/lung")
def v1_explain_lung(request: Request, data: LungCancerPredictionRequest, db: Session = Depends(get_db)):
    \"\"\"Return SHAP feature importances for a lung cancer prediction.\"\"\"
    import pandas as pd, numpy as np
    row = {
        "Age": float(data.age), "Gender": float(data.gender),
        "Smoking": float(data.smoking), "Yellow Fingers": float(data.yellow_fingers),
        "Chronic Disease": float(data.chronic_disease), "Fatigue": float(data.fatigue),
        "Wheezing": float(data.wheezing), "Shortness of Breath": float(data.shortness_of_breath),
    }
    from fastapi_backend.model_loader import _lung_features
    df = pd.DataFrame([row])[_lung_features].astype(np.float64)"""

new_lung_explain = """@v1.post("/explain/lung")
async def v1_explain_lung(request: Request, data: LungCancerPredictionRequest, db: Session = Depends(get_db)):
    \"\"\"Return SHAP feature importances for a lung cancer prediction.\"\"\"
    import pandas as pd, numpy as np
    row = {
        "Age": float(data.age), "Gender": float(data.gender),
        "Smoking": float(data.smoking), "Yellow Fingers": float(data.yellow_fingers),
        "Chronic Disease": float(data.chronic_disease), "Fatigue": float(data.fatigue),
        "Wheezing": float(data.wheezing), "Shortness of Breath": float(data.shortness_of_breath),
    }
    f = request.app.state.models.get("lung_features")
    df = pd.DataFrame([row])[f].astype(np.float64)"""
code = code.replace(old_lung_explain, new_lung_explain)

with open("app/main.py", "w") as f:
    f.write(code)

