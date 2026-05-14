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
- Implemented **A/B Testing** capabilities (`app/ab_testing.py`) to systematically deploy, compare UI variants, and measure user engagement.

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
python -m pip install -r requirements-dev.txt
dvc pull
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
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
python -m pip install -r requirements-dev.txt
```

### 2. Run the Unified Application
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open:
- **Web UI:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **API Root:** [http://127.0.0.1:8000/api](http://127.0.0.1:8000/api)
- **API Docs (Swagger):** [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)

*(Note: `start.sh` or `docker-compose up` are also available as alternate workflows).*

---

##  API Overview

### Versioned Endpoints (Requires `X-API-Key`)
*Base URL: `/api/v1`*
- `GET /` - API version info
- `GET /models` - List available models
- `POST /predict/{disease}` - Inference for Diabetes, Heart Disease, or Lung Cancer
- `POST /explain/{disease}` - SHAP Explanations
- `POST /document/upload` - Clinical feature extraction pipeline

*Development API Key:* If `API_KEY` isn't set and `APP_ENV` is not `production`, you can use `X-API-Key: healthpredict_dev_key_2026`.

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
python -m bandit -r app fastapi_backend scripts utils -x tests,notebooks
python -m pip_audit -r requirements.txt
python -m pip_audit -r requirements-dev.txt
```

---

## Reproduce Results With DVC

```bash
dvc pull
dvc repro
```

---

## Folder Structure

| Path | Purpose |
| --- | --- |
| `app/` | Main FastAPI app, HTMX templates, application routes, LLM assistant, and A/B testing framework. |
| `fastapi_backend/` | API schemas, model loading, prediction support, and SHAP explainability utilities. |
| `feature_store/` | Feature mapping and reusable feature-store components. |
| `scripts/` | Retraining, calibration, fairness evaluation, model registry, MLflow, and deployment helpers. |
| `utils/` | Shared feature engineering and helper utilities. |
| `tests/` | Unit, integration, API, infrastructure, and load tests. |
| `notebooks/` | Research notebooks and exploratory model development. |
| `models/` | Local model artifacts restored through DVC or generated by training pipelines. |
| `data/` | Local datasets restored through DVC or generated during development. |
| `results/` | Local evaluation outputs, plots, metrics, and reports. |
| `docs/` | ADRs, model cards, and project documentation. |
| `nginx/` | Nginx reverse proxy configuration. |
| `kubernetes/` | Helm chart and Kubernetes manifests. |
| `infrastructure/` | Terraform infrastructure-as-code. |
| `monitoring/` | Prometheus and Grafana configuration. |
