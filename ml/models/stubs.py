"""
Stub model classes for healthcare risk prediction.

WHY: These classes implement the same API as the real sklearn/xgboost models
(predict_proba, predict, transform) but use simple weighted heuristics instead
of trained weights. They are used in two places:
  1. Serialized to .pkl files in ml/models/ for integration tests
  2. Instantiated directly in tests/unit/ml/conftest.py for unit tests

This module lives in ml/models/ so joblib can resolve the classes when
deserializing the .pkl files (pickle needs the original module path).
"""

import numpy as np


class StubDiabetesClassifier:
    """Stub XGBoost classifier for diabetes — deterministic, input-sensitive."""

    def predict_proba(self, X):
        arr = np.asarray(X, dtype=np.float64)
        n = arr.shape[0]
        probs = np.zeros(n)
        for i in range(n):
            bmi = arr[i, 0]
            age_group = arr[i, 1]
            high_bp = arr[i, 2]
            smoker = arr[i, 3]
            high_chol = arr[i, 4]
            phys_activity = arr[i, 5]
            gen_health = arr[i, 6]
            mental_health = arr[i, 7]
            score = (
                (bmi - 18) / 40.0 * 0.25
                + (age_group - 1) / 12.0 * 0.20
                + high_bp * 0.10
                + smoker * 0.08
                + high_chol * 0.10
                + (1 - phys_activity) * 0.05
                + (gen_health - 1) / 4.0 * 0.12
                + mental_health / 30.0 * 0.10
            )
            probs[i] = np.clip(score, 0.01, 0.99)
        return np.column_stack([1.0 - probs, probs])


class StubHeartClassifier:
    """Stub XGBoost classifier for heart disease — deterministic, input-sensitive."""

    def predict_proba(self, X):
        arr = np.asarray(X, dtype=np.float64)
        n = arr.shape[0]
        probs = np.zeros(n)
        for i in range(n):
            age = arr[i, 0]
            bmi = arr[i, 2]
            no_bp = arr[i, 3]
            no_chol = arr[i, 4]
            smoker = arr[i, 5]
            phys = arr[i, 6]
            no_drink = arr[i, 9]
            gen_health = arr[i, 10]
            diabetes = arr[i, 13]
            score = (
                (age - 1) / 12.0 * 0.20
                + (bmi - 18) / 40.0 * 0.15
                + (1 - no_bp) * 0.12
                + (1 - no_chol) * 0.10
                + smoker * 0.08
                + (1 - phys) * 0.05
                + (1 - no_drink) * 0.05
                + (gen_health - 1) / 4.0 * 0.10
                + diabetes * 0.15
            )
            probs[i] = np.clip(score, 0.01, 0.99)
        return np.column_stack([1.0 - probs, probs])


class StubLungClassifier:
    """Stub classifier for lung cancer — deterministic, input-sensitive."""

    def predict_proba(self, X):
        arr = np.asarray(X, dtype=np.float64)
        n = arr.shape[0]
        probs = np.zeros(n)
        for i in range(n):
            age_scaled = arr[i, 0]
            smoking = arr[i, 2]
            yellow_fingers = arr[i, 3]
            chronic = arr[i, 4]
            fatigue = arr[i, 5]
            wheezing = arr[i, 6]
            sob = arr[i, 7]
            age_contrib = np.clip((age_scaled + 1.67) / 4.67, 0, 1)
            score = (
                age_contrib * 0.20
                + smoking * 0.25
                + yellow_fingers * 0.10
                + chronic * 0.10
                + fatigue * 0.10
                + wheezing * 0.10
                + sob * 0.10
            )
            probs[i] = np.clip(score + 0.05, 0.01, 0.99)
        return np.column_stack([1.0 - probs, probs])


class StubCalibrator:
    """Stub isotonic calibrator — pass-through with mild scaling."""

    def predict(self, X):
        arr = np.asarray(X, dtype=np.float64).ravel()
        return np.clip(arr * 0.95 + 0.02, 0.0, 1.0)


class StubScaler:
    """Stub StandardScaler for Age — normalises using fixed mean=50, std=15."""

    def transform(self, X):
        arr = np.asarray(X, dtype=np.float64)
        return (arr - 50.0) / 15.0


# Feature name lists matching what the real trained .pkl files contain
HEART_FEATURES = [
    "_AGEG5YR",
    "SEX",
    "_BMI5",
    "_RFHYPE5",
    "_RFCHOL",
    "SMOKE100",
    "_TOTINDA",
    "_FRTLT1",
    "_VEGLT1",
    "_RFDRHV5",
    "GENHLTH",
    "MENTHLTH",
    "PHYSHLTH",
    "DIABETE3",
]

LUNG_FEATURES = [
    "Age",
    "Gender",
    "Smoking",
    "Yellow Fingers",
    "Chronic Disease",
    "Fatigue",
    "Wheezing",
    "Shortness of Breath",
]
