"""
FastAPI Healthcare Risk Prediction — Unified App.

Serves the HTMX-based UI and prediction API endpoints.

Run locally:
    uvicorn app.main:app --reload --port 8000
"""

import os
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from fastapi_backend.schemas import (
    PredictionRequest,
    PredictionResponse,
    HeartDiseasePredictionRequest,
    LungCancerPredictionRequest,
)
from fastapi_backend.model_loader import (
    load_models,
    predict,
    predict_heart_disease,
    predict_lung_cancer,
    build_diabetes_features,
)
from fastapi_backend.shap_explainer import (
    load_explainers,
    explain_diabetes,
    explain_heart,
    explain_lung,
)
from app.logging_config import setup_logging, get_logger
from prometheus_fastapi_instrumentator import Instrumentator

logger = get_logger(__name__)

# ── Rate limiting ──────────────────────────────────────────────────────────
RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))
_request_log: dict[str, list[float]] = defaultdict(list)
_MAX_TRACKED_IPS = 10_000


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models at startup."""
    setup_logging()
    logger.info("application_startup", version="3.0.0")
    load_models()
    load_explainers()
    logger.info("models_loaded")
    yield
    logger.info("application_shutdown")


app = FastAPI(
    title="Healthcare Risk Prediction",
    description="AI-powered clinical risk prediction with HTMX UI.",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# ── Templates & Static ────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

static_dir = os.path.join(BASE_DIR, "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ── CORS ───────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "https://yourdomain.com,http://localhost:8000,http://127.0.0.1:8000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept", "HX-Request"],
    allow_credentials=False,
)

# ── Trusted Host middleware (reject spoofed Host headers) ─────────────
TRUSTED_HOSTS = os.environ.get(
    "TRUSTED_HOSTS",
    "localhost,127.0.0.1,yourdomain.com,www.yourdomain.com,testserver",
).split(",")

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=TRUSTED_HOSTS,
)

# ── Prometheus metrics (exposes /metrics) ─────────────────────────────────
Instrumentator(
    excluded_handlers=["/metrics", "/healthz"],
    should_group_status_codes=True,
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


# ── Request-ID middleware (traceability) ───────────────────────────────
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Rate-limit middleware ──────────────────────────────────────────────────
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Prefer X-Forwarded-For (set by Nginx) over direct client IP
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = now - 60
    _request_log[client_ip] = [t for t in _request_log[client_ip] if t > window]
    if len(_request_log[client_ip]) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Try again later."},
        )
    _request_log[client_ip].append(now)
    if len(_request_log) > _MAX_TRACKED_IPS:
        stale = [ip for ip, ts in _request_log.items() if not ts or ts[-1] < window]
        for ip in stale:
            del _request_log[ip]
    response = await call_next(request)
    duration_ms = round((time.time() - now) * 1000, 1)
    request_id = getattr(request.state, "request_id", "-")
    logger.info(
        "http_request",
        method=request.method,
        path=str(request.url.path),
        status=response.status_code,
        duration_ms=duration_ms,
        client_ip=client_ip,
    )
    return response


# ── Helper ─────────────────────────────────────────────────────────────────
def _clamp(value, lo, hi):
    """Clamp a numeric value to [lo, hi]."""
    return max(lo, min(hi, value))


def _gauge_offset(pct: float) -> float:
    """Calculate SVG gauge stroke-dashoffset from percentage."""
    return round(251.2 - 188.4 * pct / 100, 1)


# ══════════════════════════════════════════════════════════════════════════
#  UI Pages
# ══════════════════════════════════════════════════════════════════════════

@app.get("/")
def index(request: Request):
    """Render the main prediction page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/healthz")
def healthz():
    """Liveness probe for Kubernetes / Docker."""
    return {"status": "healthy"}


@app.get("/api/v1/health/ready")
def readiness():
    """Readiness probe — confirms models are loaded and app is ready."""
    from fastapi_backend.model_loader import _diabetes_model
    models_loaded = _diabetes_model is not None
    if not models_loaded:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "models not loaded"},
        )
    return {"status": "ready"}


# ══════════════════════════════════════════════════════════════════════════
#  HTMX Prediction Endpoints (return HTML fragments)
# ══════════════════════════════════════════════════════════════════════════

