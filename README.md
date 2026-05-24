# Healthcare Risk Prediction

## Project Overview

An end-to-end Machine Learning, Web, and MLOps ecosystem to predict the risk of diabetes, heart disease, and lung cancer from patient health indicators.

##  What We've Accomplished So Far

This project has evolved from basic machine learning notebooks to a robust, production-ready system. Here is a summary of our progress:

### 1. Advanced Machine Learning Pipeline & Fairness
- **Multi-Model Inference:** Successfully trained, optimized, and deployed models for predicting **Diabetes**, **Heart Disease**, and **Lung Cancer** risks.
- **Model Explainability:** Integrated **SHAP** (SHapley Additive exPlanations) values to interpret model predictions for users, providing essential transparency.
- **Fairness & Calibration:** Applied advanced evaluation techniques, including algorithmic fairness evaluations (`fairness_eval.py`) and model calibration (`calibrate_lung_model.py`) to reduce inherent bias.
- **MLOps Integration:** Implemented continuous integration (CI) pipelines, **MLflow** for experiment tracking, and **DVC** for data & model version control.

### 2. Full-Stack Web Application (FastAPI & HTMX)
- Built a unified **FastAPI** backend supporting both structured JSON APIs (`/api/v1`) and an interactive server-rendered Web UI.
- Developed a dynamic front-end using **HTMX**, delivering a seamless single-page app-like experience.
- Implemented **A/B Testing** capabilities (`backend/app/services/ab_testing.py`) to systematically deploy, compare UI variants, and measure user engagement.

### 3. NLP & AI Integrations
- **Medical Document Parser:** Created a seamless document ingestion pipeline (handling PDFs and Images) using Natural Language Processing (NLP) to extract clinical entities automatically.
- **AI Risk Assistant:** Integrated an LLM-powered chatbot to interactively help users understand their health metrics, risk factors, and overall predictions.

### 4. Enterprise-Grade Security & Monitoring
- **Robust Security:** Integrated API keys, CSRF protection, Audit Logging, and Rate Limiting. Established security workflows covering `bandit` (SAST) and `pip-audit` for dependency vulnerabilities.
- **Infrastructure & Deployment:** Fully containerized via **Docker** & **Docker Compose**. Created **Terraform** configuration for cloud infrastructure and **Kubernetes** Helm charts for orchestrated deployment.
- **Observability:** Added full telemetry support with **Prometheus** metrics and customized **Grafana** dashboards for live monitoring.

---

##  Tech Stack

- **Backend:** Python 3.12+, FastAPI, Pydantic, SQLAlchemy
- **Machine Learning:** XGBoost, scikit-learn, SHAP, Python, pandas
- **Frontend / NLP:** HTMX, Medical NLP parsing, Contextual Chatbot
- **DevOps & Infra:** Docker, Nginx, Kubernetes, Terraform, MLflow, DVC
- **Monitoring:** Prometheus, Grafana

---

## Setup Instructions

```bash
git clone <repo-url>
cd healthcare_risk_prediction
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements-dev.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:
- **Web UI:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **API Root:** [http://127.0.0.1:8000/api](http://127.0.0.1:8000/api)
- **API Docs (Swagger):** [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)

---

## Model Results

| Model | Dataset | Accuracy | AUC | F1 |
| --- | --- | ---: | ---: | ---: |
| XGBoost | Diabetes | 0.8467 | 0.8452 | 0.2995 |
| XGBoost | Heart Disease | 0.8955 | 0.7983 | 0.3429 |
| Calibrated Classifier | Lung Cancer | 0.7544 | 0.8378 | 0.7735 |

---

##  Local Development Quickstart

### Prerequisites
- Python 3.12+
- macOS/Linux shell (examples below use bash/zsh)
- (Optional) Docker & docker-compose

### 1. Setup Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements-dev.txt
```

