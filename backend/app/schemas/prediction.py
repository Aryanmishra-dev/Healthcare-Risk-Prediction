"""
Pydantic schemas for the healthcare risk prediction API.
"""

from pydantic import BaseModel, Field


MEDICAL_DISCLAIMER = (
    "This prediction is educational decision support, not a diagnosis. "
    "Consult a qualified clinician for medical advice."
)


# ── Diabetes ───────────────────────────────────────────────────────────────

class DiabetesPredictionRequest(BaseModel):
    age: float = Field(..., ge=1, le=13, description="Age group (1=18-24 … 13=80+)")
    bmi: float = Field(..., gt=0, le=100, description="Body Mass Index")
    bp: float = Field(..., ge=0, le=1, description="High blood pressure (1=Yes, 0=No)")
    cholesterol: float = Field(..., ge=0, le=1, description="High cholesterol (1=Yes, 0=No)")
    smoker: float = Field(..., ge=0, le=1, description="Smoker - 100+ cigarettes ever (1=Yes, 0=No)")
    activity: float = Field(..., ge=0, le=1, description="Physical activity (1=Active, 0=Inactive)")
    health: float = Field(..., ge=1, le=5, description="General health (1=Excellent … 5=Poor)")
    mental: float = Field(..., ge=0, le=30, description="Mental health - bad days in past 30 (0-30)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "age": 8,
                    "bmi": 32.0,
                    "bp": 1,
                    "cholesterol": 1,
                    "smoker": 0,
                    "activity": 0,
                    "health": 3,
                    "mental": 5,
                }
            ]
        }
    }


# Backward compatibility alias
PredictionRequest = DiabetesPredictionRequest


# ── Heart Disease ──────────────────────────────────────────────────────────

class HeartDiseasePredictionRequest(BaseModel):
    age: float = Field(..., ge=1, le=13, description="Age group (1=18-24 … 13=80+)")
    sex: int = Field(..., ge=0, le=1, description="Sex (1=Male, 0=Female)")
    bmi: float = Field(..., gt=0, le=100, description="Body Mass Index")
    high_bp: int = Field(..., ge=0, le=1, description="High blood pressure (1=Yes, 0=No)")
    high_chol: int = Field(..., ge=0, le=1, description="High cholesterol (1=Yes, 0=No)")
    smoker: int = Field(..., ge=0, le=1, description="Smoking history - 100+ cigarettes (1=Yes, 0=No)")
    phys_activity: int = Field(..., ge=0, le=1, description="Physical activity in past 30 days (1=Yes, 0=No)")
    fruits: int = Field(..., ge=0, le=1, description="Consume fruit 1+ times per day (1=Yes, 0=No)")
    veggies: int = Field(..., ge=0, le=1, description="Consume vegetables 1+ times per day (1=Yes, 0=No)")
    heavy_drinker: int = Field(..., ge=0, le=1, description="Heavy alcohol consumption (1=Yes, 0=No)")
    gen_health: int = Field(..., ge=1, le=5, description="General health (1=Excellent … 5=Poor)")
    ment_health: int = Field(..., ge=0, le=30, description="Days of poor mental health in past 30 (0-30)")
    phys_health: int = Field(..., ge=0, le=30, description="Days of poor physical health in past 30 (0-30)")
    diabetes: int = Field(..., ge=0, le=1, description="Diabetes diagnosis (1=Yes, 0=No)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "age": 9,
                    "sex": 1,
                    "bmi": 28.5,
                    "high_bp": 1,
                    "high_chol": 1,
                    "smoker": 1,
                    "phys_activity": 0,
                    "fruits": 1,
                    "veggies": 1,
                    "heavy_drinker": 0,
                    "gen_health": 4,
                    "ment_health": 10,
                    "phys_health": 15,
                    "diabetes": 1,
                }
            ]
        }
    }


# ── Lung Cancer ────────────────────────────────────────────────────────────