@app.post("/predict/diabetes")
async def predict_diabetes_htmx(
    request: Request,
    age: float = Form(7),
    bmi: float = Form(25.0),
    bp: float = Form(0),
    cholesterol: float = Form(0),
    smoker: float = Form(0),
    activity: float = Form(1),
    health: float = Form(3),
    mental: float = Form(0),
):
    """Handle diabetes prediction form via HTMX."""
    try:
        payload = {
            "age": _clamp(float(age), 1, 13),
            "bmi": _clamp(float(bmi), 10, 80),
            "bp": _clamp(float(bp), 0, 1),
            "cholesterol": _clamp(float(cholesterol), 0, 1),
            "smoker": _clamp(float(smoker), 0, 1),
            "activity": _clamp(float(activity), 0, 1),
            "health": _clamp(float(health), 1, 5),
            "mental": _clamp(float(mental), 0, 30),
        }
        result = predict(
            age_group=payload["age"],
            bmi=payload["bmi"],
            high_bp=payload["bp"],
            smoker=payload["smoker"],
            high_cholesterol=payload["cholesterol"],
            physical_activity=payload["activity"],
            general_health=payload["health"],
            mental_health=payload["mental"],
        )
        pct = float(result["risk_percentage"])
        return templates.TemplateResponse("partials/diabetes_result.html", {
            "request": request,
            "result": result,
            "form": payload,
            "gauge_offset": _gauge_offset(pct),
        })
    except Exception as e:
        return templates.TemplateResponse("partials/error.html", {
            "request": request,
            "error": str(e),
        })


@app.post("/predict/heart")
async def predict_heart_htmx(
    request: Request,
    hd_age: float = Form(7),
    hd_sex: int = Form(1),
    hd_bmi: float = Form(25.0),
    hd_high_bp: int = Form(0),
    hd_high_chol: int = Form(0),
    hd_smoker: int = Form(0),
    hd_phys_activity: int = Form(1),
    hd_fruits: int = Form(1),
    hd_veggies: int = Form(1),
    hd_heavy_drinker: int = Form(0),
    hd_gen_health: int = Form(3),
    hd_ment_health: int = Form(0),
    hd_phys_health: int = Form(0),
    hd_diabetes: int = Form(0),
):
    """Handle heart disease prediction form via HTMX."""
    try:
        payload = {
            "age": _clamp(float(hd_age), 1, 13),
            "sex": _clamp(int(hd_sex), 0, 1),
            "bmi": _clamp(float(hd_bmi), 10, 80),
            "high_bp": _clamp(int(hd_high_bp), 0, 1),
            "high_chol": _clamp(int(hd_high_chol), 0, 1),
            "smoker": _clamp(int(hd_smoker), 0, 1),
            "phys_activity": _clamp(int(hd_phys_activity), 0, 1),
            "fruits": _clamp(int(hd_fruits), 0, 1),
            "veggies": _clamp(int(hd_veggies), 0, 1),
            "heavy_drinker": _clamp(int(hd_heavy_drinker), 0, 1),
            "gen_health": _clamp(int(hd_gen_health), 1, 5),
            "ment_health": _clamp(int(hd_ment_health), 0, 30),
            "phys_health": _clamp(int(hd_phys_health), 0, 30),
            "diabetes": _clamp(int(hd_diabetes), 0, 1),
        }
        result = predict_heart_disease(
            age=payload["age"],
            sex=payload["sex"],
            bmi=payload["bmi"],
            high_bp=payload["high_bp"],
            high_chol=payload["high_chol"],
            smoker=payload["smoker"],
            phys_activity=payload["phys_activity"],
            fruits=payload["fruits"],
            veggies=payload["veggies"],
            heavy_drinker=payload["heavy_drinker"],
            gen_health=payload["gen_health"],
            ment_health=payload["ment_health"],
            phys_health=payload["phys_health"],
            diabetes=payload["diabetes"],
        )
        pct = float(result["risk_percentage"])
        return templates.TemplateResponse("partials/heart_result.html", {
            "request": request,
            "result": result,
            "form": payload,
            "gauge_offset": _gauge_offset(pct),
        })
    except Exception as e:
        return templates.TemplateResponse("partials/error.html", {
            "request": request,
            "error": str(e),
        })


