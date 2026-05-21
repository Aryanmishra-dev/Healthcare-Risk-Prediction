"""
Medical NLP layer for the document AI pipeline.

Extracts clinical entities from raw medical report text using
rule-based regex patterns.

Architecture note:
  This module is designed so the regex engine can be swapped for
  spaCy / scispaCy NER models later by replacing `extract_clinical_entities`.
"""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════
#  Pattern Definitions
# ══════════════════════════════════════════════════════════════════════════

# BMI — matches "BMI 27.4", "BMI: 27.4", "BMI of 27.4", "body mass index 32"
_BMI_PATTERNS = [
    re.compile(r"\b(?:BMI|body\s*mass\s*index)\s*[:=]?\s*(?:of\s+)?(\d+\.?\d*)", re.IGNORECASE),
]

# Blood Pressure — matches "BP 140/90", "blood pressure elevated/high/normal",
# "high blood pressure", "hypertension"
_BP_VALUE_PATTERN = re.compile(
    r"\b(?:BP|blood\s*pressure)\s*[:=]?\s*(\d{2,3})\s*/\s*(\d{2,3})", re.IGNORECASE
)
_BP_KEYWORD_HIGH = re.compile(
    r"\b(?:high\s*blood\s*pressure|hypertension|(?:blood\s*pressure|BP)\s*[:=]?\s*(?:elevated|high))",
    re.IGNORECASE,
)
_BP_KEYWORD_NORMAL = re.compile(
    r"\b(?:normal\s*blood\s*pressure|normotensive|(?:blood\s*pressure|BP)\s*[:=]?\s*normal)",
    re.IGNORECASE,
)

# Cholesterol — "cholesterol 240", "cholesterol high/normal", "hypercholesterolemia"
_CHOL_VALUE_PATTERN = re.compile(
    r"\b(?:cholesterol|total\s*cholesterol)\s*[:=]?\s*(\d{2,3})", re.IGNORECASE
)
_CHOL_KEYWORD_HIGH = re.compile(
    r"\b(?:high\s*cholesterol|hypercholesterol|elevated\s*cholesterol|cholesterol\s*[:=]?\s*(?:elevated|high))",
    re.IGNORECASE,
)
_CHOL_KEYWORD_NORMAL = re.compile(
    r"\b(?:normal\s*cholesterol|cholesterol\s*[:=]?\s*normal)",
    re.IGNORECASE,
)

# Smoking — "smoker", "smoking: yes", "non-smoker", "smoking history: positive"
_SMOKER_YES = re.compile(
    r"\b(?:(?:current\s+)?smoker|smoking\s*[:=]?\s*(?:yes|positive|active)|tobacco\s+use|smokes)",
    re.IGNORECASE,
)
_SMOKER_NO = re.compile(
    r"\b(?:non[\-\s]?smoker|no\s+smoking|smoking\s*[:=]?\s*(?:no|negative|none|never|denied)|never\s+smoked|does\s+not\s+smoke)",
    re.IGNORECASE,
)

# Physical Activity — "physically active", "sedentary", "exercise: regular"
_ACTIVE_YES = re.compile(
    r"\b(?:physically\s+active|active\s+lifestyle|regular\s+exercise|exercises?\s+regularly|physical\s*activity\s*[:=]?\s*(?:yes|active|regular))",
    re.IGNORECASE,
)
_ACTIVE_NO = re.compile(
    r"\b(?:sedentary|physically\s+inactive|no\s+exercise|physical\s*activity\s*[:=]?\s*(?:no|inactive|none|minimal))",
    re.IGNORECASE,
)

# General Health — 1-5 scale or keyword
_HEALTH_KEYWORD = {
    "excellent": 1,
    "very good": 2,
    "good": 3,
    "fair": 4,
    "poor": 5,
}
_GENERAL_HEALTH_PATTERN = re.compile(
    r"\b(?:general\s*health|overall\s*health|health\s*status)\s*[:=]?\s*(excellent|very\s*good|good|fair|poor|\d)",
    re.IGNORECASE,
)

# Mental Health — "mental health days: 5", "poor mental health 10 days"
_MENTAL_HEALTH_PATTERN = re.compile(
    r"\b(?:mental\s*health)\s*(?:days?\s*)?[:=]?\s*(\d{1,2})",
    re.IGNORECASE,
)
_MENTAL_HEALTH_DAYS = re.compile(
    r"(\d{1,2})\s*(?:days?\s+(?:of\s+)?(?:poor\s+)?mental\s*health)",
    re.IGNORECASE,
)

