"""Tests for utils/feature_engineering.py — BRFSS feature pipeline.

Covers:
  - Column selection and renaming
  - All BRFSS recoding rules (diabetes, bp, smoker, cholesterol, mental health, etc.)
  - Interaction feature generation
  - Feature vector construction
  - Multi-row batch processing
  - Edge values and constant validation
"""

import pandas as pd
import numpy as np
import pytest

from utils.feature_engineering import (
    BRFSS_COLUMNS,
    RENAME_MAP,
    FEATURE_COLS,
    select_and_rename,
    clean,
    add_interaction_features,
    build_feature_vector,
)


# ── select_and_rename ──────────────────────────────────────────────────────

class TestSelectAndRename:
    def _raw_row(self, **overrides):
        defaults = {
            "DIABETE3": 1,
            "_BMI5": 2500,
            "_AGEG5YR": 7,
            "BPHIGH4": 1,
            "SMOKE100": 2,
            "_RFCHOL": 1,
            "_TOTINDA": 1,
            "GENHLTH": 3,
            "MENTHLTH": 0,
            "EXTRA_COL": 999,
        }
        defaults.update(overrides)
        return pd.DataFrame([defaults])

    def test_selects_only_brfss_columns(self):
        df = select_and_rename(self._raw_row())
        assert "EXTRA_COL" not in df.columns
        assert len(df.columns) == len(BRFSS_COLUMNS)

    def test_renames_columns(self):
        df = select_and_rename(self._raw_row())
        expected = set(RENAME_MAP.values())
        assert set(df.columns) == expected

    def test_values_preserved(self):
        df = select_and_rename(self._raw_row(_BMI5=3200))
        assert df["bmi"].iloc[0] == 3200

    def test_multi_row_batch(self):
        rows = pd.DataFrame([
            {"DIABETE3": 1, "_BMI5": 2500, "_AGEG5YR": 7, "BPHIGH4": 1,
             "SMOKE100": 2, "_RFCHOL": 1, "_TOTINDA": 1, "GENHLTH": 3, "MENTHLTH": 0},
            {"DIABETE3": 3, "_BMI5": 3000, "_AGEG5YR": 10, "BPHIGH4": 3,
             "SMOKE100": 1, "_RFCHOL": 2, "_TOTINDA": 1, "GENHLTH": 2, "MENTHLTH": 5},
        ])
        df = select_and_rename(rows)
        assert len(df) == 2
        assert set(df.columns) == set(RENAME_MAP.values())


# ── clean ──────────────────────────────────────────────────────────────────

class TestClean:
    def _renamed_row(self, **overrides):
        defaults = {
            "diabetes": 1,
            "bmi": 2500,
            "age_group": 7,
            "high_bp": 1,
            "smoker": 1,
            "high_cholesterol": 1,
            "physical_activity": 1,
            "general_health": 3,
            "mental_health": 0,
        }
        defaults.update(overrides)
        return pd.DataFrame([defaults])

    def test_bmi_scaled(self):
        df = clean(self._renamed_row(bmi=2500))
        assert df["bmi"].iloc[0] == 25.0

    def test_diabetes_target_yes(self):
        df = clean(self._renamed_row(diabetes=1))
        assert df["diabetes"].iloc[0] == 1

    def test_diabetes_target_no(self):
        df = clean(self._renamed_row(diabetes=3))
        assert df["diabetes"].iloc[0] == 0

    def test_diabetes_pregnancy_dropped(self):
        df = clean(self._renamed_row(diabetes=2))
        assert len(df) == 0

    def test_high_bp_recoding(self):
        for raw, expected in [(1, 1), (2, 1), (3, 0), (4, 1)]:
            df = clean(self._renamed_row(high_bp=raw))
            assert df["high_bp"].iloc[0] == expected, f"BPHIGH4={raw}"

    def test_smoker_recoding(self):
        df_yes = clean(self._renamed_row(smoker=1))
        df_no = clean(self._renamed_row(smoker=2))
        assert df_yes["smoker"].iloc[0] == 1
        assert df_no["smoker"].iloc[0] == 0

    def test_cholesterol_inverted(self):
        df_no = clean(self._renamed_row(high_cholesterol=1))
        df_yes = clean(self._renamed_row(high_cholesterol=2))
        assert df_no["high_cholesterol"].iloc[0] == 0
        assert df_yes["high_cholesterol"].iloc[0] == 1

    def test_mental_health_88_becomes_zero(self):
        df = clean(self._renamed_row(mental_health=88))
        assert df["mental_health"].iloc[0] == 0

    def test_gen_health_missing_codes_dropped(self):
        for code in [7, 9]:
            df = clean(self._renamed_row(general_health=code))
            assert len(df) == 0, f"GENHLTH={code} should result in drop"

    def test_age_14_dropped(self):
        df = clean(self._renamed_row(age_group=14))
        assert len(df) == 0

    def test_multi_row_clean(self):
        rows = pd.DataFrame([
            {"diabetes": 1, "bmi": 2500, "age_group": 7, "high_bp": 1,
             "smoker": 1, "high_cholesterol": 1, "physical_activity": 1,
             "general_health": 3, "mental_health": 0},
            {"diabetes": 3, "bmi": 3000, "age_group": 10, "high_bp": 3,
             "smoker": 2, "high_cholesterol": 2, "physical_activity": 1,
             "general_health": 2, "mental_health": 88},
            {"diabetes": 2, "bmi": 2200, "age_group": 5, "high_bp": 1,
             "smoker": 1, "high_cholesterol": 1, "physical_activity": 1,
             "general_health": 3, "mental_health": 10},  # pregnancy → drop
        ])
        df = clean(rows)
        assert len(df) == 2  # 3rd row dropped (diabetes=2)
        assert df.iloc[0]["bmi"] == 25.0
        assert df.iloc[1]["bmi"] == 30.0
        assert df.iloc[1]["mental_health"] == 0  # 88 → 0

    def test_extreme_bmi_value(self):
        df = clean(self._renamed_row(bmi=9999))
        assert df["bmi"].iloc[0] == pytest.approx(99.99)


