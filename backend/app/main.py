"""
FastAPI Healthcare Risk Prediction — Unified App.

Serves the HTMX-based UI and prediction API endpoints.

Run locally:
    uvicorn backend.app.main:app --reload --port 8000
"""

import asyncio
import json
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_cache import FastAPICache
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

from backend.app.api.dependencies import (
    RATE_LIMIT,
    OptionalRateLimiter,
    get_api_key,
)
from backend.app.api.v1.routes.admin import admin_router
from backend.app.api.v1.routes.api_keys import router as api_keys_router
from backend.app.api.v1.routes.audit import router as audit_router
from backend.app.api.v1.routes.exports import router as exports_router
from backend.app.api.v1.routes.health import router as health_router
from backend.app.api.v1.routes.models import router as models_router
from backend.app.api.v1.routes.notifications import (
    router as notifications_router,
)
from backend.app.api.v1.routes.predictions import router as predictions_router
from backend.app.api.v1.routes.reports import router as reports_router
from backend.app.api.v1.routes.security import router as security_router
from backend.app.api.v1.routes.upload import (
    process_uploaded_document,
)
from backend.app.api.v1.routes.upload import router as upload_router
from backend.app.api.v1.routes.users import router as users_router
from backend.app.api.v1.routes.webhooks import router as webhooks_router
from backend.app.auth.router import get_current_user
from backend.app.auth.router import router as auth_router
from backend.app.core.logging import get_logger, setup_logging
from backend.app.middleware.security_headers import SecurityHeadersMiddleware
from backend.app.middleware.timing import TimingMiddleware
from backend.app.schemas.prediction import (
    MEDICAL_DISCLAIMER,
    HeartDiseasePredictionRequest,
    LegacyDiabetesAuditRequest,
    LegacyHeartAuditRequest,
    LegacyLungCancerAuditRequest,
    LungCancerPredictionRequest,
    PredictionRequest,
    PredictionResponse,
)
from backend.app.services.audit_log import log_prediction_to_db
from backend.app.services.model_loader import (
    build_diabetes_features,
    predict,
    predict_heart_disease,
    predict_lung_cancer,
)
from backend.app.services.model_manager import model_manager
from backend.app.services.model_monitoring_service import (
    model_monitoring_service,
)
from backend.app.services.shap_explainer import (
    explain_diabetes,
    explain_heart,
    explain_lung,
    load_explainers,
)

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
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)


def _csv_env(name: str, default: str) -> list[str]:
    """Read a comma-separated env var into a trimmed list."""
    return [
        item.strip()
        for item in os.environ.get(name, default).split(",")
        if item.strip()
    ]


