# Healthcare Risk Prediction — End-to-End ML Pipeline

A production-grade machine learning system for predicting **diabetes**, **heart disease**, and **lung cancer** risk from patient health indicators. Built with FastAPI, HTMX, XGBoost, and a full MLOps stack.

> **Status:** Three models live — containerised deployment with monitoring, versioned APIs, and CI/CD. App v3.0.0.

---

## Models at a Glance

| Disease | Dataset | Algorithm | ROC AUC | Calibration | Explainability |
|---|---|---|---|---|---|
| **Diabetes** | CDC BRFSS 2015 (441,456 rows) | XGBoost | 0.879 | Isotonic | SHAP TreeExplainer |
| **Heart Disease** | CDC BRFSS (derived) | XGBoost | 0.85 | Isotonic | SHAP TreeExplainer |
| **Lung Cancer** | Survey dataset | Logistic Regression | 0.97 | Isotonic | SHAP LinearExplainer |

All models serve calibrated probabilities and per-prediction SHAP explanations via the API.

---

## Repository Structure

```
Healthcare_risk_prediction/
│
├── app/
│   ├── main.py                        # Unified FastAPI + HTMX app (v3.0.0)
│   ├── logging_config.py              # Structured logging (structlog, JSON/console)
│   ├── ab_testing.py                  # A/B testing framework for model comparison
│   ├── risk_assistant.py              # CLI + Gradio diabetes risk calculator
│   ├── templates/
│   │   ├── base.html                  # Base layout (HTMX, Tailwind, fonts)
│   │   ├── index.html                 # Main page with 3 prediction tabs
│   │   └── partials/                  # HTMX result/empty/error fragments
│   └── static/
│       └── css/style.css              # Custom styles
│
├── fastapi_backend/
│   ├── model_loader.py                # Model loading & inference for all 3 diseases
│   ├── shap_explainer.py              # SHAP explainability for all models
│   └── schemas.py                     # Pydantic request/response schemas
│
├── feature_store/
│   └── __init__.py                    # Centralised feature definitions & validation
│
├── models/
│   ├── model_registry.json            # Model version, metrics, SHA-256 integrity hashes
│   ├── diabetes_xgboost.pkl           # Diabetes XGBoost model
│   ├── isotonic_calibrator.pkl        # Diabetes probability calibrator
│   ├── shap_explainer.pkl             # SHAP TreeExplainer (diabetes)
│   ├── heart_disease_xgboost.pkl      # Heart disease XGBoost model
│   ├── heart_disease_calibrator.pkl   # Heart disease calibrator
│   ├── heart_disease_features.pkl     # Heart disease feature list
│   ├── lung_cancer_model.pkl          # Lung cancer Logistic Regression model
│   ├── lung_cancer_scaler.pkl         # Lung cancer StandardScaler
│   ├── lung_cancer_calibrator.pkl     # Lung cancer isotonic calibrator
│   └── lung_cancer_features.pkl       # Lung cancer feature list
│
├── scripts/
│   ├── model_registry.py              # CLI: verify hashes, show info, bump versions
│   ├── mlflow_config.py               # MLflow experiment tracking configuration
│   └── calibrate_lung_model.py        # Generates lung cancer isotonic calibrator
│
├── monitoring/
│   ├── prometheus.yml                 # Prometheus scrape configuration
│   └── grafana_dashboard.json         # Grafana dashboard (latency, error rate, throughput)
│
├── tests/
│   ├── test_api.py                    # API + HTMX + rate-limiting + CORS tests
│   ├── test_model_predictions.py      # Model prediction + monotonicity + determinism tests
│   ├── test_feature_engineering.py    # BRFSS feature pipeline tests
│   ├── test_infrastructure.py         # v1 API, registry, monitoring, SHAP, A/B, feature store
│   └── load/
│       └── locustfile.py              # Locust load testing scenarios
│
├── notebooks/
│   ├── brfss_cleaning.ipynb           # Diabetes: cleaning → training → SHAP
│   ├── train_heart_disease_model.ipynb  # Heart disease pipeline
│   └── train_lung_cancer_model.py     # Lung cancer pipeline
│
├── utils/
│   └── feature_engineering.py         # Reusable BRFSS feature pipeline
│
├── data_raw/                          # Raw BRFSS SAS file (not tracked — 1.1 GB)
├── data_processed/                    # Cleaned CSVs (not tracked)
│
├── .github/workflows/ci.yml          # GitHub Actions CI (lint, test matrix, security, Docker)
├── Dockerfile                         # Multi-stage build, non-root user, health check
├── docker-compose.yml                 # App + optional Prometheus monitoring
├── dvc.yaml                           # DVC pipeline stages (data → train → evaluate)
├── pyproject.toml                     # pytest + coverage configuration
├── requirements.txt                   # Production dependencies
├── requirements-dev.txt               # Dev/test dependencies (pytest, locust, flake8)
├── retrain.py                         # One-shot retraining script with MLflow tracking
├── start.sh                           # One-command server startup script
└── README.md
```

