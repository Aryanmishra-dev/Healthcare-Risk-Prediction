"""
FastAPI Healthcare Risk Prediction Service.

Run locally:
    uvicorn backend.app.api.legacy_main:app --reload --port 8000
"""

import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.schemas.prediction import (HeartDiseasePredictionRequest,
                                            LungCancerPredictionRequest,
                                            PredictionRequest,
                                            PredictionResponse)
from backend.app.services.model_loader import (load_models, predict,
                                               predict_heart_disease,
                                               predict_lung_cancer)

# ── Rate limiting ──────────────────────────────────────────────────────────
RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))
_request_log: dict[str, list[float]] = defaultdict(list)
_MAX_TRACKED_IPS = 10_000  # Prevent unbounded memory growth


def _cors_origins(default: str) -> list[str]:
    """Prefer ALLOWED_ORIGINS while keeping CORS_ORIGINS backward compatible."""
    raw_origins = (
        os.environ.get("ALLOWED_ORIGINS") or os.environ.get("CORS_ORIGINS") or default
    )
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models at startup."""
    load_models(app)
    yield


app = FastAPI(
    title="Healthcare Risk Prediction API",
    description="Predicts disease risk from health indicators using trained XGBoost models.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# ── CORS ───────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = _cors_origins(
    "https://yourdomain.com,http://localhost:8000,http://127.0.0.1:8000",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-CSRFToken"],
    expose_headers=["X-CSRFToken"],
    allow_credentials="*" not in ALLOWED_ORIGINS,
)


# ── Rate-limit middleware ──────────────────────────────────────────────────
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = now - 60
    # Prune old entries for this IP
    _request_log[client_ip] = [t for t in _request_log[client_ip] if t > window]
    if len(_request_log[client_ip]) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Try again later."},
        )
    _request_log[client_ip].append(now)
    # Evict stale IPs to prevent unbounded memory growth
    if len(_request_log) > _MAX_TRACKED_IPS:
        stale = [ip for ip, ts in _request_log.items() if not ts or ts[-1] < window]
        for ip in stale:
            del _request_log[ip]
    return await call_next(request)


# ══════════════════════════════════════════════════════════════════════════
#  Root
# ══════════════════════════════════════════════════════════════════════════


@app.get("/")
@app.get("/api")
def root():
    return {
        "service": "Healthcare Risk Prediction API",
        "status": "running",
        "models": ["diabetes", "heart_disease", "lung_cancer"],
    }


# ══════════════════════════════════════════════════════════════════════════
#  Diabetes Prediction
# ══════════════════════════════════════════════════════════════════════════


@app.post("/predict", response_model=PredictionResponse)
@app.post("/api/predict", response_model=PredictionResponse)
async def make_diabetes_prediction(request: Request, data: PredictionRequest):
    """
    Predict diabetes risk from health indicators.

    Returns risk percentage (0-100) and risk level (Low/Moderate/High).
    """
    result = await predict(
        request=request,
        age_group=data.age,
        bmi=data.bmi,
        high_bp=data.bp,
        smoker=data.smoker,
        high_cholesterol=data.cholesterol,
        physical_activity=data.activity,
        general_health=data.health,
        mental_health=data.mental,
    )
    return PredictionResponse(**result)


# ══════════════════════════════════════════════════════════════════════════
#  Heart Disease Prediction
# ══════════════════════════════════════════════════════════════════════════


@app.post("/predict-heart", response_model=PredictionResponse)
@app.post("/api/predict-heart", response_model=PredictionResponse)
async def make_heart_disease_prediction(
    request: Request, data: HeartDiseasePredictionRequest
):
    """
    Predict heart disease risk from health indicators.

    Returns risk percentage (0-100) and risk level (Low/Moderate/High).
    """
    result = await predict_heart_disease(
        request=request,
        age=data.age,
        sex=data.sex,
        bmi=data.bmi,
        high_bp=data.high_bp,
        high_chol=data.high_chol,
        smoker=data.smoker,
        phys_activity=data.phys_activity,
        fruits=data.fruits,
        veggies=data.veggies,
        heavy_drinker=data.heavy_drinker,
        gen_health=data.gen_health,
        ment_health=data.ment_health,
        phys_health=data.phys_health,
        diabetes=data.diabetes,
    )
    return PredictionResponse(**result)


# ══════════════════════════════════════════════════════════════════════════
#  Lung Cancer Prediction
# ══════════════════════════════════════════════════════════════════════════


@app.post("/predict-lung", response_model=PredictionResponse)
@app.post("/api/predict-lung", response_model=PredictionResponse)
async def make_lung_cancer_prediction(
    request: Request, data: LungCancerPredictionRequest
):
    """
    Predict lung cancer risk from patient indicators.

    Returns risk percentage (0-100) and risk level (Low/Moderate/High).
    """
    result = await predict_lung_cancer(
        request=request,
        age=data.age,
        gender=data.gender,
        smoking=data.smoking,
        yellow_fingers=data.yellow_fingers,
        chronic_disease=data.chronic_disease,
        fatigue=data.fatigue,
        wheezing=data.wheezing,
        shortness_of_breath=data.shortness_of_breath,
    )
    return PredictionResponse(**result)
