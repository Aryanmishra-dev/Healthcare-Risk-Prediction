<p align="center">
  <img src="frontend/src/assets/dr_ai_avatar_v2.png" alt="HealthPredict AI" width="160"/>
</p>

<h1 align="center">HealthPredict AI</h1>

<p align="center">
  <strong>Clinical risk prediction platform for Diabetes, Heart Disease, and Lung Cancer.</strong><br/>
  FastAPI backend · XGBoost models · SHAP explainability · MLOps observability
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="backend/requirements.txt"><img src="https://img.shields.io/badge/python-3.11-blue.svg" alt="Python 3.11"></a>
  <a href="Dockerfile"><img src="https://img.shields.io/badge/docker-ready-blue.svg" alt="Docker"></a>
  <a href="deployment/kubernetes/healthpredict"><img src="https://img.shields.io/badge/kubernetes-helm-blue.svg" alt="Kubernetes"></a>
  <a href="CODE_OF_CONDUCT.md"><img src="https://img.shields.io/badge/code%20of%20conduct-contributor%20covenant-ff69b4.svg" alt="Code of Conduct"></a>
</p>

> **Medical disclaimer:** HealthPredict AI provides educational decision support only. It is not a medical device, does not provide diagnoses, and must not replace professional clinical judgment. All API responses include this disclaimer.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Machine Learning](#machine-learning)
- [Operations](#operations)
- [Testing and Quality](#testing-and-quality)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)
- [Citation](#citation)

---

## Overview

HealthPredict AI is an end-to-end web platform that estimates patient risk for three conditions — **diabetes, heart disease, and lung cancer** — from structured clinical indicators.

It combines:

- A **FastAPI + HTMX web application** with server-rendered pages and a versioned JSON REST API (`/api/v1`)
- **XGBoost classifiers** with probability calibration and SHAP explanations
- **Clinical document ingestion** (PDF / image → OCR → entity extraction → form auto-fill)
- **Enterprise foundations**: JWT + API-key auth, multi-tenancy, audit logging, rate limiting, Prometheus/Grafana observability
- **Deployment targets**: Docker Compose, Kubernetes (Helm), Terraform (AWS), and Render

Interactive API documentation is served at `/docs` when the backend is running.

---

## Features

### Risk prediction

- Three calibrated XGBoost models: diabetes, heart disease, lung cancer
- Risk score (0–100), risk band (Low / Moderate / High), and model version in every response
- SHAP-based feature explanations for transparency

### Web application

- Server-rendered UI (HTMX + Jinja2) with diabetes, heart-disease, and lung-cancer assessment pages
- Authenticated dashboard: prediction history, uploads, sessions, and profile
- Document upload flow that extracts clinical entities and pre-fills assessment forms

### API platform

- Versioned REST API under `/api/v1`, protected by API key (`X-API-Key`)
- Prediction history, exports, reports, notifications, webhooks, and admin analytics endpoints
- Health endpoints for liveness (`/healthz`) and readiness (`/api/v1/health/ready`), plus Prometheus metrics at `/metrics`

### Security and compliance

- JWT access/refresh tokens with rotation, BCrypt password hashing, RBAC (`user`, `admin`, `super_admin`)
- API keys with tenant scoping, CSRF protection, CORS allow-listing, trusted-host enforcement, and per-minute rate limiting
- Immutable audit log for predictions and security events

### MLOps and observability

- MLflow experiment tracking and model registry, DVC pipelines for reproducibility
- Async model loading with health diagnostics and Prometheus model-monitoring metrics
- Grafana dashboards for system resources, prediction throughput, latency, and error rates

---

## Architecture

<p align="center">
  <img src="docs/images/architecture.png" alt="System architecture diagram" width="800"/>
  <br/><em>System architecture — Nginx edge, FastAPI application, ML/data infrastructure, and observability.</em>
</p>

```mermaid
flowchart TB
    User(["Client / Web Browser"])

    subgraph Edge ["Edge & Security (Nginx)"]
        NginxProxy["Nginx Reverse Proxy\n(SSL termination, headers, rate limiting)"]
    end

    subgraph AppServer ["Application (FastAPI)"]
        Router["Routing\n(HTMX UI & JSON REST API)"]
        AuthService["Auth & Sessions\n(JWT, sessions, users)"]
        NLPService["Document AI\n(PyMuPDF, Tesseract OCR, clinical NLP)"]
        ModelMgr["Model Manager\n(async loading, health checks)"]
        ExplainService["Explainability\n(SHAP values & plots)"]
    end

    subgraph DataML ["ML & Data"]
        MLflow["MLflow Registry\n(model artifacts)"]
        DVCStore["DVC\n(pipelines & data versioning)"]
        DB[(PostgreSQL\n(users, predictions, audit))]
        RedisCache[(Redis\n(rate limits & sessions))]
    end

    subgraph Mon ["Observability"]
        Prometheus["Prometheus\n(/metrics)"]
        Grafana["Grafana\n(dashboards)"]
    end

    User -->|"HTTPS (443)"| NginxProxy
    NginxProxy -->|"Internal proxy (8000)"| Router
    Router <--> AuthService
    Router --> NLPService
    Router --> ModelMgr
    ModelMgr --> ExplainService
    AuthService <--> DB
    ModelMgr <--> MLflow
    ModelMgr <--> DVCStore
    Router <--> RedisCache
    Router -.->|"scrapes"| Prometheus
    Prometheus --> Grafana
```

<p align="center">
  <img src="docs/images/system_flow.png" alt="Request lifecycle diagram" width="800"/>
  <br/><em>Request lifecycle.</em>
</p>

<p align="center">
  <img src="docs/images/ml_pipeline.png" alt="ML pipeline diagram" width="800"/>
  <br/><em>ML training and inference pipeline.</em>
</p>

<p align="center">
  <img src="docs/images/database.png" alt="Entity-relationship diagram" width="800"/>
  <br/><em>Entity-relationship diagram. See <a href="docs/architecture/er_diagram.md">docs/architecture/er_diagram.md</a> for the textual schema.</em>
</p>

---

## Project Structure

```
Healthcare-Risk-Prediction/
├── backend/                 # FastAPI app, schemas, services, Alembic migrations
│   ├── app/                 # main.py, api/v1/routes, auth, models, services
│   ├── migrations/          # Alembic migration history
│   ├── requirements.txt     # Runtime dependencies
│   └── requirements-dev.txt # Development dependencies
├── frontend/                # HTMX + Jinja2 templates, Tailwind CSS assets
├── ml/                      # Training pipelines, feature engineering, DVC, registry
│   ├── pipelines/           # Training, calibration, evaluation, inference
│   ├── models/              # Versioned model artifacts
│   └── dvc.yaml             # Reproducible ML pipelines
├── shared/                  # Shared utilities
├── config/                  # Application settings
├── deployment/
│   ├── docker/              # docker-compose.dev.yml, docker-compose.yml
│   ├── kubernetes/          # Helm chart (healthpredict)
│   ├── infrastructure/      # Terraform (AWS)
│   ├── nginx/               # Reverse-proxy configuration
│   └── render.yaml          # Render deployment
├── monitoring/              # Prometheus and Grafana configuration
├── tests/                   # Unit, integration, and e2e tests
├── scripts/                 # Operational and developer scripts
├── docs/                    # Architecture docs and diagrams
├── data/                    # Local data (interim SQLite fallback for development)
│
├── Dockerfile               # Multi-stage production image (Python 3.11)
├── docker-compose.yml       # Convenience alias for local dev services
├── pyproject.toml           # Pytest, coverage, Black, isort, Flake8 config
├── Makefile                 # Developer workflow targets
├── requirements.txt         # Root dependency pointer
├── requirements-dev.txt     # Root dev dependency pointer
├── .env.example             # Documented environment template
│
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── CHANGELOG.md
└── CITATION.cff
```

---

## Getting Started

### Prerequisites

- Python **3.11**
- Docker and Docker Compose
- Tesseract OCR (required for image-based document ingestion):
  - macOS: `brew install tesseract`
  - Debian/Ubuntu: `sudo apt-get install tesseract-ocr`

### 1. Clone and install

```bash
git clone https://github.com/theogengineer/Healthcare-Risk-Prediction.git
cd Healthcare-Risk-Prediction

python -m venv .venv
source .venv/bin/activate

# Development dependencies (see Makefile `install` target)
pip install --upgrade pip
pip install -r backend/requirements-dev.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

At minimum, review `API_KEY` / `DEV_API_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`, and `ALLOWED_ORIGINS` (see [Configuration](#configuration)).

### 3. Start infrastructure

```bash
# PostgreSQL + Redis only (app runs locally)
make docker-dev
```

### 4. Apply migrations and run

```bash
make db-migrate
make dev
```

Open <http://localhost:8000>. API docs are at <http://localhost:8000/docs>.

---

## Configuration

All settings are documented in `.env.example`. Common variables:

| Variable | Purpose | Default / Example |
|----------|---------|-------------------|
| `APP_ENV` | Runtime environment | `development` |
| `HOST` / `PORT` | Local server bind | `127.0.0.1` / `8000` |
| `API_KEY` | Required API key for `/api/v1` routes in production | _unset_ |
| `DEV_API_KEY` | Fallback API key for non-production | _unset_ |
| `JWT_SECRET_KEY` | JWT signing secret (≥32 characters) | _unset_ |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | Token lifetimes | `30` / `7` |
| `DATABASE_URL` | Primary database URL | `sqlite:///data/interim/audit_log.db` (dev fallback; PostgreSQL in production) |
| `REDIS_URL` | Redis URL for rate limiting and sessions | `redis://localhost:6379/0` |
| `ALLOWED_ORIGINS` | CORS allow-list | `http://localhost:3000,http://localhost:8000` |
| `TRUSTED_HOSTS` | Trusted Host header values | `localhost,127.0.0.1,testserver` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | `60` |
| `MODEL_DIR` / `MODEL_SOURCE` | Model artifact location and loading mode (`local` or `mlflow`) | `ml/models` / `local` |
| `MLFLOW_TRACKING_URI` | MLflow tracking server | `file://mlruns` |
| `VITE_API_URL` | Public backend URL used by the frontend build | _unset_ |

> Production deployments should use PostgreSQL (`asyncpg` + Alembic migrations), a strong `JWT_SECRET_KEY`, and a configured `API_KEY`. Do not commit `.env` to version control.

---

## API Reference

All `/api/v1` routes require an API key unless noted:

```
X-API-Key: <API_KEY or DEV_API_KEY>
```

Browser UI sessions use JWT access/refresh cookies issued by `/auth/*`.

### Health and metadata

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/healthz` | Public | Liveness check |
| `GET` | `/api/v1/health/ready` | Public | Readiness (models loaded) |
| `GET` | `/metrics` | Public | Prometheus metrics |
| `GET` | `/api/v1/` | API key | Service info and supported models |
| `GET` | `/api/v1/models` | API key | Model registry summary |
| `GET` | `/docs` | Public | Interactive OpenAPI docs |

### Predictions

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/predict/diabetes` | API key | Diabetes risk prediction |
| `POST` | `/api/v1/predict/heart` | API key | Heart disease risk prediction |
| `POST` | `/api/v1/predict/lung` | API key | Lung cancer risk prediction |
| `GET` | `/api/v1/predictions/history` | API key | Paginated prediction history |
| `GET` | `/api/v1/predictions/{prediction_id}/explanation` | API key | SHAP explanation for a prediction |

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/register` | Public | Register a new user |
| `POST` | `/auth/login` | Public | Authenticate and issue session cookies |
| `POST` | `/auth/refresh` | Refresh cookie | Rotate access token |
| `GET` | `/auth/me` | Session | Current user profile |

Additional resource routes (users, reports, notifications, exports, audit, webhooks, API keys, model registry, admin) are documented in OpenAPI at `/docs`.

### Example: diabetes prediction

Note: `age` is an ordinal age group (`1` = 18–24 … `13` = 80+), not years.

```bash
curl -X POST http://localhost:8000/api/v1/predict/diabetes \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $DEV_API_KEY" \
  -d '{
    "age": 8,
    "bmi": 32.0,
    "bp": 1,
    "cholesterol": 1,
    "smoker": 0,
    "activity": 0,
    "health": 3,
    "mental": 5
  }'
```

Response (shape):

```json
{
  "risk_percentage": 62.4,
  "risk_level": "High",
  "prediction": 1,
  "probability": 0.624,
  "model_name": "diabetes",
  "model_version": "v1",
  "disclaimer": "This prediction is educational decision support, not a diagnosis. Consult a qualified clinician for medical advice."
}
```

---

## Machine Learning

- **Data:** CDC BRFSS-style survey features for diabetes and heart disease; symptom-based features for lung cancer
- **Models:** XGBoost classifiers, served in-process via Joblib with async warmup
- **Calibration:** probability calibration for reliable risk percentages
- **Explainability:** SHAP values with per-prediction explanations and summary visualizations
- **Lifecycle:** MLflow tracking and registry, DVC versioned pipelines (`ml/dvc.yaml`), promotion/rollback/archival endpoints under `/api/v1/models`

Reproduce training pipelines with DVC (`ml/dvc.yaml`, `ml/dvc.lock`). Start a local MLflow UI with:

```bash
mlflow ui --host 127.0.0.1 --port 5000
```

---

## Operations

### Docker Compose

```bash
# Development: PostgreSQL + Redis only
docker compose -f deployment/docker/docker-compose.dev.yml up -d

# Production-like full stack: app + db + redis + nginx (+ optional monitoring)
docker compose -f deployment/docker/docker-compose.yml up -d --build

# Full stack with Prometheus + Grafana
docker compose -f deployment/docker/docker-compose.yml --profile monitoring up -d
```

The top-level `docker-compose.yml` is a convenience alias that starts local `db` and `redis` services.

### Kubernetes

```bash
helm lint deployment/kubernetes/healthpredict

helm upgrade --install healthpredict deployment/kubernetes/healthpredict \
  --namespace production --create-namespace \
  -f deployment/kubernetes/healthpredict/values.yaml
```

The chart provisions the Deployment, HPA, Service, Ingress, ConfigMap, Secret, and PVC resources.

### Other targets

- Terraform AWS infrastructure: `deployment/infrastructure/`
- Render single-service deployment: `deployment/render.yaml`
- Nginx reverse-proxy config: `deployment/nginx/`

### Monitoring

| Component | Default port |
|-----------|--------------|
| Prometheus | `9090` |
| Grafana | `3000` |

Dashboards cover request latency, error rates, prediction throughput, model health, and database-pool usage.

---

## Testing and Quality

```bash
make test      # Full test suite (SQLite, no external services required)
make coverage  # Tests with HTML + terminal coverage report (htmlcov/)
make lint      # black --check + isort --check-only + flake8
make format    # black + isort auto-formatting
make security  # bandit SAST + pip-audit
```

Test layout:

- `tests/unit/` — service and component tests
- `tests/integration/` — API and database integration tests
- `tests/e2e/` — end-to-end and load tests
- `tests/fixtures/` — shared test data

Coverage thresholds are configured in `pyproject.toml`.

---

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development setup and branch naming (`feat/`, `fix/`, `docs/`)
- Conventional Commits and pull-request requirements
- Code style (Black, isort, Flake8) and testing expectations

By participating, you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Security

Do not report vulnerabilities via public issues. See [SECURITY.md](SECURITY.md) for the disclosure process, supported versions, and response timelines.

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for the full text.

---

## Citation

If you use HealthPredict AI in research, please cite it using the metadata in [CITATION.cff](CITATION.cff):

```bibtex
@software{healthpredict2026,
  title = {{HealthPredict AI}: End-to-End Healthcare Risk Prediction Platform},
  version = {3.0.0},
  year = {2026},
  url = {https://github.com/theogengineer/Healthcare-Risk-Prediction}
}
```
