#!/usr/bin/env python3
"""
evaluate_models.py
------------------
Run from project root:
    python evaluate_models.py

Outputs metrics and plots into the results/ folder.
"""

import json
import os
import warnings
from typing import Any, Dict, Iterable, Optional

import joblib
import matplotlib
import numpy as np
import pandas as pd
import shap
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")


DATA_CONFIG = {
    "diabetes": {
        "test_csv": "data/diabetes_test.csv",
        "test_csv_candidates": [
            "data/diabetes_test.csv",
            "data/processed/brfss_diabetes_clean.csv",
        ],
        "label_col": "Outcome",
        "label_aliases": ["Outcome", "diabetes", "target", "label"],
        "model": "models/diabetes_xgboost.pkl",
        "features": None,
        "scaler": None,
        "calibrator": "models/isotonic_calibrator.pkl",
        "decision_threshold": 0.5,
        "target_names": ["No Risk", "At Risk"],
    },
    "heart_disease": {
        "test_csv": "data/heart_test.csv",
        "test_csv_candidates": [
            "data/heart_test.csv",
            "data/heart_disease_test.csv",
        ],
        "label_col": "target",
        "label_aliases": ["target", "heart_disease", "Outcome", "label"],
        "model": "models/heart_disease_xgboost.pkl",
        "features": "models/heart_disease_features.pkl",
        "scaler": None,
        "calibrator": "models/heart_disease_calibrator.pkl",
        "decision_threshold": 0.2,
        "target_names": ["No Risk", "At Risk"],
    },
    "lung_cancer": {
        "test_csv": "data/lung_cancer_test.csv",
        "test_csv_candidates": [
            "data/lung_cancer_test.csv",
            "survey_lung_cancer.csv",
            "data/survey_lung_cancer.csv",
        ],
        "label_col": "LUNG_CANCER",
        "label_aliases": ["LUNG_CANCER", "lung_cancer", "target", "label"],
        "model": "models/lung_cancer_model.pkl",
        "features": "models/lung_cancer_features.pkl",
        "scaler": "models/lung_cancer_scaler.pkl",
        "calibrator": "models/lung_cancer_calibrator.pkl",
        "decision_threshold": 0.5,
        "target_names": ["No Risk", "At Risk"],
    },
}

RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)


def load_artifact(path: Optional[str]) -> Any:
    if not path:
        return None
    if not os.path.exists(path):
        return None
    try:
        return joblib.load(path)
    except Exception:
        return None


def find_existing_path(primary_path: Optional[str], candidates: Iterable[str]) -> Optional[str]:
    if primary_path and os.path.exists(primary_path):
        return primary_path
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def resolve_label_column(df: pd.DataFrame, configured_label: str, aliases: Iterable[str]) -> Optional[str]:
    if configured_label in df.columns:
        return configured_label
    for col in aliases:
        if col in df.columns:
            return col
    return None


def to_binary_series(series: pd.Series) -> pd.Series:
    normalized = series.copy()

    if normalized.dtype == object:
        normalized = normalized.astype(str).str.strip().str.lower()
        mapping = {
            "yes": 1,
            "no": 0,
            "true": 1,
            "false": 0,
            "at risk": 1,
            "no risk": 0,
            "positive": 1,
            "negative": 0,
            "1": 1,
            "0": 0,
        }
        normalized = normalized.map(mapping)

    normalized = pd.to_numeric(normalized, errors="coerce")
    normalized = normalized.dropna()

    unique_vals = set(normalized.unique().tolist())
    if unique_vals.issubset({0, 1}):
        return normalized.astype(int)

    if unique_vals.issubset({1, 2}):
        return normalized.map({1: 1, 2: 0}).astype(int)

    raise ValueError(f"Expected binary target but found values: {sorted(unique_vals)}")


