"""
FastAPI Healthcare Risk Prediction — Unified App.

Serves the HTMX-based UI and prediction API endpoints.

Run locally:
    uvicorn backend.app.main:app --reload --port 8000
"""

import json
import os
import secrets
import uuid
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Depends, HTTPException, Cookie
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from redis import asyncio as aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

class OptionalRateLimiter:
    def __init__(self, times: int, seconds: int):
        self.limiter = RateLimiter(times=times, seconds=seconds)
    async def __call__(self, request: Request, response: Response):
        if hasattr(FastAPILimiter, "redis") and FastAPILimiter.redis is not None:
            try:
                await self.limiter(request, response)
            except Exception as exc:
                logger.warning("optional_rate_limiter_failed", error=str(exc))

from backend.app.api.dependencies import get_api_key
from backend.app.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    HeartDiseasePredictionRequest,
    LungCancerPredictionRequest,
)
from backend.app.services.model_loader import (
    load_models,
    predict,
    predict_heart_disease,
    predict_lung_cancer,
    build_diabetes_features,
)
from backend.app.services.shap_explainer import (
    load_explainers,
    explain_diabetes,
    explain_heart,
    explain_lung,
)
from backend.app.core.logging import setup_logging, get_logger
from backend.app.api.v1.routes.upload import router as upload_router
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Histogram

logger = get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = REPO_ROOT / "frontend" / "src"
TEMPLATE_DIR = FRONTEND_DIR / "pages" / "templates"
STATIC_DIR = FRONTEND_DIR / "assets"
REGISTRY_PATH = REPO_ROOT / "ml" / "registry" / "model_registry.json"

# ── Model Monitoring (Drift Detection) ─────────────────────────────────────
# Track the distribution of predicted probabilities to detect concept drift
PREDICTION_PROB_METRIC = Histogram(
    "model_prediction_probability",
    "Predicted risk probability distribution",
    ["model_name"],
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
)




RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models at startup."""
    setup_logging()
    logger.info("application_startup", version="3.0.0")
    
    # Initialize in-memory cache since we removed Redis database
    from fastapi_cache.backends.inmemory import InMemoryBackend
    FastAPICache.init(InMemoryBackend(), prefix="healthpredict-cache")
        
    app.state.models = {}
    asyncio.create_task(asyncio.to_thread(load_models, app))
    asyncio.create_task(asyncio.to_thread(load_explainers))
    logger.info("models_loading_in_background")
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
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

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


# Removed old request_id_middleware since SecurityHeadersMiddleware handles it.



def _clamp(value, lo, hi):
    """Clamp a numeric value to [lo, hi]."""
    return max(lo, min(hi, value))


def _gauge_offset(pct: float) -> float:
    """Calculate SVG gauge stroke-dashoffset from percentage."""
    return round(251.2 - 188.4 * pct / 100, 1)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI validation errors cleanly for HTMX clients."""
    if request.headers.get("hx-request") == "true":
        return templates.TemplateResponse("partials/error.html", {
            "request": request,
            "error": "Invalid input provided. Please check the form fields and try again."
        }, status_code=200)
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle general HTTP exceptions cleanly for HTMX clients."""
    if request.headers.get("hx-request") == "true":
        return templates.TemplateResponse("partials/error.html", {
            "request": request,
            "error": exc.detail
        }, status_code=200)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None)
    )


# ══════════════════════════════════════════════════════════════════════════
#  UI Pages
# ══════════════════════════════════════════════════════════════════════════

def _render_index(request: Request, initial_tab: str = "home"):
    """Render the main UI shell with the requested tab selected."""
    response = templates.TemplateResponse("index.html", {"request": request, "initial_tab": initial_tab})
    if "csrf_token" not in request.cookies:
        is_prod = os.environ.get("APP_ENV") == "production"
        response.set_cookie(key="csrf_token", value=secrets.token_hex(32), httponly=False, samesite="lax", secure=is_prod)
    return response


@app.get("/")
def index(request: Request):
    """Render the Home landing page."""
    return _render_index(request, "home")


@app.get("/about")
def about_page(request: Request):
    """Render the About page."""
    return _render_index(request, "about")


@app.get("/login")
def login_page(request: Request):
    """Render the Login page."""
    return _render_index(request, "login")


@app.get("/register")
def register_page(request: Request):
    """Render the Register page."""
    return _render_index(request, "register")


@app.get("/diabetes")
def diabetes_page(request: Request):
    """Render the Diabetes risk assessment page."""
    return _render_index(request, "diabetes")


@app.get("/heart-disease")
def heart_disease_page(request: Request):
    """Render the Heart Disease risk assessment page."""
    return _render_index(request, "heart")


@app.get("/lung-cancer")
def lung_cancer_page(request: Request):
    """Render the Lung Cancer risk assessment page."""
    return _render_index(request, "lung")

@app.get("/dashboard")
def dashboard_page(request: Request):
    return _render_index(request, "dashboard")

@app.get("/dashboard/uploads")
def dashboard_uploads_page(request: Request):
    return _render_index(request, "dashboard_uploads")

@app.get("/dashboard/history")
def dashboard_history_page(request: Request):
    return _render_index(request, "dashboard_history")

@app.get("/dashboard/sessions")
def dashboard_sessions_page(request: Request):
    return _render_index(request, "dashboard_sessions")

@app.get("/dashboard/profile")
def dashboard_profile_page(request: Request):
    return _render_index(request, "dashboard_profile")

def verify_csrf_token(request: Request, csrf_token: str = Cookie(default=None)):
    if not csrf_token:
        raise HTTPException(status_code=403, detail="CSRF token missing.")
    header_token = request.headers.get("X-CSRFToken")
    if not header_token or header_token != csrf_token:
        raise HTTPException(status_code=403, detail="CSRF token validation failed.")
    return csrf_token


@app.get("/healthz")
def healthz():
    """Liveness probe for Kubernetes / Docker."""
    return {"status": "healthy"}


@app.get("/api/v1/health/ready")
def readiness(request: Request):
    """Readiness probe — confirms models are loaded and app is ready."""
    models_loaded = request.app.state.models.get("diabetes_model") is not None
    if not models_loaded:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "models not loaded"},
        )
    return {"status": "ready"}


# ══════════════════════════════════════════════════════════════════════════
#  HTMX Prediction Endpoints (return HTML fragments)
# ══════════════════════════════════════════════════════════════════════════

@app.post("/predict/diabetes", dependencies=[Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60)), Depends(verify_csrf_token)])
@cache(expire=3600)
async def predict_diabetes_htmx(
    request: Request,
    age: float = Form(7),
    bmi: float = Form(25.0),
    bp: float = Form(0),
    cholesterol: float = Form(0),
    smoker: float = Form(0),
    activity: float = Form(1),
    health: float = Form(3),
    mental: float = Form(0)
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
        result = await predict(request=request,
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
        
        # Log to DB and Prometheus
        PREDICTION_PROB_METRIC.labels(model_name="diabetes").observe(pct / 100.0)

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


@app.post("/predict/heart", dependencies=[Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60)), Depends(verify_csrf_token)])
@cache(expire=3600)
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
    hd_diabetes: int = Form(0)
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
        result = await predict_heart_disease(request=request,
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

        # Log to DB and Prometheus
        PREDICTION_PROB_METRIC.labels(model_name="heart_disease").observe(pct / 100.0)

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


@app.post("/predict/lung", dependencies=[Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60)), Depends(verify_csrf_token)])
@cache(expire=3600)
async def predict_lung_htmx(
    request: Request,
    lc_age: int = Form(50),
    lc_gender: int = Form(1),
    lc_smoking: int = Form(0),
    lc_yellow_fingers: int = Form(0),
    lc_chronic_disease: int = Form(0),
    lc_fatigue: int = Form(0),
    lc_wheezing: int = Form(0),
    lc_shortness_of_breath: int = Form(0)
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
        result = await predict_lung_cancer(request=request,
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

        # Log to DB and Prometheus
        PREDICTION_PROB_METRIC.labels(model_name="lung_cancer").observe(pct / 100.0)

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


@app.post("/api/predict", response_model=PredictionResponse, dependencies=[Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60))])
async def api_predict_diabetes(request: Request, data: PredictionRequest):
    """Predict diabetes risk (JSON API)."""
    result = await predict(request=request,
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


@app.post("/api/predict-heart", response_model=PredictionResponse, dependencies=[Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60))])
async def api_predict_heart(request: Request, data: HeartDiseasePredictionRequest):
    """Predict heart disease risk (JSON API)."""
    result = await predict_heart_disease(request=request,
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


@app.post("/api/predict-lung", response_model=PredictionResponse, dependencies=[Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60))])
async def api_predict_lung(request: Request, data: LungCancerPredictionRequest):
    """Predict lung cancer risk (JSON API)."""
    result = await predict_lung_cancer(request=request,
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

v1 = APIRouter(prefix="/api/v1", tags=["v1"], dependencies=[Depends(get_api_key)])


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
    with open(REGISTRY_PATH) as f:
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
async def v1_predict_diabetes(request: Request, data: PredictionRequest):

    """Predict diabetes risk (v1)."""
    result = await predict(request=request,
        age_group=data.age, bmi=data.bmi, high_bp=data.bp,
        smoker=data.smoker, high_cholesterol=data.cholesterol,
        physical_activity=data.activity, general_health=data.health,
        mental_health=data.mental,
    )
    
    # Log to DB and Prometheus
    await log_prediction_to_db(db, request, "diabetes", data.model_dump(), result["risk_percentage"], result["risk_level"], "api_v1", None)
    PREDICTION_PROB_METRIC.labels(model_name="diabetes").observe(result["risk_percentage"] / 100.0)

    return PredictionResponse(**result)


@v1.post("/predict/heart", response_model=PredictionResponse)
async def v1_predict_heart(request: Request, data: HeartDiseasePredictionRequest):

    """Predict heart disease risk (v1)."""
    result = await predict_heart_disease(request=request,
        age=data.age, sex=data.sex, bmi=data.bmi,
        high_bp=data.high_bp, high_chol=data.high_chol,
        smoker=data.smoker, phys_activity=data.phys_activity,
        fruits=data.fruits, veggies=data.veggies,
        heavy_drinker=data.heavy_drinker, gen_health=data.gen_health,
        ment_health=data.ment_health, phys_health=data.phys_health,
        diabetes=data.diabetes,
    )
    
    # Log to DB and Prometheus
    await log_prediction_to_db(db, request, "heart_disease", data.model_dump(), result["risk_percentage"], result["risk_level"], "api_v1", None)
    PREDICTION_PROB_METRIC.labels(model_name="heart_disease").observe(result["risk_percentage"] / 100.0)

    return PredictionResponse(**result)


@v1.post("/predict/lung", response_model=PredictionResponse)
async def v1_predict_lung(request: Request, data: LungCancerPredictionRequest):

    """Predict lung cancer risk (v1)."""
    result = await predict_lung_cancer(request=request,
        age=data.age, gender=data.gender, smoking=data.smoking,
        yellow_fingers=data.yellow_fingers,
        chronic_disease=data.chronic_disease, fatigue=data.fatigue,
        wheezing=data.wheezing,
        shortness_of_breath=data.shortness_of_breath,
    )
    
    # Log to DB and Prometheus
    await log_prediction_to_db(db, request, "lung_cancer", data.model_dump(), result["risk_percentage"], result["risk_level"], "api_v1", None)
    PREDICTION_PROB_METRIC.labels(model_name="lung_cancer").observe(result["risk_percentage"] / 100.0)

    return PredictionResponse(**result)


# ══════════════════════════════════════════════════════════════════════════
#  SHAP Explanation Endpoints (v1 only)
# ══════════════════════════════════════════════════════════════════════════

@v1.post("/explain/diabetes")
async def v1_explain_diabetes(request: Request, data: PredictionRequest):
    """Return SHAP feature importances for a diabetes prediction."""
    df = build_diabetes_features(
        age_group=data.age, bmi=data.bmi, high_bp=data.bp,
        smoker=data.smoker, high_cholesterol=data.cholesterol,
        physical_activity=data.activity, general_health=data.health,
        mental_health=data.mental,
    )
    result = await predict(request=request,
        age_group=data.age, bmi=data.bmi, high_bp=data.bp,
        smoker=data.smoker, high_cholesterol=data.cholesterol,
        physical_activity=data.activity, general_health=data.health,
        mental_health=data.mental,
    )
    
    # Output logging (less rigorous for explanations, but good-to-have)
    await log_prediction_to_db(db, request, "diabetes", data.model_dump(), result["risk_percentage"], result["risk_level"], "api_v1_explain", None)

    shap_data = explain_diabetes(df)
    return {**result, "explanation": shap_data}


@v1.post("/explain/heart")
async def v1_explain_heart(request: Request, data: HeartDiseasePredictionRequest):
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
    f = request.app.state.models.get("heart_features")
    df = pd.DataFrame([row])[f].astype(np.float64)
    result = await predict_heart_disease(request=request,
        age=data.age, sex=data.sex, bmi=data.bmi,
        high_bp=data.high_bp, high_chol=data.high_chol,
        smoker=data.smoker, phys_activity=data.phys_activity,
        fruits=data.fruits, veggies=data.veggies,
        heavy_drinker=data.heavy_drinker, gen_health=data.gen_health,
        ment_health=data.ment_health, phys_health=data.phys_health,
        diabetes=data.diabetes,
    )
    
    # Output logging (less rigorous for explanations, but good-to-have)
    await log_prediction_to_db(db, request, "heart_disease", data.model_dump(), result["risk_percentage"], result["risk_level"], "api_v1_explain", None)

    shap_data = explain_heart(df)
    return {**result, "explanation": shap_data}


@v1.post("/explain/lung")
async def v1_explain_lung(request: Request, data: LungCancerPredictionRequest):
    """Return SHAP feature importances for a lung cancer prediction."""
    import pandas as pd, numpy as np
    row = {
        "Age": float(data.age), "Gender": float(data.gender),
        "Smoking": float(data.smoking), "Yellow Fingers": float(data.yellow_fingers),
        "Chronic Disease": float(data.chronic_disease),
        "Fatigue": float(data.fatigue), "Wheezing": float(data.wheezing),
        "Shortness of Breath": float(data.shortness_of_breath),
    }
    f = request.app.state.models.get("lung_features")
    s = request.app.state.models.get("lung_scaler")
    df = pd.DataFrame([row])[f].copy()
    df["Age"] = s.transform(df[["Age"]])
    df = df.astype(np.float64)
    result = await predict_lung_cancer(request=request,
        age=data.age, gender=data.gender, smoking=data.smoking,
        yellow_fingers=data.yellow_fingers,
        chronic_disease=data.chronic_disease, fatigue=data.fatigue,
        wheezing=data.wheezing, shortness_of_breath=data.shortness_of_breath,
    )
    
    # Output logging (less rigorous for explanations, but good-to-have)
    await log_prediction_to_db(db, request, "lung_cancer", data.model_dump(), result["risk_percentage"], result["risk_level"], "api_v1_explain", None)

    shap_data = explain_lung(df)
    return {**result, "explanation": shap_data}


# ── Mount v1 router (after all routes are defined) ────────────────────────
app.include_router(
    upload_router,
    prefix="/api/v1",
    dependencies=[
        Depends(verify_csrf_token),
        Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60))
    ]
)
app.include_router(v1)