@app.post("/predict/lung")
async def predict_lung_htmx(
    request: Request,
    lc_age: int = Form(50),
    lc_gender: int = Form(1),
    lc_smoking: int = Form(0),
    lc_yellow_fingers: int = Form(0),
    lc_chronic_disease: int = Form(0),
    lc_fatigue: int = Form(0),
    lc_wheezing: int = Form(0),
    lc_shortness_of_breath: int = Form(0),
):
    """Handle lung cancer prediction form via HTMX."""
    try:
        payload = {
            "age": _clamp(int(lc_age), 18, 100),
            "gender": _clamp(int(lc_gender), 0, 1),
            "smoking": _clamp(int(lc_smoking), 0, 1),
            "yellow_fingers": _clamp(int(lc_yellow_fingers), 0, 1),
            "chronic_disease": _clamp(int(lc_chronic_disease), 0, 1),
            "fatigue": _clamp(int(lc_fatigue), 0, 1),
            "wheezing": _clamp(int(lc_wheezing), 0, 1),
            "shortness_of_breath": _clamp(int(lc_shortness_of_breath), 0, 1),
        }
        result = predict_lung_cancer(
            age=payload["age"],
            gender=payload["gender"],
            smoking=payload["smoking"],
            yellow_fingers=payload["yellow_fingers"],
            chronic_disease=payload["chronic_disease"],
            fatigue=payload["fatigue"],
            wheezing=payload["wheezing"],
            shortness_of_breath=payload["shortness_of_breath"],
        )
        pct = float(result["risk_percentage"])
        return templates.TemplateResponse("partials/lung_result.html", {
            "request": request,
            "result": result,
            "form": payload,
            "gauge_offset": _gauge_offset(pct),
        })
    except Exception as e:
        return templates.TemplateResponse("partials/error.html", {
            "request": request,
            "error": str(e),
        })


# ══════════════════════════════════════════════════════════════════════════
#  JSON API Endpoints (preserved from original FastAPI backend)
# ══════════════════════════════════════════════════════════════════════════

@app.get("/api")
def api_root():
    return {
        "service": "Healthcare Risk Prediction API",
        "status": "running",
        "models": ["diabetes", "heart_disease", "lung_cancer"],
    }