def _cors_origins(default: str) -> list[str]:
    """Prefer ALLOWED_ORIGINS while keeping CORS_ORIGINS backward
    compatible."""
    raw_origins = (
        os.environ.get("ALLOWED_ORIGINS")
        or os.environ.get("CORS_ORIGINS")
        or default
    )
    return [
        origin.strip() for origin in raw_origins.split(",") if origin.strip()
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models at startup."""
    setup_logging()
    logger.info("application_startup version=3.0.0")

    # Validate configuration before accepting any traffic (B7)
    from backend.app.api.dependencies import validate_startup_config

    validate_startup_config()

    # Initialize in-memory cache
    from fastapi_cache.backends.inmemory import InMemoryBackend

    FastAPICache.init(InMemoryBackend(), prefix="healthpredict-cache")

    app.state.models = {}

    # Load models before accepting requests so health and inference are ready.
    await model_manager.load_all_models()
    app.state.models.update(model_manager.export_app_state())
    # Load SHAP explainers synchronously (in a thread to avoid blocking).
    # This ensures explainers are ready before the first prediction request.
    await asyncio.to_thread(load_explainers)
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


@app.get("/docs", include_in_schema=False)
async def docs_alias():
    """Compatibility Swagger UI path expected by common health checks."""
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title="Healthcare Risk Prediction - Docs",
    )


@app.get("/openapi.json", include_in_schema=False)
async def openapi_alias():
    """Compatibility OpenAPI path expected by common health checks."""
    return JSONResponse(app.openapi())


# ── Templates & Static ────────────────────────────────────────────────────
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
templates.env.globals["BACKEND_URL"] = os.environ.get(
    "BACKEND_URL", "https://healthcare-risk-prediction.onrender.com"
)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── CORS ───────────────────────────────────────────────────────────────────
_IS_PROD = os.environ.get("APP_ENV") == "production"
if _IS_PROD:
    ALLOWED_ORIGINS = _cors_origins(
        "https://healthcare-risk-prediction.onrender.com",
    )
else:
    ALLOWED_ORIGINS = _cors_origins(
        "http://localhost:3000,http://localhost:8000,"
        "http://127.0.0.1:8000,"
        "https://healthcare-risk-prediction.onrender.com",
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "HX-Request",
        "HX-Trigger",
        "HX-Target",
        "HX-Current-URL",
        "X-CSRFToken",
    ],
    expose_headers=["X-CSRFToken"],
    allow_credentials="*" not in ALLOWED_ORIGINS,
)

# Add Timing Middleware for request timing and error logging
app.add_middleware(TimingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# ── Trusted Host middleware (reject spoofed Host headers) ─────────────
TRUSTED_HOSTS = _csv_env(
    "TRUSTED_HOSTS",
    "localhost,127.0.0.1,testserver,healthcare-risk-prediction.onrender.com",
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=TRUSTED_HOSTS,
)


@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    """Collect basic request metrics without a Starlette-pinned dependency."""
    if request.url.path == "/metrics":
        return await call_next(request)
    with HTTP_REQUEST_DURATION.labels(request.method, request.url.path).time():
        response = await call_next(request)
    HTTP_REQUESTS_TOTAL.labels(
        request.method, request.url.path, str(response.status_code)
    ).inc()
    return response


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Removed old request_id_middleware since SecurityHeadersMiddleware handles it.


def _clamp(value, lo, hi):
    """Clamp a numeric value to [lo, hi]."""
    return max(lo, min(hi, value))


def _gauge_offset(pct: float) -> float:
    """Calculate SVG gauge stroke-dashoffset from percentage."""
    return round(251.2 - 188.4 * pct / 100, 1)


def _age_to_group(age_years: float) -> float:
    """Map an age in years to the BRFSS 13-bucket age feature."""
    if age_years < 25:
        return 1.0
    if age_years >= 80:
        return 13.0
    return float(min(13, max(1, int((age_years - 25) // 5) + 2)))


def _prediction_payload(result: dict, model_name: str) -> dict:
    """Add launch-safe prediction metadata to a risk result."""
    probability = round(float(result["risk_percentage"]) / 100.0, 4)
    return {
        **result,
        "prediction": int(probability >= 0.5),
        "probability": probability,
        "model_name": model_name,
        "model_version": "local",
        "disclaimer": MEDICAL_DISCLAIMER,
    }


def _binary_from_legacy(value: int | float) -> int:
    """Map legacy 1/2 yes-no values to 0/1 while preserving 0/1 inputs."""
    return 1 if float(value) >= 2 else int(float(value) >= 1)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    """Handle FastAPI validation errors cleanly for HTMX clients."""
    if request.headers.get("hx-request") == "true":
        return templates.TemplateResponse(
            request,
            "partials/error.html",
            {
                "request": request,
                "error": "Invalid input provided. "
                "Please check the form fields and try again.",
            },
            status_code=200,
        )
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle general HTTP exceptions cleanly for HTMX clients."""
    if request.headers.get("hx-request") == "true":
        return templates.TemplateResponse(
            request,
            "partials/error.html",
            {"request": request, "error": exc.detail},
            status_code=200,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all 500 handler for unhandled exceptions."""
    logger.exception(
        "unhandled_exception",
        extra={"path": request.url.path, "method": request.method},
    )
    if request.headers.get("hx-request") == "true":
        return templates.TemplateResponse(
            request,
            "partials/error.html",
            {"request": request, "error": "An unexpected error occurred. Please try again."},
            status_code=500,
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ══════════════════════════════════════════════════════════════════════════
#  UI Pages
# ══════════════════════════════════════════════════════════════════════════


def _render_index(request: Request, initial_tab: str = "home"):
    """Render the main UI shell with the requested tab selected."""
    csrf_token = request.cookies.get("csrf_token") or secrets.token_hex(32)
    response = templates.TemplateResponse(
        request, "index.html", {"request": request, "initial_tab": initial_tab}
    )
    is_prod = os.environ.get("APP_ENV") == "production"
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        path="/",
        httponly=False,
        samesite="none" if is_prod else "lax",
        secure=is_prod,
    )
    response.headers["X-CSRFToken"] = csrf_token
    return response


@app.get("/")
def index(request: Request):
    """Render the Home landing page."""
    return _render_index(request, "home")


@app.get("/about")
def about_page(request: Request):
    """Render the About page."""
    return _render_index(request, "about")


@app.get("/how-it-works")
def how_it_works_page(request: Request):
    """Render the How It Works page."""
    return _render_index(request, "how-it-works")


@app.get("/contact")
def contact_page(request: Request):
    """Render the Contact page."""
    return _render_index(request, "contact")


@app.get("/model-cards")
def model_cards_page(request: Request):
    """Render the Model Cards page."""
    return _render_index(request, "model-cards")


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


def verify_csrf_token(
    request: Request, csrf_token: str = Cookie(default=None)
):
    if not csrf_token:
        raise HTTPException(status_code=403, detail="CSRF token missing.")
    header_token = request.headers.get("X-CSRFToken")
    if not header_token or header_token != csrf_token:
        raise HTTPException(
            status_code=403, detail="CSRF token validation failed."
        )
    return csrf_token


@app.get("/healthz")
def healthz():
    """Liveness probe for Kubernetes / Docker."""
    return {"status": "healthy"}


@app.get("/api/v1/health/ready")
def readiness(request: Request):
    """Readiness probe — confirms models are loaded and app is ready."""
    status = model_manager.get_health_status()
    models_ready = any(
        m["status"] == "ready" for m in status["models"].values()
    )
    if not models_ready:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "models not loaded"},
        )
    return {"status": "ready"}


# ══════════════════════════════════════════════════════════════════════════
#  HTMX Prediction Endpoints (return HTML fragments)
# ══════════════════════════════════════════════════════════════════════════


@app.post(
    "/predict/diabetes",
    dependencies=[
        Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60)),
        Depends(verify_csrf_token),
    ],
)
async def predict_diabetes_htmx(
    request: Request,
    current_user=Depends(get_current_user),
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
        result = await predict(
            request=request,
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
        await log_prediction_to_db(
            request,
            "diabetes",
            payload,
            pct,
            result["risk_level"],
            "htmx",
            str(current_user.id),
        )
        PREDICTION_PROB_METRIC.labels(model_name="diabetes").observe(
            pct / 100.0
        )

        return templates.TemplateResponse(
            request,
            "partials/diabetes_result.html",
            {
                "request": request,
                "result": result,
                "form": payload,
                "gauge_offset": _gauge_offset(pct),
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "partials/error.html",
            {
                "request": request,
                "error": str(e),
            },
        )


@app.post(
    "/predict/heart",
    dependencies=[
        Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60)),
        Depends(verify_csrf_token),
    ],
)
async def predict_heart_htmx(
    request: Request,
    current_user=Depends(get_current_user),
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
        result = await predict_heart_disease(
            request=request,
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
        await log_prediction_to_db(
            request,
            "heart_disease",
            payload,
            pct,
            result["risk_level"],
            "htmx",
            str(current_user.id),
        )
        PREDICTION_PROB_METRIC.labels(model_name="heart_disease").observe(
            pct / 100.0
        )

        return templates.TemplateResponse(
            request,
            "partials/heart_result.html",
            {
                "request": request,
                "result": result,
                "form": payload,
                "gauge_offset": _gauge_offset(pct),
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "partials/error.html",
            {
                "request": request,
                "error": str(e),
            },
        )


@app.post(
    "/predict/lung",
    dependencies=[
        Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60)),
        Depends(verify_csrf_token),
    ],
)
async def predict_lung_htmx(
    request: Request,
    current_user=Depends(get_current_user),
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
        result = await predict_lung_cancer(
            request=request,
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
        await log_prediction_to_db(
            request,
            "lung_cancer",
            payload,
            pct,
            result["risk_level"],
            "htmx",
            str(current_user.id),
        )
        PREDICTION_PROB_METRIC.labels(model_name="lung_cancer").observe(
            pct / 100.0
        )

        return templates.TemplateResponse(
            request,
            "partials/lung_result.html",
            {
                "request": request,
                "result": result,
                "form": payload,
                "gauge_offset": _gauge_offset(pct),
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "partials/error.html",
            {
                "request": request,
                "error": str(e),
            },
        )


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


@app.get("/api/dashboard")
async def api_dashboard(user=Depends(get_current_user)):
    """Protected dashboard summary used by auth smoke tests."""
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
        },
        "status": "ok",
    }


@app.post(
    "/api/predict",
    response_model=PredictionResponse,
    dependencies=[Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60))],
)
async def api_predict_diabetes(
    request: Request,
    data: PredictionRequest,
    current_user=Depends(get_current_user),
):
    """Predict diabetes risk (JSON API)."""
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
    await log_prediction_to_db(
        request,
        "diabetes",
        data.model_dump(),
        result["risk_percentage"],
        result["risk_level"],
        "api",
        str(current_user.id),
    )
    return PredictionResponse(**_prediction_payload(result, "diabetes"))


@app.post(
    "/api/predict-heart",
    response_model=PredictionResponse,
    dependencies=[Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60))],
)
async def api_predict_heart(
    request: Request,
    data: HeartDiseasePredictionRequest,
    current_user=Depends(get_current_user),
):
    """Predict heart disease risk (JSON API)."""
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
    await log_prediction_to_db(
        request,
        "heart_disease",
        data.model_dump(),
        result["risk_percentage"],
        result["risk_level"],
        "api",
        str(current_user.id),
    )
    return PredictionResponse(**_prediction_payload(result, "heart_disease"))


@app.post(
    "/api/predict-lung",
    response_model=PredictionResponse,
    dependencies=[Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60))],
)
async def api_predict_lung(
    request: Request,
    data: LungCancerPredictionRequest,
    current_user=Depends(get_current_user),
):
    """Predict lung cancer risk (JSON API)."""
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
    await log_prediction_to_db(
        request,
        "lung_cancer",
        data.model_dump(),
        result["risk_percentage"],
        result["risk_level"],
        "api",
        str(current_user.id),
    )
    return PredictionResponse(**_prediction_payload(result, "lung_cancer"))


@app.post(
    "/api/predict/diabetes",
    dependencies=[Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60))],
)
async def api_predict_diabetes_audit(
    request: Request,
    data: LegacyDiabetesAuditRequest,
    current_user=Depends(get_current_user),
):
    """Compatibility endpoint for the launch-audit diabetes payload."""
    payload = {
        "age": _age_to_group(data.age),
        "bmi": _clamp(float(data.bmi) or 10.0, 10.0, 80.0),
        "bp": (
            1.0 if data.blood_pressure >= 130 or data.glucose >= 180 else 0.0
        ),
        "cholesterol": 0.0,
        "smoker": 0.0,
        "activity": 1.0,
        "health": _clamp(
            1 + int(data.glucose >= 140) + int(data.bmi >= 30), 1, 5
        ),
        "mental": 0.0,
    }
    result = await predict(
        request=request,
        age_group=payload["age"],
        bmi=payload["bmi"],
        high_bp=payload["bp"],
        smoker=payload["smoker"],
        high_cholesterol=payload["cholesterol"],
        physical_activity=payload["activity"],
        general_health=payload["health"],
        mental_health=payload["mental"],
    )
    await log_prediction_to_db(
        request,
        "diabetes",
        data.model_dump(),
        result["risk_percentage"],
        result["risk_level"],
        "api_audit",
        str(current_user.id),
    )
    return _prediction_payload(result, "diabetes")


@app.post(
    "/api/predict/heart",
    dependencies=[Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60))],
)
async def api_predict_heart_audit(
    request: Request,
    data: LegacyHeartAuditRequest,
    current_user=Depends(get_current_user),
):
    """Compatibility endpoint for the launch-audit heart disease payload."""
    payload = {
        "age": _age_to_group(data.age),
        "sex": int(data.sex),
        "bmi": 27.0,
        "high_bp": int(data.trestbps >= 130),
        "high_chol": int(data.chol >= 240),
        "smoker": 0,
        "phys_activity": int(data.thalach >= 140),
        "fruits": 1,
        "veggies": 1,
        "heavy_drinker": 0,
        "gen_health": _clamp(
            2 + int(data.cp > 0) + int(data.exang == 1), 1, 5
        ),
        "ment_health": 0,
        "phys_health": _clamp(int(data.oldpeak * 5), 0, 30),
        "diabetes": int(data.fbs == 1),
    }
    result = await predict_heart_disease(request=request, **payload)
    await log_prediction_to_db(
        request,
        "heart_disease",
        data.model_dump(),
        result["risk_percentage"],
        result["risk_level"],
        "api_audit",
        str(current_user.id),
    )
    return _prediction_payload(result, "heart_disease")


@app.post(
    "/api/predict/cancer",
    dependencies=[Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60))],
)
@app.post(
    "/api/predict/lung",
    dependencies=[Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60))],
)
async def api_predict_lung_audit(
    request: Request,
    data: LegacyLungCancerAuditRequest,
    current_user=Depends(get_current_user),
):
    """Compatibility endpoint for the launch-audit lung cancer payload."""
    payload = {
        "age": _clamp(int(data.age), 18, 100),
        "gender": int(data.gender >= 1),
        "smoking": _binary_from_legacy(data.smoking),
        "yellow_fingers": _binary_from_legacy(data.yellow_fingers),
        "chronic_disease": _binary_from_legacy(data.chronic_disease),
        "fatigue": _binary_from_legacy(data.fatigue),
        "wheezing": _binary_from_legacy(data.wheezing),
        "shortness_of_breath": _binary_from_legacy(data.shortness_of_breath),
    }
    result = await predict_lung_cancer(request=request, **payload)
    await log_prediction_to_db(
        request,
        "lung_cancer",
        data.model_dump(),
        result["risk_percentage"],
        result["risk_level"],
        "api_audit",
        str(current_user.id),
    )
    return _prediction_payload(result, "lung_cancer")


@app.post(
    "/api/upload",
    dependencies=[Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60))],
)
async def api_upload_alias(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """Compatibility upload endpoint used by the audit workflow."""
    try:
        return await process_uploaded_document(file)
    except HTTPException as exc:
        if exc.status_code == 400 and "too large" in str(exc.detail).lower():
            raise HTTPException(status_code=413, detail=exc.detail) from exc
        raise


# ══════════════════════════════════════════════════════════════════════════
#  Versioned API — /api/v1/
# ══════════════════════════════════════════════════════════════════════════

v1 = APIRouter(
    prefix="/api/v1", tags=["v1"], dependencies=[Depends(get_api_key)]
)
v1.include_router(users_router)
v1.include_router(predictions_router)
v1.include_router(reports_router)
v1.include_router(notifications_router)
v1.include_router(security_router)
v1.include_router(exports_router)
v1.include_router(models_router)
v1.include_router(audit_router)
v1.include_router(api_keys_router)
v1.include_router(webhooks_router)
v1.include_router(admin_router)


@v1.get("/")
def v1_root():
    return {
        "service": "Healthcare Risk Prediction API",
        "version": "v1",
        "status": "running",
        "models": ["diabetes", "heart_disease", "lung_cancer"],
    }


@v1.get("/models")
async def v1_model_registry():
    """Return model registry metadata (versions, metrics, status)."""

    # B8: Use asyncio.to_thread for non-blocking file read
    def _read_registry() -> dict:
        with open(REGISTRY_PATH) as f:
            return json.load(f)

    try:
        registry = await asyncio.to_thread(_read_registry)
    except FileNotFoundError:
        return {"registry_version": "unknown", "models": {}}
    except Exception as exc:
        logger.error("registry_read_failed | error=%s", exc)
        return {"registry_version": "error", "models": {}}

    # Return only safe metadata — strip sha256 hashes from public API
    summary = {}
    for name, meta in registry.get("models", {}).items():
        summary[name] = {
            "version": meta["version"],
            "algorithm": meta["algorithm"],
            "target": meta["target"],
            "status": meta["status"],
            "metrics": meta.get("metrics", {}),
        }
    return {
        "registry_version": registry.get("registry_version", "unknown"),
        "models": summary,
    }


@v1.post("/predict/diabetes", response_model=PredictionResponse)
async def v1_predict_diabetes(request: Request, data: PredictionRequest):
    """Predict diabetes risk (v1) — fully instrumented."""
    import time as _time

    _start = _time.time()
    success = True
    try:
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
        # SHAP explanation
        df = build_diabetes_features(
            data.age,
            data.bmi,
            data.bp,
            data.smoker,
            data.cholesterol,
            data.activity,
            data.health,
            data.mental,
        )
        shap_data = explain_diabetes(df)
    except Exception:
        success = False
        raise
    finally:
        latency_ms = int((_time.time() - _start) * 1000)
        model_monitoring_service.record_prediction(
            "diabetes", latency_ms, success
        )

    await log_prediction_to_db(
        request,
        "diabetes",
        data.model_dump(),
        result["risk_percentage"],
        result["risk_level"],
        "api_v1",
        None,
        shap_values=shap_data,
        processing_time_ms=latency_ms,
    )
    PREDICTION_PROB_METRIC.labels(model_name="diabetes").observe(
        result["risk_percentage"] / 100.0
    )
    payload = _prediction_payload(result, "diabetes")
    payload["explanation"] = shap_data
    return PredictionResponse(
        **{
            k: v
            for k, v in payload.items()
            if k in PredictionResponse.model_fields
        }
    )


@v1.post("/predict/heart", response_model=PredictionResponse)
async def v1_predict_heart(
    request: Request, data: HeartDiseasePredictionRequest
):
    """Predict heart disease risk (v1) — fully instrumented."""
    import time as _time

    import numpy as np
    import pandas as pd  # type: ignore[import-untyped]

    _start = _time.time()
    success = True
    try:
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
        row = {
            "_AGEG5YR": float(data.age),
            "SEX": float(data.sex),
            "_BMI5": float(data.bmi),
            "_RFHYPE5": float(1 - data.high_bp),
            "_RFCHOL": float(1 - data.high_chol),
            "SMOKE100": float(data.smoker),
            "_TOTINDA": float(data.phys_activity),
            "_FRTLT1": float(data.fruits),
            "_VEGLT1": float(data.veggies),
            "_RFDRHV5": float(1 - data.heavy_drinker),
            "GENHLTH": float(data.gen_health),
            "MENTHLTH": float(data.ment_health),
            "PHYSHLTH": float(data.phys_health),
            "DIABETE3": float(data.diabetes),
        }
        f = request.app.state.models.get("heart_features") or list(row.keys())
        df = pd.DataFrame([row])[f].astype(np.float64)
        shap_data = explain_heart(df)
    except Exception:
        success = False
        raise
    finally:
        latency_ms = int((_time.time() - _start) * 1000)
        model_monitoring_service.record_prediction(
            "heart_disease", latency_ms, success
        )

    await log_prediction_to_db(
        request,
        "heart_disease",
        data.model_dump(),
        result["risk_percentage"],
        result["risk_level"],
        "api_v1",
        None,
        shap_values=shap_data,
        processing_time_ms=latency_ms,
    )
    PREDICTION_PROB_METRIC.labels(model_name="heart_disease").observe(
        result["risk_percentage"] / 100.0
    )
    payload = _prediction_payload(result, "heart_disease")
    payload["explanation"] = shap_data
    return PredictionResponse(
        **{
            k: v
            for k, v in payload.items()
            if k in PredictionResponse.model_fields
        }
    )


@v1.post("/predict/lung", response_model=PredictionResponse)
async def v1_predict_lung(request: Request, data: LungCancerPredictionRequest):
    """Predict lung cancer risk (v1) — fully instrumented."""
    import time as _time

    import numpy as np
    import pandas as pd

    _start = _time.time()
    success = True
    try:
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
        row = {
            "Age": float(data.age),
            "Gender": float(data.gender),
            "Smoking": float(data.smoking),
            "Yellow Fingers": float(data.yellow_fingers),
            "Chronic Disease": float(data.chronic_disease),
            "Fatigue": float(data.fatigue),
            "Wheezing": float(data.wheezing),
            "Shortness of Breath": float(data.shortness_of_breath),
        }
        f = request.app.state.models.get("lung_features") or list(row.keys())
        s = request.app.state.models.get("lung_scaler")
        df = pd.DataFrame([row])[f].copy()
        if s is not None and "Age" in df:
            df["Age"] = s.transform(df[["Age"]])
        df = df.astype(np.float64)
        shap_data = explain_lung(df)
    except Exception:
        success = False
        raise
    finally:
        latency_ms = int((_time.time() - _start) * 1000)
        model_monitoring_service.record_prediction(
            "lung_cancer", latency_ms, success
        )

    await log_prediction_to_db(
        request,
        "lung_cancer",
        data.model_dump(),
        result["risk_percentage"],
        result["risk_level"],
        "api_v1",
        None,
        shap_values=shap_data,
        processing_time_ms=latency_ms,
    )
    PREDICTION_PROB_METRIC.labels(model_name="lung_cancer").observe(
        result["risk_percentage"] / 100.0
    )
    payload = _prediction_payload(result, "lung_cancer")
    payload["explanation"] = shap_data
    return PredictionResponse(
        **{
            k: v
            for k, v in payload.items()
            if k in PredictionResponse.model_fields
        }
    )


# ══════════════════════════════════════════════════════════════════════════
#  SHAP Explanation Endpoints (v1 only)
# ══════════════════════════════════════════════════════════════════════════


@v1.post("/explain/diabetes")
async def v1_explain_diabetes(request: Request, data: PredictionRequest):
    """Return SHAP feature importances for a diabetes prediction."""
    df = build_diabetes_features(
        age_group=data.age,
        bmi=data.bmi,
        high_bp=data.bp,
        smoker=data.smoker,
        high_cholesterol=data.cholesterol,
        physical_activity=data.activity,
        general_health=data.health,
        mental_health=data.mental,
    )
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

    # Output logging (less rigorous for explanations, but good-to-have)
    await log_prediction_to_db(
        request,
        "diabetes",
        data.model_dump(),
        result["risk_percentage"],
        result["risk_level"],
        "api_v1_explain",
        None,
    )

    shap_data = explain_diabetes(df)
    return {**result, "explanation": shap_data}


@v1.post("/explain/heart")
async def v1_explain_heart(
    request: Request, data: HeartDiseasePredictionRequest
):
    """Return SHAP feature importances for a heart disease prediction."""
    import numpy as np
    import pandas as pd

    row = {
        "_AGEG5YR": float(data.age),
        "SEX": float(data.sex),
        "_BMI5": float(data.bmi),
        "_RFHYPE5": float(1 - data.high_bp),
        "_RFCHOL": float(1 - data.high_chol),
        "SMOKE100": float(data.smoker),
        "_TOTINDA": float(data.phys_activity),
        "_FRTLT1": float(data.fruits),
        "_VEGLT1": float(data.veggies),
        "_RFDRHV5": float(1 - data.heavy_drinker),
        "GENHLTH": float(data.gen_health),
        "MENTHLTH": float(data.ment_health),
        "PHYSHLTH": float(data.phys_health),
        "DIABETE3": float(data.diabetes),
    }
    f = request.app.state.models.get("heart_features") or list(row.keys())
    df = pd.DataFrame([row])[f].astype(np.float64)
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

    # Output logging (less rigorous for explanations, but good-to-have)
    await log_prediction_to_db(
        request,
        "heart_disease",
        data.model_dump(),
        result["risk_percentage"],
        result["risk_level"],
        "api_v1_explain",
        None,
    )

    shap_data = explain_heart(df)
    return {**result, "explanation": shap_data}


@v1.post("/explain/lung")
async def v1_explain_lung(request: Request, data: LungCancerPredictionRequest):
    """Return SHAP feature importances for a lung cancer prediction."""
    import numpy as np
    import pandas as pd

    row = {
        "Age": float(data.age),
        "Gender": float(data.gender),
        "Smoking": float(data.smoking),
        "Yellow Fingers": float(data.yellow_fingers),
        "Chronic Disease": float(data.chronic_disease),
        "Fatigue": float(data.fatigue),
        "Wheezing": float(data.wheezing),
        "Shortness of Breath": float(data.shortness_of_breath),
    }
    f = request.app.state.models.get("lung_features") or list(row.keys())
    s = request.app.state.models.get("lung_scaler")
    df = pd.DataFrame([row])[f].copy()
    if s is not None and "Age" in df:
        df["Age"] = s.transform(df[["Age"]])
    df = df.astype(np.float64)
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

    # Output logging (less rigorous for explanations, but good-to-have)
    await log_prediction_to_db(
        request,
        "lung_cancer",
        data.model_dump(),
        result["risk_percentage"],
        result["risk_level"],
        "api_v1_explain",
        None,
    )

    shap_data = explain_lung(df)
    return {**result, "explanation": shap_data}


# ── Mount v1 router (after all routes are defined) ────────────────────────
app.include_router(
    upload_router,
    prefix="/api/v1",
    dependencies=[
        Depends(get_api_key),
        Depends(verify_csrf_token),
        Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60)),
    ],
)
app.include_router(v1)
app.include_router(auth_router)
app.include_router(health_router)
