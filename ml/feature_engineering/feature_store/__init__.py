"""
Feature store — centralized feature definitions, transformations, and validation.

Provides a single source of truth for feature schemas so training and serving
pipelines stay consistent.

Usage:
    from ml.feature_engineering.feature_store import FeatureStore

    store = FeatureStore()
    df = store.compute("diabetes", raw_inputs)
    store.validate("diabetes", df)
"""

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeatureSpec:
    """Specification for a single feature."""

    name: str
    dtype: str  # "float64", "int64"
    min_val: float | None = None
    max_val: float | None = None
    description: str = ""


# ── Feature definitions per model ─────────────────────────────────────────

DIABETES_FEATURES: list[FeatureSpec] = [
    FeatureSpec("bmi", "float64", 10.0, 80.0, "Body Mass Index"),
    FeatureSpec("age_group", "float64", 1.0, 13.0, "BRFSS age group (1-13)"),
    FeatureSpec("high_bp", "float64", 0.0, 1.0, "High blood pressure (0/1)"),
    FeatureSpec(
        "smoker", "float64", 0.0, 1.0, "Has smoked 100+ cigarettes (0/1)"
    ),
    FeatureSpec(
        "high_cholesterol", "float64", 0.0, 1.0, "High cholesterol (0/1)"
    ),
    FeatureSpec(
        "physical_activity",
        "float64",
        0.0,
        1.0,
        "Physical activity in past 30d (0/1)",
    ),
    FeatureSpec(
        "general_health",
        "float64",
        1.0,
        5.0,
        "Self-rated health (1=Excellent..5=Poor)",
    ),
    FeatureSpec(
        "mental_health",
        "float64",
        0.0,
        30.0,
        "Days of poor mental health (0-30)",
    ),
    # Interaction features
    FeatureSpec("bmi_age", "float64", description="BMI × age_group"),
    FeatureSpec("bmi_bp", "float64", description="BMI × high_bp"),
    FeatureSpec("age_bp", "float64", description="age_group × high_bp"),
    FeatureSpec("chol_bmi", "float64", description="high_cholesterol × BMI"),
    FeatureSpec("health_bmi", "float64", description="general_health × BMI"),
]

HEART_FEATURES: list[FeatureSpec] = [
    FeatureSpec("_AGEG5YR", "float64", 1.0, 13.0, "Age group"),
    FeatureSpec("SEX", "float64", 0.0, 1.0, "Sex (0=female, 1=male)"),
    FeatureSpec("_BMI5", "float64", 10.0, 80.0, "BMI"),
    FeatureSpec(
        "_RFHYPE5", "float64", 0.0, 1.0, "No high BP risk (BRFSS coded)"
    ),
    FeatureSpec(
        "_RFCHOL",
        "float64",
        0.0,
        1.0,
        "No high cholesterol risk (BRFSS coded)",
    ),
    FeatureSpec("SMOKE100", "float64", 0.0, 1.0, "Smoked 100+ cigarettes"),
    FeatureSpec("_TOTINDA", "float64", 0.0, 1.0, "Physical activity"),
    FeatureSpec("_FRTLT1", "float64", 0.0, 1.0, "Fruit consumption"),
    FeatureSpec("_VEGLT1", "float64", 0.0, 1.0, "Vegetable consumption"),
    FeatureSpec(
        "_RFDRHV5", "float64", 0.0, 1.0, "No heavy drinking (BRFSS coded)"
    ),
    FeatureSpec("GENHLTH", "float64", 1.0, 5.0, "General health"),
    FeatureSpec("MENTHLTH", "float64", 0.0, 30.0, "Mental health days"),
    FeatureSpec("PHYSHLTH", "float64", 0.0, 30.0, "Physical health days"),
    FeatureSpec("DIABETE3", "float64", 0.0, 1.0, "Has diabetes"),
]

LUNG_FEATURES: list[FeatureSpec] = [
    FeatureSpec("Age", "float64", 18.0, 100.0, "Patient age"),
    FeatureSpec("Gender", "float64", 0.0, 1.0, "Gender (0=F, 1=M)"),
    FeatureSpec("Smoking", "float64", 0.0, 1.0, "Current smoker"),
    FeatureSpec("Yellow Fingers", "float64", 0.0, 1.0, "Yellow fingers"),
    FeatureSpec("Chronic Disease", "float64", 0.0, 1.0, "Has chronic disease"),
    FeatureSpec("Fatigue", "float64", 0.0, 1.0, "Fatigue"),
    FeatureSpec("Wheezing", "float64", 0.0, 1.0, "Wheezing"),
    FeatureSpec(
        "Shortness of Breath", "float64", 0.0, 1.0, "Shortness of breath"
    ),
]

_FEATURE_REGISTRY: dict[str, list[FeatureSpec]] = {
    "diabetes": DIABETES_FEATURES,
    "heart": HEART_FEATURES,
    "lung": LUNG_FEATURES,
}


class FeatureStore:
    """Centralized feature registry, transformation, and validation."""

    def get_specs(self, model_name: str) -> list[FeatureSpec]:
        """Return the feature specifications for a model."""
        if model_name not in _FEATURE_REGISTRY:
            raise KeyError(f"Unknown model: {model_name}")
        return _FEATURE_REGISTRY[model_name]

    def get_feature_names(self, model_name: str) -> list[str]:
        """Return ordered list of feature names for a model."""
        return [f.name for f in self.get_specs(model_name)]

    def validate(self, model_name: str, df: pd.DataFrame) -> list[str]:
        """
        Validate a DataFrame against the feature schema.

        Returns a list of validation error messages (empty if valid).
        """
        specs = self.get_specs(model_name)
        errors: list[str] = []

        expected_cols = {s.name for s in specs}
        actual_cols = set(df.columns)
        missing = expected_cols - actual_cols
        if missing:
            errors.append(f"Missing columns: {missing}")

        for spec in specs:
            if spec.name not in df.columns:
                continue
            col = df[spec.name]
            if spec.min_val is not None and (col < spec.min_val).any():
                errors.append(
                    f"{spec.name}: values below minimum {spec.min_val}"
                )
            if spec.max_val is not None and (col > spec.max_val).any():
                errors.append(
                    f"{spec.name}: values above maximum {spec.max_val}"
                )

        return errors

    def compute_diabetes(self, raw: dict[str, Any]) -> pd.DataFrame:
        """Build the full 13-feature diabetes DataFrame from raw inputs."""
        bmi = float(raw["bmi"])
        age = float(raw["age_group"])
        bp = float(raw["high_bp"])
        chol = float(raw["high_cholesterol"])
        gh = float(raw["general_health"])
        features = {
            "bmi": bmi,
            "age_group": age,
            "high_bp": bp,
            "smoker": float(raw["smoker"]),
            "high_cholesterol": chol,
            "physical_activity": float(raw["physical_activity"]),
            "general_health": gh,
            "mental_health": float(raw["mental_health"]),
            "bmi_age": bmi * age,
            "bmi_bp": bmi * bp,
            "age_bp": age * bp,
            "chol_bmi": chol * bmi,
            "health_bmi": gh * bmi,
        }
        return pd.DataFrame([features]).astype(np.float64)