@app.post("/api/predict", response_model=PredictionResponse)
def api_predict_diabetes(data: PredictionRequest):
    """Predict diabetes risk (JSON API)."""
    result = predict(
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


@app.post("/api/predict-heart", response_model=PredictionResponse)
def api_predict_heart(data: HeartDiseasePredictionRequest):
    """Predict heart disease risk (JSON API)."""
    result = predict_heart_disease(
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


@app.post("/api/predict-lung", response_model=PredictionResponse)
def api_predict_lung(data: LungCancerPredictionRequest):
    """Predict lung cancer risk (JSON API)."""
    result = predict_lung_cancer(
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


# ══════════════════════════════════════════════════════════════════════════
#  Versioned API — /api/v1/
# ══════════════════════════════════════════════════════════════════════════

v1 = APIRouter(prefix="/api/v1", tags=["v1"])


@v1.get("/")
def v1_root():
    return {
        "service": "Healthcare Risk Prediction API",
        "version": "v1",
        "status": "running",
        "models": ["diabetes", "heart_disease", "lung_cancer"],
    }


@v1.get("/models")
def v1_model_registry():
    """Return model registry metadata (versions, metrics, status)."""
    import json
    registry_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "models", "model_registry.json",
    )
    with open(registry_path) as f:
        registry = json.load(f)
    # Return only safe metadata — strip sha256 hashes from public API
    summary = {}
    for name, meta in registry["models"].items():
        summary[name] = {
            "version": meta["version"],
            "algorithm": meta["algorithm"],
            "target": meta["target"],
            "status": meta["status"],
            "metrics": meta.get("metrics", {}),
        }
    return {"registry_version": registry["registry_version"], "models": summary}


@v1.post("/predict/diabetes", response_model=PredictionResponse)
def v1_predict_diabetes(data: PredictionRequest):
    """Predict diabetes risk (v1)."""
    result = predict(
        age_group=data.age, bmi=data.bmi, high_bp=data.bp,
        smoker=data.smoker, high_cholesterol=data.cholesterol,
        physical_activity=data.activity, general_health=data.health,
        mental_health=data.mental,
    )
    return PredictionResponse(**result)


@v1.post("/predict/heart", response_model=PredictionResponse)
def v1_predict_heart(data: HeartDiseasePredictionRequest):
    """Predict heart disease risk (v1)."""
    result = predict_heart_disease(
        age=data.age, sex=data.sex, bmi=data.bmi,
        high_bp=data.high_bp, high_chol=data.high_chol,
        smoker=data.smoker, phys_activity=data.phys_activity,
        fruits=data.fruits, veggies=data.veggies,
        heavy_drinker=data.heavy_drinker, gen_health=data.gen_health,
        ment_health=data.ment_health, phys_health=data.phys_health,
        diabetes=data.diabetes,
    )
    return PredictionResponse(**result)


@v1.post("/predict/lung", response_model=PredictionResponse)
def v1_predict_lung(data: LungCancerPredictionRequest):
    """Predict lung cancer risk (v1)."""
    result = predict_lung_cancer(
        age=data.age, gender=data.gender, smoking=data.smoking,
        yellow_fingers=data.yellow_fingers,
        chronic_disease=data.chronic_disease, fatigue=data.fatigue,
        wheezing=data.wheezing,
        shortness_of_breath=data.shortness_of_breath,
    )
    return PredictionResponse(**result)


# ══════════════════════════════════════════════════════════════════════════
#  SHAP Explanation Endpoints (v1 only)
# ══════════════════════════════════════════════════════════════════════════

@v1.post("/explain/diabetes")
def v1_explain_diabetes(data: PredictionRequest):
    """Return SHAP feature importances for a diabetes prediction."""
    df = build_diabetes_features(
        age_group=data.age, bmi=data.bmi, high_bp=data.bp,
        smoker=data.smoker, high_cholesterol=data.cholesterol,
        physical_activity=data.activity, general_health=data.health,
        mental_health=data.mental,
    )
    result = predict(
        age_group=data.age, bmi=data.bmi, high_bp=data.bp,
        smoker=data.smoker, high_cholesterol=data.cholesterol,
        physical_activity=data.activity, general_health=data.health,
        mental_health=data.mental,
    )
    shap_data = explain_diabetes(df)
    return {**result, "explanation": shap_data}


@v1.post("/explain/heart")
def v1_explain_heart(data: HeartDiseasePredictionRequest):
    """Return SHAP feature importances for a heart disease prediction."""
    import pandas as pd, numpy as np
    row = {
        "_AGEG5YR": float(data.age), "SEX": float(data.sex),
        "_BMI5": float(data.bmi),
        "_RFHYPE5": float(1 - data.high_bp), "_RFCHOL": float(1 - data.high_chol),
        "SMOKE100": float(data.smoker), "_TOTINDA": float(data.phys_activity),
        "_FRTLT1": float(data.fruits), "_VEGLT1": float(data.veggies),
        "_RFDRHV5": float(1 - data.heavy_drinker),
        "GENHLTH": float(data.gen_health), "MENTHLTH": float(data.ment_health),
        "PHYSHLTH": float(data.phys_health), "DIABETE3": float(data.diabetes),
    }
    from fastapi_backend.model_loader import _heart_features
    df = pd.DataFrame([row])[_heart_features].astype(np.float64)
    result = predict_heart_disease(
        age=data.age, sex=data.sex, bmi=data.bmi,
        high_bp=data.high_bp, high_chol=data.high_chol,
        smoker=data.smoker, phys_activity=data.phys_activity,
        fruits=data.fruits, veggies=data.veggies,
        heavy_drinker=data.heavy_drinker, gen_health=data.gen_health,
        ment_health=data.ment_health, phys_health=data.phys_health,
        diabetes=data.diabetes,
    )
    shap_data = explain_heart(df)
    return {**result, "explanation": shap_data}


@v1.post("/explain/lung")
def v1_explain_lung(data: LungCancerPredictionRequest):
    """Return SHAP feature importances for a lung cancer prediction."""
    import pandas as pd, numpy as np
    from fastapi_backend.model_loader import _lung_features, _lung_scaler
    row = {
        "Age": float(data.age), "Gender": float(data.gender),
        "Smoking": float(data.smoking), "Yellow Fingers": float(data.yellow_fingers),
        "Chronic Disease": float(data.chronic_disease),
        "Fatigue": float(data.fatigue), "Wheezing": float(data.wheezing),
        "Shortness of Breath": float(data.shortness_of_breath),
    }
    df = pd.DataFrame([row])[_lung_features].copy()
    df["Age"] = _lung_scaler.transform(df[["Age"]])
    df = df.astype(np.float64)
    result = predict_lung_cancer(
        age=data.age, gender=data.gender, smoking=data.smoking,
        yellow_fingers=data.yellow_fingers,
        chronic_disease=data.chronic_disease, fatigue=data.fatigue,
        wheezing=data.wheezing, shortness_of_breath=data.shortness_of_breath,
    )
    shap_data = explain_lung(df)
    return {**result, "explanation": shap_data}


# ── Mount v1 router (after all routes are defined) ────────────────────────
app.include_router(v1)
