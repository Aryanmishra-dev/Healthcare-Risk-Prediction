"""
Diabetes Risk Assistant — Interactive CLI + Gradio UI

Uses the trained XGBoost model with isotonic probability calibration
and SHAP explanations to provide per-patient risk assessments.

Usage:
    CLI mode  :  python -m ml.pipelines.inference.risk_assistant
    Gradio UI :  python -m ml.pipelines.inference.risk_assistant --ui
"""

import sys
import os
import argparse
import numpy as np
import pandas as pd
import joblib

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT      = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
MODEL_DIR = os.path.join(ROOT, "ml", "models")

# ── Load artefacts ─────────────────────────────────────────────────────────
xgb_model  = joblib.load(os.path.join(MODEL_DIR, "diabetes_xgboost.pkl"))
iso_reg    = joblib.load(os.path.join(MODEL_DIR, "isotonic_calibrator.pkl"))
explainer  = joblib.load(os.path.join(MODEL_DIR, "shap_explainer.pkl"))


# ── Isotonic calibrator wrapper ────────────────────────────────────────────
class CalibratedModel:
    def __init__(self, base, calibrator):
        self.base = base
        self.calibrator = calibrator

    def predict_proba(self, X):
        raw = self.base.predict_proba(X)[:, 1]
        cal = self.calibrator.predict(raw)
        return np.column_stack([1.0 - cal, cal])


calibrated_model = CalibratedModel(xgb_model, iso_reg)


# ── Feature builder ───────────────────────────────────────────────────────
def build_features(age_group, bmi, high_bp, smoker, high_cholesterol,
                   physical_activity, general_health, mental_health):
    feats = {
        "bmi": bmi, "age_group": age_group, "high_bp": high_bp,
        "smoker": smoker, "high_cholesterol": high_cholesterol,
        "physical_activity": physical_activity,
        "general_health": general_health, "mental_health": mental_health,
        "bmi_age": bmi * age_group, "bmi_bp": bmi * high_bp,
        "age_bp": age_group * high_bp, "chol_bmi": high_cholesterol * bmi,
        "health_bmi": general_health * bmi,
    }
    return pd.DataFrame([feats]).astype(np.float64)


# ── Core prediction ───────────────────────────────────────────────────────
def predict_risk(age_group, bmi, high_bp, smoker, high_cholesterol,
                 physical_activity, general_health, mental_health):
    """Return a formatted risk report string."""
    df = build_features(age_group, bmi, high_bp, smoker, high_cholesterol,
                        physical_activity, general_health, mental_health)

    cal_prob = calibrated_model.predict_proba(df)[0, 1]
    raw_prob = xgb_model.predict_proba(df)[:, 1][0]

    shap_vals = explainer.shap_values(df)[0]
    feat_names = list(df.columns)
    contribs = pd.Series(shap_vals, index=feat_names).sort_values(key=abs, ascending=False)

    if cal_prob < 0.20:
        level = "LOW"
    elif cal_prob < 0.45:
        level = "MODERATE"
    else:
        level = "HIGH"

    lines = [
        "=" * 52,
        "   DIABETES RISK ASSESSMENT",
        "=" * 52,
        f"",
        f"   Estimated Diabetes Risk : {cal_prob:.2f}  ({cal_prob * 100:.1f}%)",
        f"   Risk Level              : {level}",
        f"   Model Confidence        : calibrated probability",
        f"   (Raw model score        : {raw_prob:.2f})",
        f"",
        f"   Top Contributing Factors:",
        "   " + "-" * 42,
    ]
    total_abs = sum(abs(contribs))
    for feat, val in contribs.head(5).items():
        d = "+" if val > 0 else "-"
        label = feat.replace("_", " ").title()
        pct = abs(val) / total_abs * 100
        lines.append(f"   {d} {label:.<34} {pct:5.1f}%")
    lines.append("")
    lines.append("=" * 52)
    return "\n".join(lines)


# ── CLI mode ──────────────────────────────────────────────────────────────
def cli():
    print("\n🩺  Diabetes Risk Calculator  (type 'q' to quit)\n")
    while True:
        try:
            age   = float(input("Age group  (1-13, 1=18-24 … 13=80+) : "))
            bmi   = float(input("BMI        (e.g. 27.5)              : "))
            bp    = float(input("High BP    (1=Yes 0=No)             : "))
            smoke = float(input("Smoker     (1=Yes 0=No)             : "))
            chol  = float(input("High chol  (1=Yes 0=No)             : "))
            pa    = float(input("Phys act   (1=Active 0=Inactive)    : "))
            gh    = float(input("Gen health (1=Excellent … 5=Poor)   : "))
            mh    = float(input("Mental hlth days (0-30)             : "))
        except (ValueError, EOFError):
            break

        report = predict_risk(age, bmi, bp, smoke, chol, pa, gh, mh)
        print("\n" + report + "\n")

        again = input("Another patient? (y/n): ").strip().lower()
        if again != "y":
            break


# ── Gradio UI ─────────────────────────────────────────────────────────────
def launch_ui():
    try:
        import gradio as gr
    except ImportError:
        print("Install Gradio first:  pip install gradio")
        sys.exit(1)

    def ui_predict(age_group, bmi, high_bp, smoker, high_cholesterol,
                   physical_activity, general_health, mental_health):
        return predict_risk(age_group, bmi, high_bp, smoker, high_cholesterol,
                            physical_activity, general_health, mental_health)

    iface = gr.Interface(
        fn=ui_predict,
        inputs=[
            gr.Slider(1, 13, step=1, value=7, label="Age Group (1=18-24 … 13=80+)"),
            gr.Number(value=27.5, label="BMI"),
            gr.Radio([("Yes", 1), ("No", 0)], value=0, label="High Blood Pressure"),
            gr.Radio([("Yes", 1), ("No", 0)], value=0, label="Smoker (100+ cigarettes ever)"),
            gr.Radio([("Yes", 1), ("No", 0)], value=0, label="High Cholesterol"),
            gr.Radio([("Active", 1), ("Inactive", 0)], value=1, label="Physical Activity"),
            gr.Slider(1, 5, step=1, value=3, label="General Health (1=Excellent … 5=Poor)"),
            gr.Number(value=0, label="Days of Poor Mental Health (0-30)"),
        ],
        outputs=gr.Textbox(label="Risk Assessment", lines=16),
        title="🩺 Diabetes Risk Calculator",
        description="Enter clinical indicators to receive a calibrated diabetes risk estimate with SHAP-driven explanations.",
        flagging_mode="never",
    )
    iface.launch()


# ── Entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diabetes Risk Assistant")
    parser.add_argument("--ui", action="store_true", help="Launch Gradio web UI")
    args = parser.parse_args()

    if args.ui:
        launch_ui()
    else:
        cli()