# Age — "age 52", "age: 65", "52 years old", "52 yo", "52-year-old", "Age: 25 Years"
_AGE_PATTERNS = [
    re.compile(r"\bage\s*[:=]?\s*(\d{1,3})\b(?!\s*years?\s*old)", re.IGNORECASE),
    re.compile(r"\bage\s*[:=]?\s*(\d{1,3})\s*years?\b", re.IGNORECASE),
    re.compile(r"\b(\d{1,3})\s*years?\b", re.IGNORECASE),
    re.compile(r"\b(\d{1,3})\s*(?:years?\s*old|y/?o\b|yr)", re.IGNORECASE),
    re.compile(r"\b(\d{1,3})[\-\s]?year[\-\s]?old\b", re.IGNORECASE),
    re.compile(r"\bpatient.*?(\d{2,3})\s*(?:years?|y/?o)", re.IGNORECASE),
]

# Gender — "male", "female", "sex: M/F", "gender: male", ", Male"
_GENDER_MALE = re.compile(
    r"\b(?:(?:sex|gender)\s*[:=]?\s*(?:male|m\b)|(?:^|\s)male\b(?:\s+patient)?|,\s*Male\b)",
    re.IGNORECASE,
)
_GENDER_FEMALE = re.compile(
    r"\b(?:(?:sex|gender)\s*[:=]?\s*(?:female|f\b)|(?:^|\s)female\b(?:\s+patient)?|,\s*Female\b)",
    re.IGNORECASE,
)

# Blood Group — "blood group: O+", "type: A negative"
_BLOOD_GROUP_PATTERN = re.compile(
    r"\b(?:blood\s*group|blood\s*type|type)\s*[:=]?\s*(A|B|AB|O)\s*([\+\-]|pos(?:itive)?|neg(?:ative)?)",
    re.IGNORECASE,
)

# Medical History, Diagnosis, Medications (matches until next heading or blank line)
_SECTION_LOOKAHEAD = r"(?=\n\s*[A-Z][A-Za-z\s]+:|\n\s*\n|\Z)"

_MEDICAL_HISTORY_PATTERN = re.compile(
    r"\b(?:medical\s*history|pmh|past\s*medical\s*history)\s*[:=]\s*(.*?)" + _SECTION_LOOKAHEAD,
    re.IGNORECASE | re.DOTALL,
)

_DIAGNOSIS_PATTERN = re.compile(
    r"\b(?:diagnosis|assessment|impression)\s*[:=]\s*(.*?)" + _SECTION_LOOKAHEAD,
    re.IGNORECASE | re.DOTALL,
)

_MEDICATIONS_PATTERN = re.compile(
    r"\b(?:medications?|rx|prescriptions?)\s*[:=]\s*(.*?)" + _SECTION_LOOKAHEAD,
    re.IGNORECASE | re.DOTALL,
)


# ══════════════════════════════════════════════════════════════════════════
#  Extraction Functions
# ══════════════════════════════════════════════════════════════════════════

def _extract_bmi(text: str) -> float | None:
    for pat in _BMI_PATTERNS:
        m = pat.search(text)
        if m:
            return float(m.group(1))
    return None


def _extract_blood_pressure(text: str) -> str | None:
    """Return 'high', 'normal', or None."""
    # Check numeric value first (systolic >= 140 or diastolic >= 90 → high)
    m = _BP_VALUE_PATTERN.search(text)
    if m:
        systolic, diastolic = int(m.group(1)), int(m.group(2))
        return "high" if systolic >= 140 or diastolic >= 90 else "normal"
    if _BP_KEYWORD_HIGH.search(text):
        return "high"
    if _BP_KEYWORD_NORMAL.search(text):
        return "normal"
    return None


def _extract_cholesterol(text: str) -> str | None:
    """Return 'high', 'normal', or None."""
    m = _CHOL_VALUE_PATTERN.search(text)
    if m:
        val = int(m.group(1))
        return "high" if val >= 240 else "normal"
    if _CHOL_KEYWORD_HIGH.search(text):
        return "high"
    if _CHOL_KEYWORD_NORMAL.search(text):
        return "normal"
    return None


