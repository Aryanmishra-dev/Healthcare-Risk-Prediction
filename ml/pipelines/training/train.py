#!/usr/bin/env python3
"""
Full retraining pipeline for the Diabetes Risk Prediction model.

Downloads BRFSS 2015 data, applies corrected cleaning (DIABETE3 = 1 vs 3),
trains XGBoost with isotonic calibration, and exports all deployment artifacts.

Run:
    python -m ml.pipelines.training.train
"""

import os
import sys
import io
import zipfile
from urllib.parse import urlparse
import numpy as np
import pandas as pd
import requests

# ── Optional MLflow tracking ──────────────────────────────────────────────
try:
    from ml.registry.mlflow_config import init_tracking, log_training_run
    mlflow = init_tracking()
    _MLFLOW_AVAILABLE = True
    print("MLflow tracking enabled.")
except ImportError:
    _MLFLOW_AVAILABLE = False
    print("MLflow not installed — skipping experiment tracking.")

# ── Paths ─────────────────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(ROOT)
DATA_RAW = os.path.join(ROOT, "data", "raw")
DATA_PROC = os.path.join(ROOT, "data", "processed")
MODEL_DIR = os.path.join(ROOT, "ml", "models")
os.makedirs(DATA_RAW, exist_ok=True)
os.makedirs(DATA_PROC, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

XPT_PATH = os.path.join(DATA_RAW, "LLCP2015.XPT")


def _download_file_https(url: str, destination: str) -> None:
    """Download a file only from approved HTTPS hosts with request timeouts."""
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        raise ValueError("Only HTTPS downloads are allowed.")

    allowed_hosts = {"www.cdc.gov", "cdc.gov"}
    if parsed.netloc.lower() not in allowed_hosts:
        raise ValueError(f"Download host is not allowed: {parsed.netloc}")

    with requests.get(url, stream=True, timeout=(5, 120)) as response:
        response.raise_for_status()
        with open(destination, "wb") as out_file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    out_file.write(chunk)

# ══════════════════════════════════════════════════════════════════════════
# STEP 1: Download BRFSS 2015 data if not present
# ══════════════════════════════════════════════════════════════════════════
if not os.path.exists(XPT_PATH):
    url = "https://www.cdc.gov/brfss/annual_data/2015/files/LLCP2015XPT.zip"
    zip_path = os.path.join(DATA_RAW, "LLCP2015XPT.zip")

    print(f"Downloading BRFSS 2015 data from CDC...")
    print(f"  URL: {url}")
    _download_file_https(url, zip_path)
    print(f"  Downloaded: {os.path.getsize(zip_path) / 1024 / 1024:.1f} MB")

    print("  Extracting...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(DATA_RAW)
    os.remove(zip_path)
    print(f"  Extracted to: {XPT_PATH}")
else:
    print(f"BRFSS data already exists: {XPT_PATH}")

# ══════════════════════════════════════════════════════════════════════════
# STEP 2: Load and clean data with CORRECTED label encoding
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 2: Loading and cleaning BRFSS data")
print("=" * 60)

df = pd.read_sas(XPT_PATH)
print(f"  Raw data shape: {df.shape}")

# Select columns
columns = [
    "DIABETE3", "_BMI5", "_AGEG5YR", "BPHIGH4",
    "SMOKE100", "_RFCHOL", "_TOTINDA", "GENHLTH", "MENTHLTH",
]
df = df[columns]

# Rename
df = df.rename(columns={
    "DIABETE3": "diabetes",
    "_BMI5": "bmi",
    "_AGEG5YR": "age_group",
    "BPHIGH4": "high_bp",
    "SMOKE100": "smoker",
    "_RFCHOL": "high_cholesterol",
    "_TOTINDA": "physical_activity",
    "GENHLTH": "general_health",
    "MENTHLTH": "mental_health",
})

# ── BMI: raw value is ×100 ────────────────────────────────────────────────
df["bmi"] = df["bmi"] / 100

# ── CRITICAL FIX: Correct diabetes label encoding ────────────────────────
# BRFSS DIABETE3: 1=Yes, 2=Yes(pregnancy), 3=No, 4=No(borderline)
# PREVIOUS BUG: isin([1, 2]) kept only diabetic people, excluding value 3
df = df[df["diabetes"].isin([1, 3])]
df["diabetes"] = df["diabetes"].replace({1: 1, 3: 0})
print(f"  After diabetes filter: {df.shape}")
print(f"  Diabetes prevalence: {df['diabetes'].mean():.3f} ({df['diabetes'].mean()*100:.1f}%)")

# ── Recode BRFSS categoricals to clean binary (0/1) ─────────────────────
# BPHIGH4: 1=Yes, 2=Yes(preg), 3=No, 4=Borderline → 1=Yes, 0=No
df["high_bp"] = df["high_bp"].map({1: 1, 2: 1, 3: 0, 4: 1})

# SMOKE100: 1=Yes, 2=No → 1/0
df["smoker"] = df["smoker"].map({1: 1, 2: 0})

# _RFCHOL: 1=No risk, 2=Yes high cholesterol → 0/1
df["high_cholesterol"] = df["high_cholesterol"].map({1: 0, 2: 1})

# _TOTINDA: 1=Active, 2=Inactive → 1/0
df["physical_activity"] = df["physical_activity"].map({1: 1, 2: 0})

# MENTHLTH: 1-30 days, 88=None → recode 88 to 0
df["mental_health"] = df["mental_health"].replace(88, 0)

# GENHLTH: 1-5 valid, 7/9 = missing
df["general_health"] = df["general_health"].replace([7, 9], pd.NA)

# _AGEG5YR: 1-13 valid, 14=Don't know
df["age_group"] = df["age_group"].replace(14, pd.NA)

# Drop rows with any remaining NA
df = df.dropna()
print(f"  After cleaning: {df.shape}")
print(f"  Final diabetes prevalence: {df['diabetes'].mean():.3f} ({df['diabetes'].mean()*100:.1f}%)")
print(f"\n  Class distribution:")
print(f"    {df['diabetes'].value_counts().to_dict()}")

# Save clean CSV
df.to_csv(os.path.join(DATA_PROC, "brfss_diabetes_clean.csv"), index=False)
print(f"  Saved clean CSV to data/processed/")

import pandera as pa
diabetes_schema = pa.DataFrameSchema({
    "diabetes": pa.Column(float, checks=pa.Check.isin([0, 1])),
    "bmi": pa.Column(float, checks=pa.Check.ge(0)),
    "age_group": pa.Column(float, checks=pa.Check.in_range(1, 14)),
    "high_bp": pa.Column(float, checks=pa.Check.isin([0, 1])),
    "smoker": pa.Column(float, checks=pa.Check.isin([0, 1])),
    "high_cholesterol": pa.Column(float, checks=pa.Check.isin([0, 1])),
    "physical_activity": pa.Column(float, checks=pa.Check.isin([0, 1])),
    "general_health": pa.Column(float, checks=pa.Check.in_range(1, 5)),
    "mental_health": pa.Column(float, checks=pa.Check.in_range(0, 30))
})
df = diabetes_schema.validate(df)
print("  Pandera Schema Validation Passed.")

# ══════════════════════════════════════════════════════════════════════════
# STEP 3: Feature engineering
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 3: Feature engineering")
print("=" * 60)

df["bmi_age"]    = df["bmi"] * df["age_group"]
df["bmi_bp"]     = df["bmi"] * df["high_bp"]
df["age_bp"]     = df["age_group"] * df["high_bp"]
df["chol_bmi"]   = df["high_cholesterol"] * df["bmi"]
df["health_bmi"] = df["general_health"] * df["bmi"]

X = df.drop("diabetes", axis=1)
y = df["diabetes"]

feature_cols = list(X.columns)
print(f"  Features ({len(feature_cols)}): {feature_cols}")

# ══════════════════════════════════════════════════════════════════════════
# STEP 4: Train/test split
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 4: Train/test split")
print("=" * 60)

from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Ensure float64
X_train = X_train.apply(pd.to_numeric, errors="coerce").astype(np.float64)
X_test  = X_test.apply(pd.to_numeric, errors="coerce").astype(np.float64)
y_train = y_train.astype(np.float64)
y_test  = y_test.astype(np.float64)

neg = (y_train == 0).sum()
pos = (y_train == 1).sum()
scale_pos_weight = neg / pos

print(f"  Train: {X_train.shape}, Test: {X_test.shape}")
print(f"  Positive (diabetes=1): {pos:,.0f}")
print(f"  Negative (diabetes=0): {neg:,.0f}")
print(f"  scale_pos_weight: {scale_pos_weight:.4f}")

# ══════════════════════════════════════════════════════════════════════════
# STEP 5: Train XGBoost
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 5: Training XGBoost")
print("=" * 60)

from xgboost import XGBClassifier

xgb = XGBClassifier(
    n_estimators=800,
    max_depth=6,
    learning_rate=0.03,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=scale_pos_weight,
    eval_metric="auc",
    random_state=42,
    n_jobs=-1,
    early_stopping_rounds=50,
)

xgb.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=50,
)

print(f"\n  Best iteration: {xgb.best_iteration}")
print(f"  Best AUC: {xgb.best_score:.4f}")

# ══════════════════════════════════════════════════════════════════════════
# STEP 6: Evaluate
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 6: Evaluation")
print("=" * 60)

from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score

y_pred = xgb.predict(X_test)
y_prob = xgb.predict_proba(X_test)[:, 1]
roc_auc = roc_auc_score(y_test, y_prob)

print(f"  ROC AUC: {roc_auc:.4f}")
print(f"  Confusion Matrix:\n{confusion_matrix(y_test, y_pred)}")
print(f"\n{classification_report(y_test, y_pred)}")

# ══════════════════════════════════════════════════════════════════════════
# STEP 7: Isotonic Calibration
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 7: Isotonic Calibration")
print("=" * 60)

from sklearn.isotonic import IsotonicRegression
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss

# Split test set 50/50 for calibration
n_cal = len(X_test) // 2
X_cal,  X_eval  = X_test.iloc[:n_cal],  X_test.iloc[n_cal:]
y_cal,  y_eval  = y_test.iloc[:n_cal],  y_test.iloc[n_cal:]

raw_probs_cal = xgb.predict_proba(X_cal)[:, 1]
iso_reg = IsotonicRegression(out_of_bounds="clip")
iso_reg.fit(raw_probs_cal, y_cal)

# Evaluate calibration
y_prob_raw_eval = xgb.predict_proba(X_eval)[:, 1]
y_prob_cal_eval = iso_reg.predict(y_prob_raw_eval)

brier_raw = brier_score_loss(y_eval, y_prob_raw_eval)
brier_cal = brier_score_loss(y_eval, y_prob_cal_eval)
improvement = (brier_raw - brier_cal) / brier_raw * 100

print(f"  Calibration set: {X_cal.shape[0]:,} samples")
print(f"  Evaluation set:  {X_eval.shape[0]:,} samples")
print(f"  Brier Score (Raw):        {brier_raw:.4f}")
print(f"  Brier Score (Calibrated): {brier_cal:.4f}")
print(f"  Improvement:              {improvement:.1f}%")
print(f"  Prevalence in eval set:   {y_eval.mean():.3f}")
print(f"  Mean raw predicted prob:  {y_prob_raw_eval.mean():.3f}")
print(f"  Mean calibrated prob:     {y_prob_cal_eval.mean():.3f}")

# ══════════════════════════════════════════════════════════════════════════
# STEP 8: Export all artifacts
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 8: Exporting model artifacts")
print("=" * 60)

import joblib

# PKL artifacts
joblib.dump(xgb, os.path.join(MODEL_DIR, "diabetes_xgboost.pkl"))
joblib.dump(iso_reg, os.path.join(MODEL_DIR, "isotonic_calibrator.pkl"))

# Isotonic calibration as NPZ (for lightweight ONNX deployment)
np.savez(
    os.path.join(MODEL_DIR, "isotonic_calibration.npz"),
    X_thresholds=np.array(iso_reg.X_thresholds_, dtype=np.float32),
    y_thresholds=np.array(iso_reg.y_thresholds_, dtype=np.float32),
)

# SHAP explainer
import shap
explainer = shap.TreeExplainer(xgb)
joblib.dump(explainer, os.path.join(MODEL_DIR, "shap_explainer.pkl"))

# ONNX export
try:
    from onnxmltools import convert_xgboost
    from onnxmltools.convert.common.data_types import FloatTensorType

    # onnxmltools requires booster without named features
    import tempfile, xgboost as xgb_lib
    booster = xgb.get_booster()
    tmp_path = os.path.join(MODEL_DIR, "_tmp_booster.json")
    booster.save_model(tmp_path)
    clean_booster = xgb_lib.Booster()
    clean_booster.load_model(tmp_path)
    clean_booster.feature_names = None
    os.remove(tmp_path)

    onnx_input = [("features", FloatTensorType([None, 13]))]
    onnx_model = convert_xgboost(clean_booster, initial_types=onnx_input, target_opset=12)
    onnx_path = os.path.join(MODEL_DIR, "diabetes_xgboost.onnx")
    with open(onnx_path, "wb") as f:
        f.write(onnx_model.SerializeToString())
    print("  ONNX export: OK")
except ImportError:
    print("  WARNING: onnxmltools not available.")
    print("  Install with: pip install onnxmltools")
except Exception as e:
    print(f"  ONNX export error: {e}")

print("\n  Exported files:")
for f_name in sorted(os.listdir(MODEL_DIR)):
    size = os.path.getsize(os.path.join(MODEL_DIR, f_name))
    print(f"    {f_name:.<40} {size/1024:.0f} KB")

# ══════════════════════════════════════════════════════════════════════════
# STEP 9: Verification — test realistic scenarios
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 9: Verification — realistic scenarios")
print("=" * 60)

def build_and_predict(name, ag, bmi, bp, smk, chol, pa, gh, mh):
    features = np.array([[
        bmi, ag, bp, smk, chol, pa, gh, mh,
        bmi*ag, bmi*bp, ag*bp, chol*bmi, gh*bmi,
    ]], dtype=np.float64)
    df_feat = pd.DataFrame(features, columns=feature_cols)
    raw = xgb.predict_proba(df_feat)[:, 1][0]
    cal = iso_reg.predict([raw])[0]
    return raw, cal

scenarios = [
    ("Healthy 30yo",           3, 22.0, 0, 0, 0, 1, 1,  0),
    ("Average 40yo",           5, 26.0, 0, 0, 0, 1, 2,  3),
    ("Moderate 50yo+chol",     7, 28.0, 0, 0, 1, 1, 2,  5),
    ("Overweight 45yo+BP",     6, 32.0, 1, 0, 0, 0, 3,  5),
    ("High risk 60yo",         9, 35.0, 1, 1, 1, 0, 5, 15),
    ("Obese+hypertension 70", 10, 38.0, 1, 1, 1, 0, 5, 10),
]

print(f"\n  {'Scenario':<30} {'Raw':>6} {'Calibrated':>12} {'Level':>10}")
print(f"  {'-'*60}")
for name, *args in scenarios:
    raw, cal = build_and_predict(name, *args)
    level = "Low" if cal < 0.20 else "Moderate" if cal < 0.45 else "High"
    print(f"  {name:<30} {raw:>5.3f} {cal*100:>10.1f}% {level:>10}")

# ══════════════════════════════════════════════════════════════════════════
# STEP 10: MLflow experiment tracking
# ══════════════════════════════════════════════════════════════════════════
if _MLFLOW_AVAILABLE:
    print("\n" + "=" * 60)
    print("STEP 10: Logging to MLflow")
    print("=" * 60)
    log_training_run(
        model_name="diabetes_xgboost",
        params={
            "n_estimators": 800,
            "max_depth": 6,
            "learning_rate": 0.03,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "scale_pos_weight": round(scale_pos_weight, 4),
            "best_iteration": xgb.best_iteration,
        },
        metrics={
            "roc_auc": roc_auc,
            "brier_raw": brier_raw,
            "brier_calibrated": brier_cal,
            "calibration_improvement_pct": round(improvement, 2),
        },
        artifacts=[
            os.path.join(MODEL_DIR, "diabetes_xgboost.pkl"),
            os.path.join(MODEL_DIR, "isotonic_calibrator.pkl"),
        ],
        tags={"algorithm": "XGBoost", "dataset": "BRFSS_2015"},
    )

print("\n" + "=" * 60)
print("RETRAINING COMPLETE")
print("=" * 60)
