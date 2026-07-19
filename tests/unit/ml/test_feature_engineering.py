import numpy as np
import pandas as pd
import pytest

from ml.feature_engineering.feature_store import FeatureStore
from shared.utils.feature_engineering import (
    add_interaction_features,
    clean,
    select_and_rename,
)


@pytest.fixture
def sample_brfss_data():
    """Create a minimal mock DataFrame resembling raw BRFSS data."""
    data = {
        "DIABETE3": [1, 3, 4],  # 1=Yes, 3=No, 4=Pre-diabetes
        "_AGEG5YR": [7, 8, 9],
        "_BMI5": [2500, 3000, 2200],  # BMI * 100
        "BPHIGH4": [1, 3, 1],  # 1=Yes, 3=No
        "_RFCHOL": [1, 2, 1],  # 1=No risk, 2=High chol
        "SMOKE100": [1, 2, 1],  # 1=Yes, 2=No
        "_TOTINDA": [1, 2, 1],  # 1=Had activity, 2=No activity
        "GENHLTH": [3, 4, 1],
        "MENTHLTH": [0, 5, 88],  # 88 means 0 days
    }
    return pd.DataFrame(data)


def test_setup_brfss_features(sample_brfss_data):
    """Test standard feature extraction and recoding of BRFSS data."""
    df_selected = select_and_rename(sample_brfss_data)
    df_clean = clean(df_selected)

    # Check shape (row with DIABETE3=4 is dropped)
    assert len(df_clean) == 2

    # Check DIABETE3 target recoding (1=1, 3=0)
    assert df_clean["diabetes"].tolist() == [1, 0]

    # Check BMI scaling (divided by 100)
    assert df_clean["bmi"].tolist() == [25.0, 30.0]

    # Check high_bp (1=1, 3=0)
    assert df_clean["high_bp"].tolist() == [1, 0]

    # Check SMOKE100 recoding (1=1, 2=0)
    assert df_clean["smoker"].tolist() == [1, 0]

    # Check generic 88->0 recoding for mental health
    assert df_clean["mental_health"].tolist() == [0, 5]


def test_add_interaction_features(sample_brfss_data):
    """Test that interaction features are correctly calculated."""
    df_selected = select_and_rename(sample_brfss_data)
    df_clean = clean(df_selected)
    df_with_interactions = add_interaction_features(df_clean)

    # Check that new columns exist
    expected_cols = ["bmi_age", "bmi_bp", "age_bp", "chol_bmi", "health_bmi"]
    for col in expected_cols:
        assert col in df_with_interactions.columns

    # Spot check one calculation: bmi_age = bmi * age_group
    assert df_with_interactions["bmi_age"].iloc[0] == 25.0 * 7


class TestFeatureStore:
    def test_feature_store_pipeline(self):
        """Test the Feature Store compute and validate pipeline."""
        store = FeatureStore()

        raw_inputs = {
            "bmi": 25.0,
            "age_group": 7,
            "high_bp": 0,
            "smoker": 0,
            "high_cholesterol": 0,
            "physical_activity": 1,
            "general_health": 3,
            "mental_health": 0,
        }

        # Test compute
        df = store.compute_diabetes(raw_inputs)
        assert "bmi_age" in df.columns
        assert len(df) == 1

        # Test validation (should pass with no errors)
        errors = store.validate("diabetes", df)
        assert len(errors) == 0

        # Test validation with a missing column
        df_bad = df.drop(columns=["age_group"])
        errors_bad = store.validate("diabetes", df_bad)
        assert len(errors_bad) > 0
        assert "Missing columns" in errors_bad[0]

        # Test validation with out-of-bounds data
        df_out = df.copy()
        df_out["bmi"] = 90.0  # Above max 80.0
        errors_out = store.validate("diabetes", df_out)
        assert len(errors_out) > 0
        assert "bmi" in errors_out[0]
        assert "above maximum" in errors_out[0]
