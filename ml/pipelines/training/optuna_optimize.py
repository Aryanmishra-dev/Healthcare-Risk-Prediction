#!/usr/bin/env python3
"""
Optuna hyperparameter optimization script template for Healthcare Risk Prediction models.
This script demonstrates how to optimize an XGBoost classifer using Optuna.
"""

import os

import joblib
import numpy as np
import optuna
import pandas as pd
from sklearn.model_selection import cross_val_score, train_test_split
from xgboost import XGBClassifier

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
DATA_PROC = os.path.join(ROOT, "data", "processed")
os.makedirs(DATA_PROC, exist_ok=True)


def objective(trial):
    # Dummy load logic (Use actual preprocessed data here)
    # df = pd.read_csv(os.path.join(DATA_PROC, "brfss_diabetes_clean.csv"))
    # X = df.drop("diabetes", axis=1)
    # y = df["diabetes"]

    np.random.seed(42)
    X = np.random.rand(500, 10)
    y = np.random.randint(0, 2, size=500)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    param = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 1000, step=100),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "learning_rate": trial.suggest_float(
            "learning_rate", 1e-3, 0.1, log=True
        ),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, 10.0),
        "random_state": 42,
        "n_jobs": -1,
        "eval_metric": "auc",
    }

    model = XGBClassifier(**param)

    # Cross validation for robustness
    score = cross_val_score(
        model, X_train, y_train, cv=3, scoring="roc_auc", n_jobs=-1
    ).mean()
    return score


def main():
    print("Starting Optuna Hyperparameter Optimization...")
    study = optuna.create_study(
        direction="maximize", study_name="diabetes_xgboost_tuning"
    )
    study.optimize(objective, n_trials=10, timeout=600)

    print("\nBest Trial:")
    trial = study.best_trial
    print(f"  ROC AUC: {trial.value:.4f}")
    print("  Params: ")
    for key, value in trial.params.items():
        print(f"    {key}: {value}")

    # Save the study
    joblib.dump(study, os.path.join(ROOT, "ml", "models", "optuna_study.pkl"))
    print("Optuna study saved successfully.")


if __name__ == "__main__":
    main()
