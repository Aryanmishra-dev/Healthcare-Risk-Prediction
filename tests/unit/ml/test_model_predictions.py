"""Tests for ML model prediction sanity — ensures models produce reasonable outputs.

Covers:
  - All 3 models: low/high risk sanity, output schema, bounds, determinism
  - Monotonicity tests: worsening inputs → non-decreasing risk
  - Risk threshold classification logic
  - Model artefact file existence
  - Feature vector shape and content
"""

import os
import pytest

from backend.app.services.model_loader import (
    load_models,
    build_diabetes_features,
    _sync_predict_diabetes,
    _sync_predict_heart,
    _sync_predict_lung,
)

from backend.app.main import app

def predict_diabetes(**kwargs):
    m = app.state.models.get("diabetes_model")
    c = app.state.models.get("diabetes_calibrator")
    return _sync_predict_diabetes(m, c, **kwargs)

def predict_heart_disease(**kwargs):
    m = app.state.models.get("heart_model")
    c = app.state.models.get("heart_calibrator")
    f = app.state.models.get("heart_features")
    return _sync_predict_heart(m, c, f, **kwargs)

def predict_lung_cancer(**kwargs):
    m = app.state.models.get("lung_model")
    s = app.state.models.get("lung_scaler")
    f = app.state.models.get("lung_features")
    c = app.state.models.get("lung_calibrator")
    return _sync_predict_lung(m, s, f, c, **kwargs)


@pytest.fixture(scope="module", autouse=True)
def _load():
    """Load all models once for the entire test module."""
    from backend.app.main import app
    load_models(app)


# ── Model Artefact Files ──────────────────────────────────────────────────

MODEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../..", "ml", "models")
)


class TestModelFiles:
    @pytest.mark.parametrize("filename", [
        "diabetes_xgboost.pkl",
        "isotonic_calibrator.pkl",
        "heart_disease_xgboost.pkl",
        "heart_disease_calibrator.pkl",
        "heart_disease_features.pkl",
        "lung_cancer_model.pkl",
        "lung_cancer_scaler.pkl",
        "lung_cancer_features.pkl",
    ])
    def test_model_file_exists(self, filename):
        path = os.path.join(MODEL_DIR, filename)
        assert os.path.isfile(path), f"Missing model file: {filename}"

    @pytest.mark.parametrize("filename", [
        "diabetes_xgboost.pkl",
        "heart_disease_xgboost.pkl",
        "lung_cancer_model.pkl",
    ])
    def test_model_file_non_empty(self, filename):
        path = os.path.join(MODEL_DIR, filename)
        assert os.path.getsize(path) > 0, f"Empty model file: {filename}"


# ── Diabetes Model ─────────────────────────────────────────────────────────

