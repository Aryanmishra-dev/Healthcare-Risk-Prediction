"""
Medical NLP layer for the document AI pipeline.

Extracts clinical entities from raw medical report text using
rule-based regex patterns.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Negation detection — checked before keyword patterns to avoid false positives
_NEGATION_PREFIX_PATTERNS = re.compile(
    r"\b(?:no|denies|denied|without|rule\s*out|ruled?\s*out|"
    r"negative\s*for|no\s*history\s*of|no\s*evidence\s*of|"
    r"does\s*not\s*have|denies\s*any\s*history\s*of)\s+(?:any\s+)?",
    re.IGNORECASE,
)


def _is_negated(text: str, keyword: str, window: int = 30) -> bool:
    """Check if keyword is negated within a window of chars before it."""
    idx = text.lower().find(keyword.lower())
    if idx == -1:
        return False
    start = max(0, idx - window)
    prefix = text[start:idx]
    return bool(_NEGATION_PREFIX_PATTERNS.search(prefix))


# Pattern Definitions
_BMI_PATTERNS = [
    re.compile(
        r"\b(?:BMI|body\s*mass\s*index)\s*[:=]?\s*(?:of\s+)?(\d+\.?\d*)",
        re.IGNORECASE,
    )
]
_BP_VALUE_PATTERN = re.compile(
    r"\b(?:BP|blood\s*pressure)\s*[:=]?\s*(\d{2,3})\s*/\s*(\d{2,3})",
    re.IGNORECASE,
)
_BP_KEYWORD_HIGH = re.compile(
    r"\b(?:high\s*blood\s*pressure|hypertension|"
    r"(?:blood\s*pressure|BP)\s*[:=]?\s*(?:elevated|high))",
    re.IGNORECASE,
)
_BP_KEYWORD_NORMAL = re.compile(
    r"\b(?:normal\s*blood\s*pressure|normotensive|"
    r"(?:blood\s*pressure|BP)\s*[:=]?\s*normal)",
    re.IGNORECASE,
)
_CHOL_VALUE_PATTERN = re.compile(
    r"\b(?:cholesterol|total\s*cholesterol)\s*[:=]?\s*(\d{2,3})", re.IGNORECASE
)
_CHOL_KEYWORD_HIGH = re.compile(
    r"\b(?:high\s*cholesterol|hypercholesterol|"
    r"elevated\s*cholesterol|cholesterol\s*[:=]?\s*(?:elevated|high))",
    re.IGNORECASE,
)
_CHOL_KEYWORD_NORMAL = re.compile(
    r"\b(?:normal\s*cholesterol|cholesterol\s*[:=]?\s*normal)", re.IGNORECASE
)
_SMOKER_YES = re.compile(
    r"\b(?:(?:current\s+)?smoker|"
    r"smoking\s*[:=]?\s*(?:yes|positive|active)|tobacco\s+use|smokes)",
    re.IGNORECASE,
)
_SMOKER_NO = re.compile(
    r"\b(?:non[\-\s]?smoker|no\s+smoking|"
    r"smoking\s*[:=]?\s*(?:no|negative|none|never|denied)|"
    r"never\s+smoked|does\s+not\s+smoke)",
    re.IGNORECASE,
)
_ACTIVE_YES = re.compile(
    r"\b(?:physically\s+active|active\s+lifestyle|"
    r"regular\s+exercise|exercises?\s+regularly|"
    r"physical\s*activity\s*[:=]?\s*(?:yes|active|regular))",
    re.IGNORECASE,
)
_ACTIVE_NO = re.compile(
    r"\b(?:sedentary|physically\s+inactive|no\s+exercise|"
    r"physical\s*activity\s*[:=]?\s*(?:no|inactive|none|minimal))",
    re.IGNORECASE,
)
_HEALTH_KEYWORD = {
    "excellent": 1,
    "very good": 2,
    "good": 3,
    "fair": 4,
    "poor": 5,
}
_GENERAL_HEALTH_PATTERN = re.compile(
    r"\b(?:general\s*health|overall\s*health|health\s*status)\s*[:=]?\s*"
    r"(excellent|very\s*good|good|fair|poor|\d)",
    re.IGNORECASE,
)
_MENTAL_HEALTH_PATTERN = re.compile(
    r"\b(?:mental\s*health)\s*(?:days?\s*)?[:=]?\s*(\d{1,2})", re.IGNORECASE
)
_MENTAL_HEALTH_DAYS = re.compile(
    r"(\d{1,2})\s*(?:days?\s+(?:of\s+)?(?:poor\s+)?mental\s*health)",
    re.IGNORECASE,
)
_AGE_PATTERNS = [
    re.compile(
        r"\bage\s*[:=]?\s*(\d{1,3})\b(?!\s*years?\s*old)", re.IGNORECASE
    ),
    re.compile(r"\bage\s*[:=]?\s*(\d{1,3})\s*years?\b", re.IGNORECASE),
    re.compile(r"\b(\d{1,3})\s*years?\b", re.IGNORECASE),
    re.compile(r"\b(\d{1,3})\s*(?:years?\s*old|y/?o\b|yr)", re.IGNORECASE),
    re.compile(r"\b(\d{1,3})[\-\s]?year[\-\s]?old\b", re.IGNORECASE),
    re.compile(r"\bpatient.*?(\d{2,3})\s*(?:years?|y/?o)", re.IGNORECASE),
]
_GENDER_MALE = re.compile(
    r"\b(?:(?:sex|gender)\s*[:=]?\s*(?:male|m\b)|"
    r"(?:^|\s)male\b(?:\s+patient)?|,\s*Male\b)",
    re.IGNORECASE,
)
_GENDER_FEMALE = re.compile(
    r"\b(?:(?:sex|gender)\s*[:=]?\s*(?:female|f\b)|"
    r"(?:^|\s)female\b(?:\s+patient)?|,\s*Female\b)",
    re.IGNORECASE,
)
_BLOOD_GROUP_PATTERN = re.compile(
    r"\b(?:blood\s*group|blood\s*type|type)\s*[:=]?\s*"
    r"(A|B|AB|O)\s*([\+\-]|pos(?:itive)?|neg(?:ative)?)",
    re.IGNORECASE,
)
_SECTION_LOOKAHEAD = r"(?=\n\s*[A-Z][A-Za-z\s]+:|\n\s*\n|\Z)"
_MEDICAL_HISTORY_PATTERN = re.compile(
    r"\b(?:medical\s*history|pmh|past\s*medical\s*history)\s*[:=]\s*(.*?)"
    + _SECTION_LOOKAHEAD,
    re.IGNORECASE | re.DOTALL,
)
_DIAGNOSIS_PATTERN = re.compile(
    r"\b(?:diagnosis|assessment|impression)\s*[:=]\s*(.*?)"
    + _SECTION_LOOKAHEAD,
    re.IGNORECASE | re.DOTALL,
)
_MEDICATIONS_PATTERN = re.compile(
    r"\b(?:medications?|rx|prescriptions?)\s*[:=]\s*(.*?)"
    + _SECTION_LOOKAHEAD,
    re.IGNORECASE | re.DOTALL,
)

# New Patterns
_GLUCOSE_PATTERN = re.compile(
    r"\b(?:glucose|blood\s*sugar)\s*[:=]?\s*(\d{2,3})", re.IGNORECASE
)
_FASTING_GLUCOSE_PATTERN = re.compile(
    r"\b(?:fasting\s*glucose|fbs)\s*[:=]?\s*(\d{2,3})", re.IGNORECASE
)
_RANDOM_GLUCOSE_PATTERN = re.compile(
    r"\b(?:random\s*glucose|rbs)\s*[:=]?\s*(\d{2,3})", re.IGNORECASE
)
_HBA1C_PATTERN = re.compile(r"\bhba1c\s*[:=]?\s*(\d{1,2}\.\d)", re.IGNORECASE)
_LDL_PATTERN = re.compile(
    r"\b(?:ldl|ldl-c)\s*[:=]?\s*(\d{2,3})", re.IGNORECASE
)
_TRIGLYCERIDES_PATTERN = re.compile(
    r"\b(?:triglycerides|tg)\s*[:=]?\s*(\d{2,3})", re.IGNORECASE
)
_COPD_PATTERN = re.compile(
    r"\b(?:copd|chronic\s*obstructive\s*pulmonary\s*disease)\b", re.IGNORECASE
)
_ASTHMA_PATTERN = re.compile(r"\basthma\b", re.IGNORECASE)
_LUNG_CANCER_PATTERN = re.compile(
    r"\b(?:lung\s*cancer|pulmonary\s*carcinoma)\b", re.IGNORECASE
)
_FAM_HIST_DIABETES = re.compile(
    r"\bfamily\s*history\s*(?:of\s*)?diabetes\b", re.IGNORECASE
)
_FAM_HIST_HEART = re.compile(
    r"\bfamily\s*history\s*(?:of\s*)?(?:heart\s*disease|cvd|cardiovascular)\b",
    re.IGNORECASE,
)
_FAM_HIST_CANCER = re.compile(
    r"\bfamily\s*history\s*(?:of\s*)?cancer\b", re.IGNORECASE
)
_HEART_RATE_PATTERN = re.compile(
    r"\b(?:heart\s*rate|hr|pulse)\s*[:=]?\s*(\d{2,3})\b", re.IGNORECASE
)
_RESP_RATE_PATTERN = re.compile(
    r"\b(?:respiratory\s*rate|rr)\s*[:=]?\s*(\d{1,2})\b", re.IGNORECASE
)


def _make_res(val, conf, raw):
    if val is None:
        return None
    return {"value": val, "confidence": conf, "raw": raw}


def _extract_bmi(text: str):
    for pat in _BMI_PATTERNS:
        m = pat.search(text)
        if m:
            return _make_res(float(m.group(1)), 0.9, m.group(0))
    return None


def _extract_blood_pressure(text: str):
    m = _BP_VALUE_PATTERN.search(text)
    if m:
        systolic, diastolic = int(m.group(1)), int(m.group(2))
        return _make_res(
            "high" if systolic >= 140 or diastolic >= 90 else "normal",
            0.95,
            m.group(0),
        )
    m = _BP_KEYWORD_HIGH.search(text)
    if m and not _is_negated(text, m.group(0)):
        return _make_res("high", 0.8, m.group(0))
    m = _BP_KEYWORD_NORMAL.search(text)
    if m and not _is_negated(text, m.group(0)):
        return _make_res("normal", 0.8, m.group(0))
    return None


def _extract_cholesterol(text: str):
    m = _CHOL_VALUE_PATTERN.search(text)
    if m:
        return _make_res(
            "high" if int(m.group(1)) >= 240 else "normal", 0.9, m.group(0)
        )
    m = _CHOL_KEYWORD_HIGH.search(text)
    if m and not _is_negated(text, m.group(0)):
        return _make_res("high", 0.8, m.group(0))
    m = _CHOL_KEYWORD_NORMAL.search(text)
    if m and not _is_negated(text, m.group(0)):
        return _make_res("normal", 0.8, m.group(0))
    return None


def _extract_smoking(text: str):
    m = _SMOKER_NO.search(text)
    if m and not _is_negated(text, m.group(0)):
        return _make_res("no", 0.85, m.group(0))
    m = _SMOKER_YES.search(text)
    if m and not _is_negated(text, m.group(0)):
        return _make_res("yes", 0.85, m.group(0))
    return None


def _extract_physical_activity(text: str):
    m = _ACTIVE_YES.search(text)
    if m and not _is_negated(text, m.group(0)):
        return _make_res("active", 0.8, m.group(0))
    m = _ACTIVE_NO.search(text)
    if m and not _is_negated(text, m.group(0)):
        return _make_res("inactive", 0.8, m.group(0))
    return None


def _extract_general_health(text: str):
    m = _GENERAL_HEALTH_PATTERN.search(text)
    if m:
        val = m.group(1).lower().strip()
        if val.isdigit():
            v = int(val)
            if 1 <= v <= 5:
                return _make_res(v, 0.9, m.group(0))
        elif val in _HEALTH_KEYWORD:
            return _make_res(_HEALTH_KEYWORD[val], 0.85, m.group(0))
    return None


def _extract_mental_health(text: str):
    m = _MENTAL_HEALTH_PATTERN.search(text)
    if m:
        return _make_res(min(int(m.group(1)), 30), 0.9, m.group(0))
    m = _MENTAL_HEALTH_DAYS.search(text)
    if m:
        return _make_res(min(int(m.group(1)), 30), 0.8, m.group(0))
    return None


def _extract_age(text: str):
    for pat in _AGE_PATTERNS:
        m = pat.search(text)
        if m:
            val = int(m.group(1))
            if 0 < val <= 120:
                return _make_res(val, 0.95, m.group(0))
    return None


def _extract_gender(text: str):
    m = _GENDER_MALE.search(text)
    if m:
        return _make_res("male", 0.95, m.group(0))
    m = _GENDER_FEMALE.search(text)
    if m:
        return _make_res("female", 0.95, m.group(0))
    return None


def _extract_blood_group(text: str):
    m = _BLOOD_GROUP_PATTERN.search(text)
    if m:
        group = m.group(1).upper()
        sign = m.group(2).lower()
        if sign in ["+", "pos", "positive"]:
            return _make_res(f"{group}+", 0.95, m.group(0))
        elif sign in ["-", "neg", "negative"]:
            return _make_res(f"{group}-", 0.95, m.group(0))
    return None


def _extract_medical_history(text: str):
    m = _MEDICAL_HISTORY_PATTERN.search(text)
    if m:
        return _make_res(m.group(1).strip(), 0.9, m.group(0))
    return None


def _extract_diagnosis(text: str):
    m = _DIAGNOSIS_PATTERN.search(text)
    if m:
        return _make_res(m.group(1).strip(), 0.9, m.group(0))
    return None


def _extract_medications(text: str):
    m = _MEDICATIONS_PATTERN.search(text)
    if m:
        return _make_res(m.group(1).strip(), 0.9, m.group(0))
    return None


def _extract_regex(pattern, text, conf=0.8, bool_flag=False, val_type=str):
    m = pattern.search(text)
    if m:
        if bool_flag:
            if _is_negated(text, m.group(0)):
                return None
            return _make_res("yes", conf, m.group(0))
        try:
            return _make_res(val_type(m.group(1)), conf, m.group(0))
        except Exception:
            return None
    if bool_flag:
        return None  # Absence of evidence is not evidence of absence
    return None


def extract_clinical_entities(raw_text: str) -> dict[str, Any]:
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
        "glucose": _extract_regex(_GLUCOSE_PATTERN, raw_text, val_type=float),
        "fasting_glucose": _extract_regex(
            _FASTING_GLUCOSE_PATTERN, raw_text, val_type=float
        ),
        "random_glucose": _extract_regex(
            _RANDOM_GLUCOSE_PATTERN, raw_text, val_type=float
        ),
        "hba1c": _extract_regex(_HBA1C_PATTERN, raw_text, val_type=float),
        "ldl": _extract_regex(_LDL_PATTERN, raw_text, val_type=float),
        "triglycerides": _extract_regex(
            _TRIGLYCERIDES_PATTERN, raw_text, val_type=float
        ),
        "copd": _extract_regex(_COPD_PATTERN, raw_text, bool_flag=True),
        "asthma": _extract_regex(_ASTHMA_PATTERN, raw_text, bool_flag=True),
        "lung_cancer_history": _extract_regex(
            _LUNG_CANCER_PATTERN, raw_text, bool_flag=True
        ),
        "family_history_diabetes": _extract_regex(
            _FAM_HIST_DIABETES, raw_text, bool_flag=True
        ),
        "family_history_heart_disease": _extract_regex(
            _FAM_HIST_HEART, raw_text, bool_flag=True
        ),
        "family_history_cancer": _extract_regex(
            _FAM_HIST_CANCER, raw_text, bool_flag=True
        ),
        "heart_rate": _extract_regex(
            _HEART_RATE_PATTERN, raw_text, val_type=int
        ),
        "respiratory_rate": _extract_regex(
            _RESP_RATE_PATTERN, raw_text, val_type=int
        ),
    }

    found = {k: v for k, v in entities.items() if v is not None}
    logger.info(
        "clinical_entities_extracted",
        extra={"found_count": len(found), "fields": list(found.keys())},
    )

    return entities
