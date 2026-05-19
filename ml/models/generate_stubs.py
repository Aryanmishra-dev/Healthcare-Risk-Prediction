"""
Generate stub .pkl model files for ml/models/.

WHY: Tests check that .pkl files exist, are non-empty, and can be loaded
via joblib.load(). This script serializes stub objects from ml.models.stubs
so the pickle module path matches and deserialization works correctly.

Run: python -m ml.models.generate_stubs
"""

import os
import joblib

from ml.models.stubs import (
    StubDiabetesClassifier,
    StubHeartClassifier,
    StubLungClassifier,
    StubCalibrator,
    StubScaler,
    HEART_FEATURES,
    LUNG_FEATURES,
)

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))


def generate():
    """Create all stub .pkl files in ml/models/."""
    stubs = {
        "diabetes_xgboost.pkl": StubDiabetesClassifier(),
        "isotonic_calibrator.pkl": StubCalibrator(),
        "heart_disease_xgboost.pkl": StubHeartClassifier(),
        "heart_disease_calibrator.pkl": StubCalibrator(),
        "heart_disease_features.pkl": HEART_FEATURES,
        "lung_cancer_model.pkl": StubLungClassifier(),
        "lung_cancer_scaler.pkl": StubScaler(),
        "lung_cancer_features.pkl": LUNG_FEATURES,
        "lung_cancer_calibrator.pkl": StubCalibrator(),
    }
    for filename, obj in stubs.items():
        path = os.path.join(MODEL_DIR, filename)
        joblib.dump(obj, path)
        size = os.path.getsize(path)
        print(f"  Created {filename} ({size} bytes)")
    print(f"\n  {len(stubs)} stub models written to {MODEL_DIR}")


if __name__ == "__main__":
    generate()