---

## ML Pipeline

### Diabetes (CDC BRFSS 2015)

**Data Cleaning**
- Source: [CDC BRFSS 2015](https://www.cdc.gov/brfss/) (`LLCP2015.XPT`, SAS format, 441,456 rows)
- 9 variables selected, renamed, cleaned — rows with 7+ missing values dropped
- BMI rescaled from ×100 integer encoding

**Feature Engineering**
- 5 interaction features: `bmi_age`, `bmi_bp`, `age_bp`, `chol_bmi`, `health_bmi`
- 13 total features fed to the model
- Definitions centralised in `feature_store/`

**Class Imbalance**
- `scale_pos_weight = count(negative) / count(positive)` — full training set retained (30,024 rows)

**Models**
| Model | ROC AUC |
|---|---|
| Random Forest (baseline) | 0.871 |
| **XGBoost + early stopping** | **0.879** |

XGBoost config: `n_estimators=800, max_depth=6, lr=0.03, subsample=0.8, colsample=0.8, early_stopping_rounds=50`

**Probability Calibration**
- Isotonic regression maps raw XGBoost scores → real-world probabilities
- Brier score: 0.156 → 0.034 (78% improvement)

**Explainability (SHAP)**
- `TreeExplainer` for global and per-patient feature attribution
- Summary plot, bar plot, dependence plot (BMI × Age interaction)
- Risk calculator shows top 5 contributing factors per prediction

### Heart Disease

- 14 clinical features (age group, sex, BMI, blood pressure, cholesterol, smoking, physical activity, diet, alcohol, general/mental/physical health, diabetes)
- XGBoost with isotonic-calibrated probabilities
- SHAP TreeExplainer for per-prediction explanations
- Stratified 80/20 split + cross-validation

### Lung Cancer

- 8 features: age, gender, smoking, yellow fingers, chronic disease, fatigue, wheezing, shortness of breath
- Logistic Regression + StandardScaler pipeline
- Isotonic calibration for probability adjustment
- SHAP LinearExplainer for per-prediction explanations
- Multi-model comparison (Logistic Regression, RF, SVM, KNN, Naive Bayes, GBM, XGBoost) with GridSearchCV tuning

---

## API Endpoints

### HTMX UI Endpoints (return HTML fragments)

| Endpoint | Description |
|---|---|
| `GET /` | Main UI with all 3 prediction tabs |
| `POST /predict/diabetes` | Diabetes form → HTML result fragment |
| `POST /predict/heart` | Heart disease form → HTML result fragment |
| `POST /predict/lung` | Lung cancer form → HTML result fragment |

### JSON API — Legacy (v0)

| Endpoint | Disease |
|---|---|
| `POST /api/predict` | Diabetes |
| `POST /api/predict-heart` | Heart Disease |
| `POST /api/predict-lung` | Lung Cancer |

### JSON API — Versioned (v1)

| Endpoint | Description |
|---|---|
| `GET /api/v1/` | API info + available models |
| `GET /api/v1/models` | Model registry (versions, metrics, status) |
| `POST /api/v1/predict/diabetes` | Diabetes prediction |
| `POST /api/v1/predict/heart` | Heart disease prediction |
| `POST /api/v1/predict/lung` | Lung cancer prediction |
| `POST /api/v1/explain/diabetes` | Diabetes prediction + SHAP explanation |
| `POST /api/v1/explain/heart` | Heart disease prediction + SHAP explanation |
| `POST /api/v1/explain/lung` | Lung cancer prediction + SHAP explanation |

### Infrastructure Endpoints

| Endpoint | Description |
|---|---|
| `GET /healthz` | Liveness/readiness probe |
| `GET /metrics` | Prometheus metrics (request rate, latency, error rate) |
| `GET /api/docs` | Swagger UI |

**Prediction response:**
```json
{
  "risk_percentage": 29.9,
  "risk_level": "Moderate"
}
```

**Explanation response (v1 explain endpoints):**
```json
{
  "risk_percentage": 29.9,
  "risk_level": "Moderate",
  "explanation": {
    "features": ["bmi", "age_group", "high_bp", "..."],
    "shap_values": [0.1234, -0.0567, 0.0891, "..."],
    "base_value": -1.2345
  }
}
```

---

## Quick Start

### Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run the Server

**Option 1 — One-command startup:**
```bash
bash start.sh
```

**Option 2 — Manual:**
```bash
uvicorn app.main:app --reload --port 8000
```

**Option 3 — Docker:**
```bash
docker compose up --build
```

**Option 4 — Docker with Prometheus monitoring:**
```bash
docker compose --profile monitoring up --build
```

Open http://127.0.0.1:8000 in your browser.  
Swagger API docs: http://127.0.0.1:8000/api/docs  
Prometheus metrics: http://127.0.0.1:8000/metrics

### Train Models

**Option A — Automated retraining script (downloads BRFSS data, logs to MLflow):**
```bash
python retrain.py
```

**Option B — Notebooks:**
```bash
# Diabetes
jupyter notebook notebooks/brfss_cleaning.ipynb

# Heart disease
jupyter notebook notebooks/train_heart_disease_model.ipynb

# Lung cancer
python -m notebooks.train_lung_cancer_model
```

### Verify Model Integrity
```bash
python scripts/model_registry.py verify   # check SHA-256 hashes
python scripts/model_registry.py info      # print model metadata
```

### Run Tests
```bash
pip install -r requirements-dev.txt
pytest                                     # 161 tests, 88% coverage
```

### Load Testing
```bash
pip install locust
locust -f tests/load/locustfile.py --host http://localhost:8000
```

### Diabetes Risk Calculator (CLI / Gradio)
```bash
python app/risk_assistant.py               # CLI mode
python app/risk_assistant.py --ui          # Gradio web UI (requires: pip install gradio)
```

---

## System Architecture

```
User Browser (http://localhost:8000)
      │
      ▼
FastAPI + HTMX UI (single server)
      │
      ├── HTMX forms   → POST /predict/{disease}         → HTML fragment
      ├── Legacy API    → POST /api/predict*              → JSON response
      ├── Versioned API → POST /api/v1/predict/{disease}  → JSON response
      ├── Explain API   → POST /api/v1/explain/{disease}  → JSON + SHAP values
      ├── Health        → GET /healthz                    → liveness probe
      └── Metrics       → GET /metrics                    → Prometheus scrape
      │
      ▼
ML Models (loaded at startup)
      ├── diabetes_xgboost.pkl    + isotonic_calibrator.pkl  + SHAP TreeExplainer
      ├── heart_disease_xgboost.pkl + heart_disease_calibrator.pkl + SHAP TreeExplainer
      └── lung_cancer_model.pkl   + lung_cancer_calibrator.pkl + SHAP LinearExplainer
      │
      ▼
Infrastructure
      ├── Prometheus + Grafana          (monitoring/alerting)
      ├── MLflow                        (experiment tracking)
      ├── DVC                           (data & pipeline versioning)
      ├── Model Registry                (version, metrics, SHA-256 integrity)
      ├── Feature Store                 (centralised feature definitions)
      └── A/B Testing Framework         (champion vs challenger routing)
```

---

## MLOps & Infrastructure

| Capability | Implementation | Details |
|---|---|---|
| **Automated Testing** | pytest | 161 tests, 88% coverage, model + API + infra |
| **CI/CD** | GitHub Actions | Lint → Test (matrix 3.12/3.13) → Security audit → Docker build + smoke test |
| **Containerisation** | Docker | Multi-stage build, non-root user, health check, resource limits |
| **Structured Logging** | structlog | JSON output (prod), console (dev), request-level tracing |
| **API Versioning** | `/api/v1/` | Versioned endpoints; legacy routes preserved for backwards compatibility |
| **Model Calibration** | Isotonic regression | All 3 models return calibrated probabilities |
| **Explainability** | SHAP | Per-prediction feature attributions via `/api/v1/explain/*` endpoints |
| **Model Versioning** | Model registry | `model_registry.json` — version, metrics, SHA-256 hash verification |
| **Experiment Tracking** | MLflow | Parameters, metrics, and artifacts logged during retraining |
| **Monitoring** | Prometheus + Grafana | `/metrics` endpoint, latency histograms, error rates, request counts |
| **Data Versioning** | DVC | Pipeline stages for data processing + model training |
| **Load Testing** | Locust | 7 weighted user scenarios covering all endpoints |
| **A/B Testing** | Custom framework | Deterministic hash-based traffic routing, result comparison |
| **Feature Store** | Custom module | Centralised feature definitions, validation, and transformation |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| ML | XGBoost 3.2, scikit-learn 1.8, SHAP 0.51 |
| Data | pandas 3.0, NumPy 2.x, pyreadstat |
| API | FastAPI 0.135, Uvicorn 0.41, Pydantic 2.12 |
| UI | HTMX 1.9, Jinja2 3.1, Tailwind CSS (CDN) |
| Logging | structlog 24.x |
| Monitoring | prometheus-fastapi-instrumentator 7.x |
| Containerisation | Docker (multi-stage), Docker Compose |
| CI/CD | GitHub Actions (lint, test matrix, security, Docker) |
| Testing | pytest 8.x, pytest-cov, Locust 2.x |
| Experiment Tracking | MLflow (optional) |
| Data Versioning | DVC (optional) |
| Visualisation | matplotlib 3.10, seaborn 0.13 |
| Serialisation | joblib 1.5 |

---

## Evaluation Strategy

- Stratified 80/20 train-test split across all models
- 5-fold cross-validation (Diabetes: Mean AUC 0.860 ± 0.010)
- Confusion matrix, precision/recall/F1, ROC-AUC
- ROC curve comparison across model families
- **Reliability diagram** — calibration curve + Brier score
- SHAP global feature importance + per-patient local explanations
- Model integrity verification via SHA-256 hash checks

---

## Security

- **Rate limiting** — 60 requests/minute per IP (configurable via `RATE_LIMIT_PER_MINUTE` env var)
- **CORS** — restricted to localhost origins by default (configurable via `CORS_ORIGINS` env var)
- **Input validation** — Pydantic schemas on all endpoints
- **Non-root container** — Docker runs as `appuser` (UID 1000)
- **Read-only filesystem** — Docker Compose mounts app as read-only
- **Dependency auditing** — `pip-audit` in CI pipeline
- **No secrets in registry** — SHA-256 hashes stripped from public `/api/v1/models` response

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `RATE_LIMIT_PER_MINUTE` | `60` | Max requests per IP per minute |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Comma-separated allowed origins |
| `APP_ENV` | `development` | `production` for JSON log output |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `MLFLOW_TRACKING_URI` | `file://mlruns` | MLflow tracking server URI |

---

## Author

**Aryan Mishra**  
Data Science Student — focused on ML Engineering & Deployment

---

## License

This project is for educational and portfolio purposes.