class LungCancerPredictionRequest(BaseModel):
    age: int = Field(..., ge=18, le=100, description="Patient age in years")
    gender: int = Field(..., ge=0, le=1, description="Gender (1=Male, 0=Female)")
    smoking: int = Field(..., ge=0, le=1, description="Smoking (1=Yes, 0=No)")
    yellow_fingers: int = Field(..., ge=0, le=1, description="Yellow fingers (1=Yes, 0=No)")
    chronic_disease: int = Field(..., ge=0, le=1, description="Chronic disease (1=Yes, 0=No)")
    fatigue: int = Field(..., ge=0, le=1, description="Fatigue (1=Yes, 0=No)")
    wheezing: int = Field(..., ge=0, le=1, description="Wheezing (1=Yes, 0=No)")
    shortness_of_breath: int = Field(..., ge=0, le=1, description="Shortness of breath (1=Yes, 0=No)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "age": 65,
                    "gender": 1,
                    "smoking": 1,
                    "yellow_fingers": 1,
                    "chronic_disease": 1,
                    "fatigue": 1,
                    "wheezing": 1,
                    "shortness_of_breath": 1,
                }
            ]
        }
    }


# ── Shared Response ────────────────────────────────────────────────────────

class PredictionResponse(BaseModel):
    risk_percentage: float = Field(..., description="Risk as percentage (0-100)")
    risk_level: str = Field(..., description="Risk classification: Low, Moderate, or High")
    prediction: int = Field(0, ge=0, le=1, description="Binary risk class derived from the model probability")
    probability: float = Field(0.0, ge=0, le=1, description="Risk probability in the [0, 1] range")
    model_name: str = Field("unknown", description="Model family used for inference")
    model_version: str = Field("local", description="Model version or artifact stage")
    disclaimer: str = Field(MEDICAL_DISCLAIMER, description="Medical safety disclaimer")


class LegacyDiabetesAuditRequest(BaseModel):
    pregnancies: float = Field(0, ge=0, le=30)
    glucose: float = Field(..., ge=0, le=500)
    blood_pressure: float = Field(..., ge=0, le=300)
    skin_thickness: float = Field(0, ge=0, le=200)
    insulin: float = Field(0, ge=0, le=1000)
    bmi: float = Field(..., ge=0, le=150)
    diabetes_pedigree_function: float = Field(0, ge=0, le=5)
    age: float = Field(..., ge=0, le=120)


class LegacyHeartAuditRequest(BaseModel):
    age: float = Field(..., ge=0, le=120)
    sex: int = Field(..., ge=0, le=1)
    cp: int = Field(0, ge=0, le=4)
    trestbps: float = Field(..., ge=0, le=300)
    chol: float = Field(..., ge=0, le=700)
    fbs: int = Field(0, ge=0, le=1)
    restecg: int = Field(0, ge=0, le=2)
    thalach: float = Field(0, ge=0, le=250)
    exang: int = Field(0, ge=0, le=1)
    oldpeak: float = Field(0, ge=0, le=10)
    slope: int = Field(0, ge=0, le=3)
    ca: int = Field(0, ge=0, le=4)
    thal: int = Field(0, ge=0, le=3)


class LegacyLungCancerAuditRequest(BaseModel):
    gender: int = Field(..., ge=0, le=2)
    age: int = Field(..., ge=0, le=120)
    smoking: int = Field(..., ge=0, le=2)
    yellow_fingers: int = Field(0, ge=0, le=2)
    anxiety: int = Field(0, ge=0, le=2)
    peer_pressure: int = Field(0, ge=0, le=2)
    chronic_disease: int = Field(0, ge=0, le=2)
    fatigue: int = Field(0, ge=0, le=2)
    allergy: int = Field(0, ge=0, le=2)
    wheezing: int = Field(0, ge=0, le=2)
    alcohol_consuming: int = Field(0, ge=0, le=2)
    coughing: int = Field(0, ge=0, le=2)
    shortness_of_breath: int = Field(0, ge=0, le=2)
    swallowing_difficulty: int = Field(0, ge=0, le=2)
    chest_pain: int = Field(0, ge=0, le=2)