### 2. Run the Unified Application
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open:
- **Web UI:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **API Root:** [http://127.0.0.1:8000/api](http://127.0.0.1:8000/api)
- **API Docs (Swagger):** [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)

*(Note: `deployment/scripts/start.sh` or `docker compose -f deployment/docker/docker-compose.yml up` are also available as alternate workflows).*

---

##  API Overview

### Versioned Endpoints (Requires `X-API-Key`)
*Base URL: `/api/v1`*
- `GET /` - API version info
- `GET /models` - List available models
- `POST /predict/{disease}` - Inference for Diabetes, Heart Disease, or Lung Cancer
- `POST /explain/{disease}` - SHAP Explanations
- `POST /document/upload` - Clinical feature extraction pipeline

*Development API Key:* Set `DEV_API_KEY` locally and pass that value as `X-API-Key` when `API_KEY` is not set.

### Public/Legacy Endpoints (No API key needed)
- `POST /api/predict`
- `GET /healthz`
- HTMX prediction endpoints: `POST /predict/{disease}` (Requires CSRF tokens)

---

##  Security & Quality Checks

Run local checks in your active `.venv`:
```bash
pytest tests/
python -m pytest -q
python -m bandit -r backend/app ml shared -x tests,ml/experiments
python -m pip_audit -r backend/requirements.txt
python -m pip_audit -r backend/requirements-dev.txt
```

---

## Reproduce Results With DVC

```bash
python -m pip install -r ml/requirements-dvc.txt
dvc repro ml/dvc.yaml
dvc status ml/dvc.yaml
```

`ml/dvc.yaml` regenerates the deterministic local stub model artifacts used for
launch smoke tests and CI. Full retraining requires the raw datasets and a real
DVC remote; configure one with `dvc remote add -d <name> <url>` before using
`dvc pull` for production-scale data or model artifacts.

---

## Project Structure

```text
.
├── .dockerignore
├── .env
├── .gitignore
├── README.md
├── backend
│   ├── Dockerfile.backend
│   ├── __init__.py
│   ├── app
│   │   ├── __init__.py
│   │   ├── api
│   │   │   ├── __init__.py
│   │   │   ├── dependencies.py
│   │   │   ├── legacy_main.py
│   │   │   └── v1
│   │   │       ├── __init__.py
│   │   │       └── routes
│   │   │           ├── __init__.py
│   │   │           └── upload.py
│   │   ├── core
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   └── security.py
│   │   ├── main.py
│   │   ├── middleware
│   │   │   └── __init__.py
│   │   ├── schemas
│   │   │   ├── __init__.py
│   │   │   └── prediction.py
│   │   ├── services
│   │   │   ├── __init__.py
│   │   │   ├── ab_testing.py
│   │   │   ├── document_parser.py
│   │   │   ├── feature_mapper.py
│   │   │   ├── medical_nlp.py
│   │   │   ├── model_loader.py
│   │   │   └── shap_explainer.py
│   │   └── utils
│   │       ├── __init__.py
│   │       └── file_validation.py
│   ├── requirements-dev.txt
│   └── requirements.txt
├── config
│   ├── .env.development
│   ├── .env.example
│   ├── .env.production
│   ├── .env.staging
│   ├── __init__.py
│   ├── feature_flags.yaml
│   └── settings.py
├── data
│   ├── external
│   │   └── .gitkeep
│   ├── interim
│   │   ├── .gitkeep
│   │   ├── audit_log.db
│   │   ├── audit_log.db-shm
│   │   └── audit_log.db-wal
│   ├── processed
│   │   └── .gitkeep
│   ├── raw
│   │   └── .gitkeep
│   └── schemas
│       └── .gitkeep
├── deployment
│   ├── ci
│   │   └── .github
│   │       └── workflows
│   │           └── ci.yml
│   ├── docker
│   │   └── docker-compose.yml
│   ├── infrastructure
│   │   ├── main.tf
│   │   ├── outputs.tf
│   │   └── variables.tf
│   ├── kubernetes
│   │   └── healthpredict
│   │       ├── Chart.yaml
│   │       ├── templates
│   │       │   ├── _helpers.tpl
│   │       │   ├── configmap.yaml
│   │       │   ├── deployment.yaml
│   │       │   ├── hpa.yaml
│   │       │   ├── secret.yaml
│   │       │   └── service.yaml
│   │       └── values.yaml
│   ├── nginx
│   │   ├── nginx.conf
│   │   ├── nginx.dev.conf
│   │   └── ssl
│   │       └── README.md
│   └── scripts
│       ├── deploy.sh
│       ├── reorganize.sh
│       └── start.sh
├── docs
│   ├── .env.example
│   ├── CHANGELOG.md
│   ├── CONTRIBUTING.md
│   ├── SECURITY.md
│   ├── api
│   │   └── .gitkeep
│   ├── architecture
│   │   └── adr
│   │       ├── 0001-use-fastapi-for-backend.md
│   │       ├── 0002-use-htmx-for-frontend.md
│   │       └── 0003-use-dvc-for-model-versioning.md
│   ├── ml
│   │   └── model_cards
│   │       ├── diabetes_model.md
│   │       ├── heart_disease_model.md
│   │       └── lung_cancer_model.md
│   └── runbooks
│       └── .gitkeep
├── frontend
│   ├── Dockerfile.frontend
│   ├── package.json
│   ├── public
│   │   └── .gitkeep
│   └── src
│       ├── assets
│       │   └── dr_ai_avatar_v2.png
│       ├── components
│       │   ├── common
│       │   │   └── .gitkeep
│       │   ├── features
│       │   │   └── .gitkeep
│       │   └── layout
│       │       └── .gitkeep
│       ├── hooks
│       │   └── .gitkeep
│       ├── pages
│       │   └── templates
│       │       ├── base.html
│       │       ├── index.html
│       │       └── partials
│       │           ├── about.html
│       │           ├── dashboard_history.html
│       │           ├── dashboard_profile.html
│       │           ├── dashboard_sessions.html
│       │           ├── dashboard_uploads.html
│       │           ├── diabetes_empty.html
│       │           ├── diabetes_form.html
│       │           ├── diabetes_result.html
│       │           ├── error.html
│       │           ├── heart_empty.html
│       │           ├── heart_form.html
│       │           ├── heart_result.html
│       │           ├── home.html
│       │           ├── lung_empty.html
│       │           ├── lung_form.html
│       │           ├── lung_result.html
│       │           └── upload_widget.html
│       ├── services
│       │   └── .gitkeep
│       ├── store
│       │   └── .gitkeep
│       ├── styles
│       │   └── style.css
│       └── utils
│           └── .gitkeep
├── generate_tree.py
├── ml
│   ├── __init__.py
│   ├── dvc.yaml
│   ├── experiments
│   │   ├── __init__.py
│   │   └── brfss_cleaning.ipynb
│   ├── feature_engineering
│   │   ├── __init__.py
│   │   ├── feature_store
│   │   │   └── __init__.py
│   │   └── transformers
│   │       └── __init__.py
│   ├── models
│   │   ├── .gitkeep
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── diabetes_xgboost.pkl
│   │   ├── generate_stubs.py
│   │   ├── heart_disease_calibrator.pkl
│   │   ├── heart_disease_features.pkl
│   │   ├── heart_disease_xgboost.pkl
│   │   ├── isotonic_calibrator.pkl
│   │   ├── lung_cancer_calibrator.pkl
│   │   ├── lung_cancer_features.pkl
│   │   ├── lung_cancer_model.pkl
│   │   ├── lung_cancer_scaler.pkl
│   │   └── stubs.py
│   ├── pipelines
│   │   ├── __init__.py
│   │   ├── evaluation
│   │   │   ├── __init__.py
│   │   │   ├── evaluate.py
│   │   │   ├── fairness_eval.py
│   │   │   └── results
│   │   │       ├── .gitkeep
│   │   │       └── __init__.py
│   │   ├── inference
│   │   │   ├── __init__.py
│   │   │   └── risk_assistant.py
│   │   └── training
│   │       ├── __init__.py
│   │       ├── calibrate_lung_model.py
│   │       ├── optuna_optimize.py
│   │       ├── train.py
│   │       ├── train_heart_disease_model.py
│   │       └── train_lung_cancer_model.py
│   ├── preprocessing
│   │   └── __init__.py
│   └── registry
│       ├── __init__.py
│       ├── mlflow_config.py
│       ├── model_registry.json
│       ├── model_registry.py
│       └── upload_models_to_s3.py
├── monitoring
│   ├── alerts
│   │   └── .gitkeep
│   ├── dashboards
│   │   ├── grafana_dashboard.json
│   │   └── provisioning
│   │       ├── dashboards
│   │       │   └── dashboard.yml
│   │       └── datasources
│   │           └── prometheus.yml
│   ├── logging
│   │   └── .gitkeep
│   └── metrics
│       └── prometheus.yml
├── pyproject.toml
├── requirements.txt
├── scripts
│   ├── browser_test.py
│   ├── cookies.txt
│   ├── patch_index.py
│   ├── patch_main.py
│   └── patch_upload.py
├── shared
│   ├── __init__.py
│   ├── constants
│   │   ├── .gitkeep
│   │   └── __init__.py
│   ├── types
│   │   ├── .gitkeep
│   │   └── __init__.py
│   └── utils
│       ├── __init__.py
│       └── feature_engineering.py
├── tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── e2e
│   │   ├── __init__.py
│   │   └── load
│   │       ├── __init__.py
│   │       └── locustfile.py
│   ├── fixtures
│   │   ├── .gitkeep
│   │   └── __init__.py
│   ├── integration
│   │   ├── __init__.py
│   │   ├── api
│   │   │   ├── __init__.py
│   │   │   ├── test_api.py
│   │   │   ├── test_api_endpoints.py
│   │   │   ├── test_api_integration.py
│   │   │   └── test_infrastructure.py
│   │   └── db
│   │       └── __init__.py
│   ├── test_api.py
│   ├── test_auth.py
│   └── unit
│       ├── __init__.py
│       ├── backend
│       │   ├── __init__.py
│       │   ├── test_ab_testing.py
│       │   ├── test_document_pipeline.py
│       │   └── test_rate_limiter.py
│       ├── ml
│       │   ├── __init__.py
│       │   ├── conftest.py
│       │   ├── test_feature_engineering.py
│       │   └── test_model_predictions.py
│       └── shared
│           └── __init__.py
└── tree.txt
```