def get_probabilities(model: Any, x_test: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(x_test)
        if probs.ndim == 2 and probs.shape[1] >= 2:
            return probs[:, 1]
        return probs.reshape(-1)

    if hasattr(model, "decision_function"):
        raw = model.decision_function(x_test)
        return 1.0 / (1.0 + np.exp(-raw))

    raise RuntimeError("Model does not support probability outputs.")


def apply_calibration(calibrator: Any, y_prob: np.ndarray) -> np.ndarray:
    if calibrator is None:
        return y_prob

    try:
        cal_prob = calibrator.predict(y_prob)
    except Exception:
        cal_prob = calibrator.predict(y_prob.reshape(-1, 1))

    cal_prob = np.asarray(cal_prob).reshape(-1)
    return np.clip(cal_prob, 0.0, 1.0)


def safe_target_names(target_names: Iterable[str], y_true: pd.Series) -> Optional[Iterable[str]]:
    classes = sorted(pd.Series(y_true).astype(int).unique().tolist())
    if classes == [0, 1]:
        return target_names
    return None


def evaluate(disease: str, cfg: Dict[str, Any]) -> Optional[Dict[str, float]]:
    print(f"\n{'=' * 50}")
    print(f"  Evaluating: {disease.upper()}")
    print(f"{'=' * 50}")

    out_dir = os.path.join(RESULTS_DIR, disease)
    os.makedirs(out_dir, exist_ok=True)

    csv_path = find_existing_path(cfg.get("test_csv"), cfg.get("test_csv_candidates", []))
    if not csv_path:
        print(f"  [SKIP] Test CSV not found for {disease}.")
        print(f"         Checked: {cfg.get('test_csv_candidates', [cfg.get('test_csv')])}")
        return None

    print(f"  Using test data: {csv_path}")
    df = pd.read_csv(csv_path)

    label_col = resolve_label_column(df, cfg.get("label_col", ""), cfg.get("label_aliases", []))
    if not label_col:
        print(f"  [ERROR] Could not resolve label column for {disease}.")
        print(f"          Available columns: {list(df.columns)}")
        return None

    y_raw = df[label_col]
    try:
        y_test = to_binary_series(y_raw)
    except Exception as exc:
        print(f"  [ERROR] Failed to parse label column '{label_col}': {exc}")
        return None

    df = df.loc[y_test.index].copy()

    feature_list = load_artifact(cfg.get("features"))
    if feature_list is not None:
        missing_features = [col for col in feature_list if col not in df.columns]
        if missing_features:
            print(f"  [ERROR] Missing expected features ({len(missing_features)}): {missing_features}")
            return None
        x_test = df[feature_list].copy()
    else:
        x_test = df.drop(columns=[label_col]).copy()

    scaler = load_artifact(cfg.get("scaler"))
    if scaler is not None:
        # Some models (e.g., lung cancer) fit scaler only on Age; handle both 1-col and full-matrix scalers.
        expected_scaler_features = int(getattr(scaler, "n_features_in_", x_test.shape[1]))
        if expected_scaler_features == x_test.shape[1]:
            x_test = pd.DataFrame(
                scaler.transform(x_test),
                columns=x_test.columns,
                index=x_test.index,
            )
        elif expected_scaler_features == 1 and "Age" in x_test.columns:
            x_test = x_test.copy()
            x_test[["Age"]] = scaler.transform(x_test[["Age"]])
        else:
            print(
                "  [ERROR] Scaler feature mismatch: "
                f"scaler expects {expected_scaler_features}, data has {x_test.shape[1]}"
            )
            return None

    model = load_artifact(cfg.get("model"))
    if model is None:
        print(f"  [ERROR] Model not found: {cfg.get('model')}")
        return None

    try:
        y_prob_raw = get_probabilities(model, x_test)
    except Exception as exc:
        print(f"  [ERROR] Failed to get probabilities: {exc}")
        return None

    calibrator = load_artifact(cfg.get("calibrator"))
    y_prob = apply_calibration(calibrator, y_prob_raw)
    decision_threshold = float(cfg.get("decision_threshold", 0.5))
    decision_threshold = min(max(decision_threshold, 0.0), 1.0)
    y_pred = (y_prob >= decision_threshold).astype(int)

    print(f"  Decision threshold: {decision_threshold:.2f}")

    metrics = {
        "Accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "Precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "Recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "F1-Score": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "AUC-ROC": round(float(roc_auc_score(y_test, y_prob)), 4),
    }

    print(f"\n  {'Metric':<12} {'Value':>8}")
    print(f"  {'-' * 22}")
    for key, value in metrics.items():
        print(f"  {key:<12} {value:>8}")

    report_target_names = safe_target_names(cfg.get("target_names", ["No", "Yes"]), y_test)
    print("\n  Classification Report:")
    print(
        classification_report(
            y_test,
            y_pred,
            target_names=report_target_names,
            zero_division=0,
        )
    )

    with open(os.path.join(out_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    cm = confusion_matrix(y_test, y_pred)
    disp = ConfusionMatrixDisplay(cm, display_labels=cfg.get("target_names", ["0", "1"]))
    _, ax = plt.subplots(figsize=(5, 4))
    disp.plot(ax=ax, colorbar=False, cmap="Blues")
    ax.set_title(f"Confusion Matrix - {disease.replace('_', ' ').title()}")
    plt.tight_layout()
    cm_path = os.path.join(out_dir, "confusion_matrix.png")
    plt.savefig(cm_path, dpi=150)
    plt.close()
    print(f"  Saved: {cm_path}")

    try:
        shap_sample_size = min(len(x_test), 1000)
        x_shap = x_test.sample(n=shap_sample_size, random_state=42) if len(x_test) > shap_sample_size else x_test

        explainer = shap.Explainer(model, x_shap)
        shap_values = explainer(x_shap)

        shap.summary_plot(shap_values, x_shap, show=False, plot_size=(10, 6))
        plt.title(f"SHAP Summary - {disease.replace('_', ' ').title()}")
        plt.tight_layout()
        shap_path = os.path.join(out_dir, "shap_summary.png")
        plt.savefig(shap_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  Saved: {shap_path}")
    except Exception as exc:
        print(f"  [WARN] SHAP plot failed: {exc}")

    return metrics


def main() -> None:
    all_metrics = {}

    for disease, cfg in DATA_CONFIG.items():
        result = evaluate(disease, cfg)
        if result:
            all_metrics[disease] = result

    if all_metrics:
        print(f"\n{'=' * 60}")
        print("  COMBINED RESULTS SUMMARY")
        print(f"{'=' * 60}")
        print(f"  {'Disease':<18} {'Acc':>6} {'Prec':>6} {'Rec':>6} {'F1':>6} {'AUC':>6}")
        print(f"  {'-' * 54}")
        for disease, metric_dict in all_metrics.items():
            print(
                f"  {disease:<18}"
                f" {metric_dict['Accuracy']:>6}"
                f" {metric_dict['Precision']:>6}"
                f" {metric_dict['Recall']:>6}"
                f" {metric_dict['F1-Score']:>6}"
                f" {metric_dict['AUC-ROC']:>6}"
            )

        df_summary = pd.DataFrame(all_metrics).T
        csv_path = os.path.join(RESULTS_DIR, "all_metrics.csv")
        df_summary.to_csv(csv_path)
        print(f"\n  Summary saved to: {csv_path}")
    else:
        print("\nNo evaluations were completed. Check dataset paths in DATA_CONFIG.")

    print(f"\nDone. Results directory: ./{RESULTS_DIR}/")


if __name__ == "__main__":
    main()