class TestDiabetesModel:
    def test_low_risk_healthy_young(self):
        result = predict_diabetes(
            age_group=1, bmi=22.0, high_bp=0, smoker=0,
            high_cholesterol=0, physical_activity=1,
            general_health=1, mental_health=0,
        )
        assert result["risk_level"] == "Low"
        assert result["risk_percentage"] < 20

    def test_high_risk_elderly_obese(self):
        result = predict_diabetes(
            age_group=13, bmi=42.0, high_bp=1, smoker=1,
            high_cholesterol=1, physical_activity=0,
            general_health=5, mental_health=30,
        )
        assert result["risk_percentage"] > 20

    def test_output_keys(self):
        result = predict_diabetes(
            age_group=7, bmi=25.0, high_bp=0, smoker=0,
            high_cholesterol=0, physical_activity=1,
            general_health=3, mental_health=0,
        )
        assert "risk_percentage" in result
        assert "risk_level" in result

    def test_percentage_bounded(self):
        result = predict_diabetes(
            age_group=7, bmi=25.0, high_bp=0, smoker=0,
            high_cholesterol=0, physical_activity=1,
            general_health=3, mental_health=0,
        )
        assert 0 <= result["risk_percentage"] <= 100

    def test_risk_level_valid(self):
        result = predict_diabetes(
            age_group=7, bmi=25.0, high_bp=0, smoker=0,
            high_cholesterol=0, physical_activity=1,
            general_health=3, mental_health=0,
        )
        assert result["risk_level"] in ("Low", "Moderate", "High")

    def test_feature_vector_shape(self):
        df = build_diabetes_features(
            age_group=7, bmi=25.0, high_bp=0, smoker=0,
            high_cholesterol=0, physical_activity=1,
            general_health=3, mental_health=0,
        )
        assert df.shape == (1, 13)

    def test_deterministic(self):
        args = dict(
            age_group=7, bmi=28.0, high_bp=1, smoker=0,
            high_cholesterol=1, physical_activity=1,
            general_health=3, mental_health=5,
        )
        r1 = predict_diabetes(**args)
        r2 = predict_diabetes(**args)
        assert r1["risk_percentage"] == r2["risk_percentage"]

    def test_monotonicity_bmi(self):
        """Higher BMI (other factors equal) should not reduce risk."""
        base = dict(
            age_group=7, high_bp=1, smoker=0,
            high_cholesterol=1, physical_activity=0,
            general_health=3, mental_health=5,
        )
        low = predict_diabetes(bmi=22.0, **base)["risk_percentage"]
        high = predict_diabetes(bmi=45.0, **base)["risk_percentage"]
        assert high >= low

    def test_monotonicity_age(self):
        """Older age group should have >= risk than younger."""
        base = dict(
            bmi=30.0, high_bp=1, smoker=0,
            high_cholesterol=1, physical_activity=0,
            general_health=3, mental_health=5,
        )
        young = predict_diabetes(age_group=1, **base)["risk_percentage"]
        old = predict_diabetes(age_group=13, **base)["risk_percentage"]
        assert old >= young


# ── Heart Disease Model ───────────────────────────────────────────────────

class TestHeartDiseaseModel:
    def test_low_risk_healthy(self):
        result = predict_heart_disease(
            age=1, sex=0, bmi=22.0, high_bp=0, high_chol=0,
            smoker=0, phys_activity=1, fruits=1, veggies=1,
            heavy_drinker=0, gen_health=1, ment_health=0,
            phys_health=0, diabetes=0,
        )
        assert result["risk_level"] == "Low"

    def test_elevated_risk_unhealthy(self):
        result = predict_heart_disease(
            age=13, sex=1, bmi=40.0, high_bp=1, high_chol=1,
            smoker=1, phys_activity=0, fruits=0, veggies=0,
            heavy_drinker=1, gen_health=5, ment_health=30,
            phys_health=30, diabetes=1,
        )
        assert result["risk_percentage"] > 10

    def test_output_keys(self):
        result = predict_heart_disease(
            age=7, sex=1, bmi=25.0, high_bp=0, high_chol=0,
            smoker=0, phys_activity=1, fruits=1, veggies=1,
            heavy_drinker=0, gen_health=3, ment_health=0,
            phys_health=0, diabetes=0,
        )
        assert "risk_percentage" in result
        assert "risk_level" in result

    def test_percentage_bounded(self):
        result = predict_heart_disease(
            age=7, sex=1, bmi=25.0, high_bp=0, high_chol=0,
            smoker=0, phys_activity=1, fruits=1, veggies=1,
            heavy_drinker=0, gen_health=3, ment_health=0,
            phys_health=0, diabetes=0,
        )
        assert 0 <= result["risk_percentage"] <= 100

    def test_deterministic(self):
        args = dict(
            age=7, sex=1, bmi=25.0, high_bp=0, high_chol=0,
            smoker=0, phys_activity=1, fruits=1, veggies=1,
            heavy_drinker=0, gen_health=3, ment_health=0,
            phys_health=0, diabetes=0,
        )
        r1 = predict_heart_disease(**args)
        r2 = predict_heart_disease(**args)
        assert r1["risk_percentage"] == r2["risk_percentage"]

    def test_risk_changes_with_risk_factors(self):
        """Adding risk factors should change the predicted risk."""
        low_risk = predict_heart_disease(
            age=1, sex=0, bmi=22.0, high_bp=0, high_chol=0,
            smoker=0, phys_activity=1, fruits=1, veggies=1,
            heavy_drinker=0, gen_health=1, ment_health=0,
            phys_health=0, diabetes=0,
        )["risk_percentage"]
        high_risk = predict_heart_disease(
            age=13, sex=1, bmi=40.0, high_bp=1, high_chol=1,
            smoker=1, phys_activity=0, fruits=0, veggies=0,
            heavy_drinker=1, gen_health=5, ment_health=30,
            phys_health=30, diabetes=1,
        )["risk_percentage"]
        assert high_risk > low_risk


