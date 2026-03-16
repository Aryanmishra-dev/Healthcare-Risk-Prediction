"""
Clinical feature mapping layer for the document AI pipeline.

Converts NLP-extracted clinical entities into the structured format
required by each ML model (diabetes, heart disease, lung cancer).
"""

from typing import Any


# ══════════════════════════════════════════════════════════════════════════
#  Age → Age Group Conversion
# ══════════════════════════════════════════════════════════════════════════

def _age_to_group(age: int | None) -> float:
    """
    Convert a raw age (years) to the BRFSS age-group code (1-13).

    Mapping:
      1 → 18-24, 2 → 25-29, 3 → 30-34, 4 → 35-39, 5 → 40-44,
      6 → 45-49, 7 → 50-54, 8 → 55-59, 9 → 60-64, 10 → 65-69,
      11 → 70-74, 12 → 75-79, 13 → 80+
    """
    if age is None:
        return 7.0  # default: 50-54
    if age < 18:
        return 1.0
    if age >= 80:
        return 13.0

    brackets = [
        (24, 1), (29, 2), (34, 3), (39, 4), (44, 5),
        (49, 6), (54, 7), (59, 8), (64, 9), (69, 10),
        (74, 11), (79, 12),
    ]
    for upper, code in brackets:
        if age <= upper:
            return float(code)
    return 13.0


def _bool_flag(value: str | None, positive: str | list[str] = "yes") -> float:
    """Convert a string value to a 0/1 float flag."""
    if value is None:
        return 0.0
    if isinstance(positive, str):
        positive = [positive]
    return 1.0 if value.lower() in [p.lower() for p in positive] else 0.0


# ══════════════════════════════════════════════════════════════════════════
#  Diabetes Feature Mapping
# ══════════════════════════════════════════════════════════════════════════

def map_to_diabetes_features(entities: dict[str, Any]) -> dict[str, Any]:
    """
    Map extracted clinical entities to diabetes model input.
    Returns None for missing properties so the frontend doesn't overwrite manual inputs.
    """
    res = {}
    if entities.get("age") is not None:
        res["age"] = _age_to_group(entities.get("age"))
    if entities.get("bmi") is not None:
        res["bmi"] = entities.get("bmi")
    if entities.get("blood_pressure") is not None:
        res["bp"] = _bool_flag(entities.get("blood_pressure"), "high")
    if entities.get("cholesterol") is not None:
        res["cholesterol"] = _bool_flag(entities.get("cholesterol"), "high")
    if entities.get("smoking") is not None:
        res["smoker"] = _bool_flag(entities.get("smoking"), "yes")
    if entities.get("physical_activity") is not None:
        res["activity"] = _bool_flag(entities.get("physical_activity"), "active")
    if entities.get("general_health") is not None:
        res["health"] = float(entities.get("general_health"))
    if entities.get("mental_health") is not None:
        res["mental"] = float(entities.get("mental_health"))
    return res


# ══════════════════════════════════════════════════════════════════════════
#  Heart Disease Feature Mapping
# ══════════════════════════════════════════════════════════════════════════

def map_to_heart_features(entities: dict[str, Any]) -> dict[str, Any]:
    """
    Map extracted clinical entities to heart disease model input.
    Returns None for missing properties so the frontend doesn't overwrite manual inputs.
    """
    res = {}
    if entities.get("age") is not None:
        res["hd_age"] = _age_to_group(entities.get("age"))
    if entities.get("gender") is not None:
        res["hd_sex"] = 1 if entities.get("gender") == "male" else 0
    if entities.get("bmi") is not None:
        res["hd_bmi"] = entities.get("bmi")
    if entities.get("blood_pressure") is not None:
        res["hd_high_bp"] = int(_bool_flag(entities.get("blood_pressure"), "high"))
    if entities.get("cholesterol") is not None:
        res["hd_high_chol"] = int(_bool_flag(entities.get("cholesterol"), "high"))
    if entities.get("smoking") is not None:
        res["hd_smoker"] = int(_bool_flag(entities.get("smoking"), "yes"))
    if entities.get("physical_activity") is not None:
        res["hd_phys_activity"] = int(_bool_flag(entities.get("physical_activity"), "active"))
    if entities.get("general_health") is not None:
        res["hd_gen_health"] = int(entities.get("general_health"))
    if entities.get("mental_health") is not None:
        res["hd_ment_health"] = int(entities.get("mental_health"))
    return res


# ══════════════════════════════════════════════════════════════════════════
#  Lung Cancer Feature Mapping
# ══════════════════════════════════════════════════════════════════════════

def map_to_lung_features(entities: dict[str, Any]) -> dict[str, Any]:
    """
    Map extracted clinical entities to lung cancer model input.
    Returns None for missing properties so the frontend doesn't overwrite manual inputs.
    """
    res = {}
    if entities.get("age") is not None:
        res["lc_age"] = entities.get("age")
    if entities.get("gender") is not None:
        res["lc_gender"] = 1 if entities.get("gender") == "male" else 0
    if entities.get("smoking") is not None:
        res["lc_smoking"] = int(_bool_flag(entities.get("smoking"), "yes"))
    return res


# ══════════════════════════════════════════════════════════════════════════
#  Convenience: Map to All Models
# ══════════════════════════════════════════════════════════════════════════

def map_to_all_models(entities: dict[str, Any]) -> dict[str, Any]:
    """
    Map extracted entities to feature dicts for all three disease models.

    Returns:
        {
            "diabetes": { ... },
            "heart": { ... },
            "lung": { ... },
        }
    """
    return {
        "diabetes": map_to_diabetes_features(entities),
        "heart": map_to_heart_features(entities),
        "lung": map_to_lung_features(entities),
    }