# ── add_interaction_features ───────────────────────────────────────────────

class TestInteractionFeatures:
    def test_creates_five_columns(self):
        df = pd.DataFrame([{
            "bmi": 25.0, "age_group": 7, "high_bp": 1,
            "high_cholesterol": 1, "general_health": 3,
        }])
        result = add_interaction_features(df)
        for col in ["bmi_age", "bmi_bp", "age_bp", "chol_bmi", "health_bmi"]:
            assert col in result.columns

    def test_interaction_values(self):
        df = pd.DataFrame([{
            "bmi": 30.0, "age_group": 10, "high_bp": 1,
            "high_cholesterol": 0, "general_health": 4,
        }])
        result = add_interaction_features(df)
        assert result["bmi_age"].iloc[0] == 300.0
        assert result["bmi_bp"].iloc[0] == 30.0
        assert result["age_bp"].iloc[0] == 10.0
        assert result["chol_bmi"].iloc[0] == 0.0
        assert result["health_bmi"].iloc[0] == 120.0

    def test_does_not_mutate_input(self):
        df = pd.DataFrame([{
            "bmi": 25.0, "age_group": 7, "high_bp": 1,
            "high_cholesterol": 1, "general_health": 3,
        }])
        original_cols = list(df.columns)
        add_interaction_features(df)
        assert list(df.columns) == original_cols

    def test_zero_interactions(self):
        df = pd.DataFrame([{
            "bmi": 0.0, "age_group": 0, "high_bp": 0,
            "high_cholesterol": 0, "general_health": 0,
        }])
        result = add_interaction_features(df)
        for col in ["bmi_age", "bmi_bp", "age_bp", "chol_bmi", "health_bmi"]:
            assert result[col].iloc[0] == 0.0


# ── build_feature_vector ───────────────────────────────────────────────────

class TestBuildFeatureVector:
    def test_returns_dataframe_with_13_columns(self):
        df = build_feature_vector(
            age_group=7, bmi=25.0, high_bp=1, smoker=0,
            high_cholesterol=1, physical_activity=1,
            general_health=3, mental_health=5,
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert len(df.columns) == 13

    def test_interaction_terms_present(self):
        df = build_feature_vector(
            age_group=7, bmi=25.0, high_bp=1, smoker=0,
            high_cholesterol=1, physical_activity=1,
            general_health=3, mental_health=5,
        )
        for col in ["bmi_age", "bmi_bp", "age_bp", "chol_bmi", "health_bmi"]:
            assert col in df.columns

    def test_correct_interaction_values(self):
        df = build_feature_vector(
            age_group=10, bmi=30.0, high_bp=0, smoker=1,
            high_cholesterol=1, physical_activity=0,
            general_health=5, mental_health=10,
        )
        assert df["bmi_age"].iloc[0] == 300.0
        assert df["bmi_bp"].iloc[0] == 0.0
        assert df["chol_bmi"].iloc[0] == 30.0

    def test_dtype_is_float64(self):
        df = build_feature_vector(
            age_group=7, bmi=25.0, high_bp=1, smoker=0,
            high_cholesterol=1, physical_activity=1,
            general_health=3, mental_health=5,
        )
        assert all(df.dtypes == np.float64)

    def test_columns_match_feature_cols(self):
        df = build_feature_vector(
            age_group=7, bmi=25.0, high_bp=1, smoker=0,
            high_cholesterol=1, physical_activity=1,
            general_health=3, mental_health=5,
        )
        assert list(df.columns) == FEATURE_COLS


# ── Constants Validation ──────────────────────────────────────────────────

class TestConstants:
    def test_brfss_columns_count(self):
        assert len(BRFSS_COLUMNS) == 9

    def test_rename_map_matches_brfss_columns(self):
        assert set(RENAME_MAP.keys()) == set(BRFSS_COLUMNS)

    def test_feature_cols_count(self):
        assert len(FEATURE_COLS) == 13

    def test_feature_cols_include_interactions(self):
        for col in ["bmi_age", "bmi_bp", "age_bp", "chol_bmi", "health_bmi"]:
            assert col in FEATURE_COLS