def _extract_smoking(text: str) -> str | None:
    """Return 'yes', 'no', or None."""
    # Check 'no' first (more specific patterns like 'non-smoker')
    if _SMOKER_NO.search(text):
        return "no"
    if _SMOKER_YES.search(text):
        return "yes"
    return None


def _extract_physical_activity(text: str) -> str | None:
    """Return 'active', 'inactive', or None."""
    if _ACTIVE_YES.search(text):
        return "active"
    if _ACTIVE_NO.search(text):
        return "inactive"
    return None


def _extract_general_health(text: str) -> int | None:
    """Return 1-5 scale or None."""
    m = _GENERAL_HEALTH_PATTERN.search(text)
    if m:
        val = m.group(1).lower().strip()
        if val.isdigit():
            v = int(val)
            return v if 1 <= v <= 5 else None
        return _HEALTH_KEYWORD.get(val)
    return None


def _extract_mental_health(text: str) -> int | None:
    """Return 0-30 days or None."""
    m = _MENTAL_HEALTH_PATTERN.search(text)
    if m:
        v = int(m.group(1))
        return min(v, 30)
    m = _MENTAL_HEALTH_DAYS.search(text)
    if m:
        v = int(m.group(1))
        return min(v, 30)
    return None


def _extract_age(text: str) -> int | None:
    for pat in _AGE_PATTERNS:
        m = pat.search(text)
        if m:
            val = int(m.group(1))
            if 0 < val <= 120:
                return val
    return None


def _extract_gender(text: str) -> str | None:
    """Return 'male', 'female', or None."""
    if _GENDER_MALE.search(text):
        return "male"
    if _GENDER_FEMALE.search(text):
        return "female"
    return None


def _extract_blood_group(text: str) -> str | None:
    m = _BLOOD_GROUP_PATTERN.search(text)
    if m:
        group = m.group(1).upper()
        sign = m.group(2).lower()
        if sign in ["+", "pos", "positive"]:
            return f"{group}+"
        elif sign in ["-", "neg", "negative"]:
            return f"{group}-"
    return None


def _extract_medical_history(text: str) -> str | None:
    m = _MEDICAL_HISTORY_PATTERN.search(text)
    if m:
        return m.group(1).strip()
    return None


def _extract_diagnosis(text: str) -> str | None:
    m = _DIAGNOSIS_PATTERN.search(text)
    if m:
        return m.group(1).strip()
    return None


def _extract_medications(text: str) -> str | None:
    m = _MEDICATIONS_PATTERN.search(text)
    if m:
        return m.group(1).strip()
    return None


# ══════════════════════════════════════════════════════════════════════════
#  Public API
# ══════════════════════════════════════════════════════════════════════════

def extract_clinical_entities(raw_text: str) -> dict[str, Any]:
    """
    Extract clinical entities from raw medical report text.

    Returns a dictionary with keys:
      - bmi (float | None)
      - blood_pressure ("high" | "normal" | None)
      - cholesterol ("high" | "normal" | None)
      - smoking ("yes" | "no" | None)
      - physical_activity ("active" | "inactive" | None)
      - general_health (int 1-5 | None)
      - mental_health (int 0-30 | None)
      - age (int | None)
      - gender ("male" | "female" | None)
      - blood_group (str | None)
      - medical_history (str | None)
      - diagnosis (str | None)
      - medications (str | None)
    """
    entities = {
        "bmi": _extract_bmi(raw_text),
        "blood_pressure": _extract_blood_pressure(raw_text),
        "cholesterol": _extract_cholesterol(raw_text),
        "smoking": _extract_smoking(raw_text),
        "physical_activity": _extract_physical_activity(raw_text),
        "general_health": _extract_general_health(raw_text),
        "mental_health": _extract_mental_health(raw_text),
        "age": _extract_age(raw_text),
        "gender": _extract_gender(raw_text),
        "blood_group": _extract_blood_group(raw_text),
        "medical_history": _extract_medical_history(raw_text),
        "diagnosis": _extract_diagnosis(raw_text),
        "medications": _extract_medications(raw_text),
    }

    found = {k: v for k, v in entities.items() if v is not None}
    logger.info("clinical_entities_extracted", extra={"found_count": len(found), "fields": list(found.keys())})

    return entities
