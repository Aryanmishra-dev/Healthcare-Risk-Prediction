# Healthcare Risk Prediction

Unified FastAPI application for predicting risk of diabetes, heart disease, and lung cancer from patient health indicators.

The project includes:

- HTMX-based web UI
- JSON APIs (legacy and versioned)
- SHAP explainability endpoints
- Document upload and clinical entity extraction pipeline
- Audit logging, rate limiting, CSRF checks, and Prometheus metrics

## Core Capabilities

- Multi-model prediction: diabetes, heart disease, lung cancer
- Versioned API under `/api/v1` with API key authentication
- Legacy JSON API under `/api/*` without API key requirement
- SHAP explanations for all three disease models
- Document ingestion endpoint at `/api/v1/document/upload` (PDF/JPG/JPEG/PNG, max 5 MB)
- Model loading from local `models/` or optional S3 bucket (`S3_MODEL_BUCKET`)

## Tech Stack

- Backend: FastAPI, Pydantic, SQLAlchemy
- ML: XGBoost, scikit-learn, SHAP
- Data: pandas, numpy
- Infra: Docker, Nginx, Kubernetes Helm, Terraform
- Monitoring: Prometheus and Grafana
- CI: GitHub Actions (lint, tests, security scans, Docker build)

## Local Development

### Prerequisites

- Python 3.12+
- macOS/Linux shell (examples below use bash/zsh)

### 1. Create and activate an isolated environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

### 2. Run the unified app

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

- UI: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- API root: [http://127.0.0.1:8000/api](http://127.0.0.1:8000/api)
- OpenAPI docs: [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)

Note: `start.sh` exists for an alternate local workflow and currently expects a local environment at `.venv-1`.

## API Overview

### Public endpoints (no API key)

- `GET /api`
- `POST /api/predict`
- `POST /api/predict-heart`
- `POST /api/predict-lung`
- `GET /healthz`
- `GET /api/v1/health/ready`

### Versioned endpoints (require `X-API-Key`)

- `GET /api/v1/`
- `GET /api/v1/models`
- `POST /api/v1/predict/diabetes`
- `POST /api/v1/predict/heart`
- `POST /api/v1/predict/lung`
- `POST /api/v1/explain/diabetes`
- `POST /api/v1/explain/heart`
- `POST /api/v1/explain/lung`

Development default API key fallback:

- If `API_KEY` is not set and `APP_ENV` is not `production`, the app accepts:
  - `X-API-Key: healthpredict_dev_key_2026`

### HTMX prediction endpoints (CSRF-protected)

- `POST /predict/diabetes`
- `POST /predict/heart`
- `POST /predict/lung`

These endpoints require:

- `csrf_token` cookie
- matching `X-CSRFToken` header

## Example Requests

### Legacy JSON prediction

```bash
curl -X POST "http://127.0.0.1:8000/api/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "age": 7,
    "bmi": 29.4,
    "bp": 1,
    "cholesterol": 1,
    "smoker": 0,
    "activity": 1,
    "health": 3,
    "mental": 2
  }'
```

### Versioned API prediction (with API key)

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/predict/diabetes" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: healthpredict_dev_key_2026" \
  -d '{
    "age": 7,
    "bmi": 29.4,
    "bp": 1,
    "cholesterol": 1,
    "smoker": 0,
    "activity": 1,
    "health": 3,
    "mental": 2
  }'
```

## Security and Quality Checks

Run locally from your active `.venv`:

```bash
python -m pytest -q
python -m bandit -r app fastapi_backend scripts utils -x tests,notebooks
python -m pip_audit -r requirements.txt
python -m pip_audit -r requirements-dev.txt
```

## CI Pipeline

The workflow at `.github/workflows/ci.yml` runs on every push and pull request:

- Lint job (flake8)
- Test job (Python 3.12 and 3.13, with coverage artifacts)
- Security job:
  - Bandit static scan
  - pip-audit for runtime dependencies
  - pip-audit for development dependencies
- Docker image build verification

## Configuration

Common environment variables:

- `APP_ENV` (`development` or `production`)
- `API_KEY` (required in production)
- `REDIS_URL` (default: `redis://localhost:6379/0`)
- `RATE_LIMIT_PER_MINUTE` (default: `60`)
- `CORS_ORIGINS` (comma-separated)
- `TRUSTED_HOSTS` (comma-separated)
- `DATABASE_URL` (Postgres URL, otherwise SQLite fallback)
- `S3_MODEL_BUCKET` (optional model source)

## Repository Layout

- `app/`: unified FastAPI app, templates, routes, services
- `fastapi_backend/`: model schemas/loaders and prediction logic
- `models/`: trained model artifacts and model registry
- `tests/`: API, integration, and infrastructure tests
- `scripts/`: retraining and MLOps helper scripts
- `.github/workflows/`: CI pipeline definitions

## Deployment Notes

- Docker files: `Dockerfile`, `docker-compose.yml`
- Nginx configs: `nginx/`
- Kubernetes chart: `kubernetes/healthpredict/`
- Terraform IaC: `infrastructure/`