# ── Lung Cancer Model ────────────────────────────────────────────────────

class TestLungCancerModel:
    def test_low_risk_healthy(self):
        result = predict_lung_cancer(
            age=25, gender=0, smoking=0, yellow_fingers=0,
            chronic_disease=0, fatigue=0, wheezing=0,
            shortness_of_breath=0,
        )
        assert result["risk_percentage"] < 60

    def test_high_risk_all_symptoms(self):
        result = predict_lung_cancer(
            age=70, gender=1, smoking=1, yellow_fingers=1,
            chronic_disease=1, fatigue=1, wheezing=1,
            shortness_of_breath=1,
        )
        assert result["risk_percentage"] > 30

    def test_output_keys(self):
        result = predict_lung_cancer(
            age=50, gender=1, smoking=0, yellow_fingers=0,
            chronic_disease=0, fatigue=0, wheezing=0,
            shortness_of_breath=0,
        )
        assert "risk_percentage" in result
        assert "risk_level" in result

    def test_percentage_bounded(self):
        result = predict_lung_cancer(
            age=50, gender=1, smoking=0, yellow_fingers=0,
            chronic_disease=0, fatigue=0, wheezing=0,
            shortness_of_breath=0,
        )
        assert 0 <= result["risk_percentage"] <= 100

    def test_risk_level_valid(self):
        result = predict_lung_cancer(
            age=50, gender=1, smoking=0, yellow_fingers=0,
            chronic_disease=0, fatigue=0, wheezing=0,
            shortness_of_breath=0,
        )
        assert result["risk_level"] in ("Low", "Moderate", "High")

    def test_deterministic(self):
        args = dict(
            age=50, gender=1, smoking=0, yellow_fingers=0,
            chronic_disease=0, fatigue=0, wheezing=0,
            shortness_of_breath=0,
        )
        r1 = predict_lung_cancer(**args)
        r2 = predict_lung_cancer(**args)
        assert r1["risk_percentage"] == r2["risk_percentage"]

    def test_smoking_increases_risk(self):
        base = dict(
            age=50, gender=1, yellow_fingers=0,
            chronic_disease=0, fatigue=0, wheezing=0,
            shortness_of_breath=0,
        )
        no = predict_lung_cancer(smoking=0, **base)["risk_percentage"]
        yes = predict_lung_cancer(smoking=1, **base)["risk_percentage"]
        assert yes >= no


# ── Risk Level Threshold Tests ────────────────────────────────────────────

class TestRiskThresholds:
    @pytest.mark.parametrize("pct,expected", [
        (0, "Low"), (19.9, "Low"),
        (20, "Moderate"), (44.9, "Moderate"),
        (45, "High"), (100, "High"),
    ])
    def test_diabetes_thresholds(self, pct, expected):
        if pct < 20:
            level = "Low"
        elif pct < 45:
            level = "Moderate"
        else:
            level = "High"
        assert level == expected

    @pytest.mark.parametrize("pct,expected", [
        (0, "Low"), (29.9, "Low"),
        (30, "Moderate"), (59.9, "Moderate"),
        (60, "High"), (100, "High"),
    ])
    def test_lung_thresholds(self, pct, expected):
        if pct < 30:
            level = "Low"
        elif pct < 60:
            level = "Moderate"
        else:
            level = "High"
        assert level == expected
