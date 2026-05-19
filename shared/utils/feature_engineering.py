"""
Feature engineering utilities for the BRFSS diabetes risk model.

Centralises all column selection, renaming, cleaning, and interaction-term
creation so the same transformations can be applied in both the training
notebook and the production inference path.
"""

import pandas as pd
import numpy as np

# ── Raw BRFSS columns we use ───────────────────────────────────────────────
BRFSS_COLUMNS = [
    "DIABETE3",
    "_BMI5",
    "_AGEG5YR",
    "BPHIGH4",
    "SMOKE100",
    "_RFCHOL",
    "_TOTINDA",
    "GENHLTH",
    "MENTHLTH",
]

RENAME_MAP = {
    "DIABETE3": "diabetes",
    "_BMI5": "bmi",
    "_AGEG5YR": "age_group",
    "BPHIGH4": "high_bp",
    "SMOKE100": "smoker",
    "_RFCHOL": "high_cholesterol",
    "_TOTINDA": "physical_activity",
    "GENHLTH": "general_health",
    "MENTHLTH": "mental_health",
}

FEATURE_COLS = [
    "bmi", "age_group", "high_bp", "smoker", "high_cholesterol",
    "physical_activity", "general_health", "mental_health",
    "bmi_age", "bmi_bp", "age_bp", "chol_bmi", "health_bmi",
]


def select_and_rename(df: pd.DataFrame) -> pd.DataFrame:
    """Select the BRFSS columns we need and rename to friendly names."""
    return df[BRFSS_COLUMNS].rename(columns=RENAME_MAP)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standard BRFSS cleaning pipeline:
      1. Scale BMI (raw value is ×100).
      2. Keep diabetes=1 (yes) and diabetes=3 (no) per BRFSS 2015 coding.
         DIABETE3: 1=Yes, 2=Yes(pregnancy only), 3=No, 4=No(borderline).
      3. Recode binary/categorical features to clean 0/1 values.
      4. Handle missing-value codes per column (not blanket replacement).
    """
    df = df.copy()

    # ── BMI: raw value is ×100 ────────────────────────────────────────────
    df["bmi"] = df["bmi"] / 100

    # ── Diabetes target: keep Yes (1) and No (3), drop pregnancy (2) ──────
    df = df[df["diabetes"].isin([1, 3])]
    df["diabetes"] = df["diabetes"].replace({1: 1, 3: 0})

    # ── Recode categoricals to clean binary (0/1) ────────────────────────
    # BPHIGH4: 1=Yes, 2=Yes(preg), 3=No, 4=Borderline → 1=Yes/Borderline, 0=No
    df["high_bp"] = df["high_bp"].map({1: 1, 2: 1, 3: 0, 4: 1})

    # SMOKE100: 1=Yes, 2=No → 1/0
    df["smoker"] = df["smoker"].map({1: 1, 2: 0})

    # _RFCHOL: 1=No risk, 2=Yes high cholesterol → 0/1
    df["high_cholesterol"] = df["high_cholesterol"].map({1: 0, 2: 1})

    # _TOTINDA: 1=Active, 2=Inactive → 1/0
    df["physical_activity"] = df["physical_activity"].map({1: 1, 2: 0})

    # MENTHLTH: 1-30 days, 88=None → recode 88 to 0
    df["mental_health"] = df["mental_health"].replace(88, 0)

    # GENHLTH: 1=Excellent … 5=Poor — keep as ordinal (7/9 are missing)
    df["general_health"] = df["general_health"].replace([7, 9], pd.NA)

    # _AGEG5YR: 1-13 valid, 14=Don't know → drop 14
    df["age_group"] = df["age_group"].replace(14, pd.NA)

    # Drop rows with any remaining NA
    df = df.dropna()

    return df


def add_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create the five interaction terms used by the model."""
    df = df.copy()
    df["bmi_age"]    = df["bmi"] * df["age_group"]
    df["bmi_bp"]     = df["bmi"] * df["high_bp"]
    df["age_bp"]     = df["age_group"] * df["high_bp"]
    df["chol_bmi"]   = df["high_cholesterol"] * df["bmi"]
    df["health_bmi"] = df["general_health"] * df["bmi"]
    return df


def build_feature_vector(
    age_group: float,
    bmi: float,
    high_bp: float,
    smoker: float,
    high_cholesterol: float,
    physical_activity: float,
    general_health: float,
    mental_health: float,
) -> pd.DataFrame:
    """
    Build a single-row DataFrame with all 13 features from raw clinical inputs.
    Used at inference time (risk calculator / API).

    Expected encoding (clean 0/1, matching the retrained model):
        age_group:         1-13  (1=18-24 … 13=80+)
        bmi:               continuous (e.g. 27.5)
        high_bp:           1=Yes, 0=No
        smoker:            1=Yes, 0=No
        high_cholesterol:  1=Yes, 0=No
        physical_activity: 1=Active, 0=Inactive
        general_health:    1=Excellent … 5=Poor
        mental_health:     0-30 (days of poor mental health; 0=none)
    """
    features = {
        "bmi":               bmi,
        "age_group":         age_group,
        "high_bp":           high_bp,
        "smoker":            smoker,
        "high_cholesterol":  high_cholesterol,
        "physical_activity": physical_activity,
        "general_health":    general_health,
        "mental_health":     mental_health,
        "bmi_age":           bmi * age_group,
        "bmi_bp":            bmi * high_bp,
        "age_bp":            age_group * high_bp,
        "chol_bmi":          high_cholesterol * bmi,
        "health_bmi":        general_health * bmi,
    }
    return pd.DataFrame([features]).astype(np.float64)
