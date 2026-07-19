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
        (24, 1),
        (29, 2),
        (34, 3),
        (39, 4),
        (44, 5),
        (49, 6),
        (54, 7),
        (59, 8),
        (64, 9),
        (69, 10),
        (74, 11),
        (79, 12),
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


def _map_field(entities, key, mapper=lambda x: x):
    if key in entities and entities[key] is not None:
        val = mapper(entities[key]["value"])
        return {"value": val, "confidence": entities[key]["confidence"]}
    return None


# ══════════════════════════════════════════════════════════════════════════
#  Diabetes Feature Mapping
# ══════════════════════════════════════════════════════════════════════════


def map_to_diabetes_features(entities: dict[str, Any]) -> dict[str, Any]:
    """
    Map extracted clinical entities to diabetes model input.
    """
    res = {}
    res["age"] = _map_field(entities, "age", _age_to_group)
    res["bmi"] = _map_field(entities, "bmi")
    res["bp"] = _map_field(
        entities, "blood_pressure", lambda x: _bool_flag(x, "high")
    )
    res["cholesterol"] = _map_field(
        entities, "cholesterol", lambda x: _bool_flag(x, "high")
    )
    res["smoker"] = _map_field(
        entities, "smoking", lambda x: _bool_flag(x, "yes")
    )
    res["activity"] = _map_field(
        entities, "physical_activity", lambda x: _bool_flag(x, "active")
    )
    res["health"] = _map_field(entities, "general_health", float)
    res["mental"] = _map_field(entities, "mental_health", float)

    # Remove Nones so frontend handles them
    return {k: v for k, v in res.items() if v is not None}


# ══════════════════════════════════════════════════════════════════════════
#  Heart Disease Feature Mapping
# ══════════════════════════════════════════════════════════════════════════


def map_to_heart_features(entities: dict[str, Any]) -> dict[str, Any]:
    """
    Map extracted clinical entities to heart disease model input.
    """
    res = {}
    res["hd_age"] = _map_field(entities, "age", _age_to_group)
    res["hd_sex"] = _map_field(
        entities, "gender", lambda x: 1 if x == "male" else 0
    )
    res["hd_bmi"] = _map_field(entities, "bmi")
    res["hd_high_bp"] = _map_field(
        entities, "blood_pressure", lambda x: int(_bool_flag(x, "high"))
    )
    res["hd_high_chol"] = _map_field(
        entities, "cholesterol", lambda x: int(_bool_flag(x, "high"))
    )
    res["hd_smoker"] = _map_field(
        entities, "smoking", lambda x: int(_bool_flag(x, "yes"))
    )
    res["hd_phys_activity"] = _map_field(
        entities, "physical_activity", lambda x: int(_bool_flag(x, "active"))
    )
    res["hd_gen_health"] = _map_field(entities, "general_health", int)
    res["hd_ment_health"] = _map_field(entities, "mental_health", int)

    # Additional mappings based on family history or diabetes history could
    # be added here
    res["hd_diabetes"] = _map_field(
        entities,
        "diagnosis",
        lambda x: 2 if "diabetes" in str(x).lower() else 0,
    )

    return {k: v for k, v in res.items() if v is not None}


# ══════════════════════════════════════════════════════════════════════════
#  Lung Cancer Feature Mapping
# ══════════════════════════════════════════════════════════════════════════


def map_to_lung_features(entities: dict[str, Any]) -> dict[str, Any]:
    """
    Map extracted clinical entities to lung cancer model input.
    """
    res = {}
    res["lc_age"] = _map_field(entities, "age")
    res["lc_gender"] = _map_field(
        entities, "gender", lambda x: 1 if x == "male" else 0
    )
    res["lc_smoking"] = _map_field(
        entities, "smoking", lambda x: int(_bool_flag(x, "yes"))
    )

    # New mapped features for lung cancer form
    res["lc_chronic_disease"] = _map_field(
        entities, "copd", lambda x: int(_bool_flag(x, "yes"))
    )
    res["lc_wheezing"] = _map_field(
        entities, "asthma", lambda x: int(_bool_flag(x, "yes"))
    )

    return {k: v for k, v in res.items() if v is not None}


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
