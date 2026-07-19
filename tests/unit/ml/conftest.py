"""
Stub model fixtures for unit tests — loaded when real .pkl weights are absent.

WHY: The ml/models/ directory may not have trained weights (.pkl files).
     load_models() catches the FileNotFoundError and sets all model slots to None,
     causing every prediction helper to fail with KeyError: None.
     These stubs implement the exact sklearn/xgboost interface (predict_proba,
     predict, transform) so prediction functions produce schema-valid dicts
     without needing real weights on disk.
"""

import pytest

from backend.app.main import app
from ml.models.stubs import (
    HEART_FEATURES,
    LUNG_FEATURES,
    StubCalibrator,
    StubDiabetesClassifier,
    StubHeartClassifier,
    StubLungClassifier,
    StubScaler,
)

# ── Fixture: inject stubs into app.state.models before tests run ──────────


@pytest.fixture(scope="module", autouse=True)
def _load_stub_models():
    """Replace real model loading with deterministic stubs.

    WHY: Runs before the module-level _load() fixture in
    test_model_predictions.py. Populates app.state.models with stubs
    so load_models() sees them already loaded and skips disk access.
    """
    app.state.models = {
        # Diabetes
        "diabetes_model": StubDiabetesClassifier(),
        "diabetes_calibrator": StubCalibrator(),
        # Heart disease
        "heart_model": StubHeartClassifier(),
        "heart_calibrator": StubCalibrator(),
        "heart_features": HEART_FEATURES,
        # Lung cancer
        "lung_model": StubLungClassifier(),
        "lung_scaler": StubScaler(),
        "lung_features": LUNG_FEATURES,
        "lung_calibrator": StubCalibrator(),
    }
    yield
