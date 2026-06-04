# HealthPredict AI: End-to-End Healthcare Risk Prediction Platform

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](#)
[![Python Version](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg)](#)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](#)
[![Docker Support](https://img.shields.io/badge/docker-ready-blue.svg)](#)
[![Kubernetes Support](https://img.shields.io/badge/kubernetes-helm-blue.svg)](#)

An enterprise-grade, end-to-end Machine Learning, Web, and MLOps ecosystem designed to predict patient risks for **Diabetes**, **Heart Disease**, and **Lung Cancer** based on clinical indicators. This platform combines a highly interactive **FastAPI & HTMX** web interface, robust versioned REST APIs, natural language clinical document ingestion, A/B testing capability, model explainability (SHAP), algorithmic fairness calibration, and comprehensive observability (Prometheus & Grafana).

---

##  System Architecture

```mermaid
flowchart TB
    User(["Client / Web Browser"])
    
    subgraph Edge ["Edge & Security Layer (Nginx)"]
        NginxProxy["Nginx Reverse Proxy\n(SSL Termination, Headers, Rate Limiting)"]
    end

    subgraph AppServer ["Application Layer (FastAPI Backend)"]
        Router["Unified Routing Engine\n(HTMX UI & JSON REST API)"]
        AuthService["Auth & Session Manager\n(JWT, Session Store, DB User Store)"]
        NLPService["Medical NLP Parser\n(PyMuPDF, Tesseract OCR, Clinical Heuristics)"]
        ABService["A/B Testing Engine\n(Variant Routing & Analytics)"]
        ModelMgr["Model Health & Warmup Manager\n(Async Loading, Health Diagnostics)"]
        ExplainService["SHAP Explainability Engine\n(Feature Plots & Force Diagrams)"]
    end

    subgraph DataML ["ML & Data Infrastructure"]
        MLflow["MLflow Registry\n(Production Model Artifacts)"]
        DVCStore["DVC Registry\n(Local Stub Artifacts & Pipelines)"]
        DB[(SQLite / PostgreSQL\nAudit Logs & User Profiles)]
        RedisCache[(Redis Cache\nRate Limiter & Session Cache)]
    end

    subgraph Mon ["Telemetry & Observability"]
        Prometheus["Prometheus Server\n(Metrics Exporter /metrics)"]
        Grafana["Grafana Dashboards\n(System & ML Health Visuals)"]
    end

    %% Client Interactions
    User -->|HTTPS (443)| NginxProxy
    NginxProxy -->|Internal Proxy (8000)| Router
    
    %% Application Flow
    Router <--> AuthService
    Router --> NLPService
    Router --> ABService
    Router --> ModelMgr
    ModelMgr --> ExplainService
    
    %% Data Store Interactions
    AuthService <--> DB
    NLPService -.-> DB
    ModelMgr <--> MLflow
    ModelMgr <--> DVCStore
    Router <--> RedisCache
    
    %% Monitoring Exporters
    Router -.->|Scrapes| Prometheus
    Prometheus --> Grafana
```

---

##  Key Features & Capabilities

### 1. Advanced Machine Learning & Algorithmic Fairness
*   **Multi-Model Predictions:** Live inference for **Diabetes**, **Heart Disease**, and **Lung Cancer** risks using production-trained XGBoost classifiers.
*   **Model Explainability (SHAP):** Live generation of SHAP (SHapley Additive exPlanations) values, converting complex ensemble predictions into interpretable local feature importance visualizations for clinicians.
*   **Model Calibration & Bias Reductions:** All models feature probability calibration (e.g., Isotonic Regression in `calibrate_lung_model.py`) and algorithmic fairness evaluations (`fairness_eval.py`) to reduce demographics-based prediction disparities.
*   **Warmup & Lifecycle Management:** Built-in `ModelManager` runs asynchronous startup warmups, registers memory footfalls, assesses pipeline readiness latency, and transitions model stages automatically.

### 2. Clinical NLP Document Ingestion
*   **Structured Parser:** Handles PDF and image uploads containing clinical reports (utilizing PyMuPDF, Pillow, and Tesseract OCR).
*   **NLP Entity Extraction:** Automates the extraction of patient metrics (such as BMI, high blood pressure, smoker status, and age groups) from raw clinical unstructured texts, pre-populating risk evaluation forms.

### 3. Integrated Full-Stack Web App (FastAPI & HTMX)
*   **Interactive Web UI:** Developed a single-page-like interactive dashboard using **HTMX** for asynchronous form submission and partial page rendering without heavy frontend JS frameworks.
*   **A/B Testing Framework:** Embedded variant router (`backend/app/services/ab_testing.py`) to compare different UI layouts and form structures, recording engagement metrics dynamically.

### 4. Enterprise Security & Quality Compliance
*   **Multiple Auth Schemes:** Secure user session management via encrypted cookies/JWT and API Key headers (`X-API-Key`) for developer integrations.
*   **Defensive Security:** Implements CSRF tokens on forms, Trusted Host header validation, CORS strict configurations, and Redis-backed IP rate-limiting (`slowapi`).
*   **Security Scanning:** Integrated SAST via `bandit` and dependency auditing via `pip-audit` directly into local workflows and CI check-steps.

### 5. Production Telemetry & Observability
*   **Live Metrics:** Exposes a `/metrics` scrape endpoint for Prometheus, monitoring api latencies, request error rates, model warmups, and DB query times.
*   **Grafana Visualization:** Auto-configured dashboards present system resources alongside predictive throughput and classification latencies.

---

##  Technology Stack

| Component | Technologies & Frameworks | Description |
| :--- | :--- | :--- |
| **Backend Core** | FastAPI, Pydantic v2, SQLAlchemy, Uvicorn, Gunicorn | High-performance async APIs, request validation, and database ORM. |
| **Machine Learning**| XGBoost, Scikit-Learn, SHAP, Pandas, NumPy, Joblib | Model architectures, explainability plots, and data pre-processing. |
| **MLOps / Registry**| MLflow, DVC (Data Version Control) | Experiment tracking, model registry, and pipeline run reproducibility. |
| **Frontend UI** | HTMX, Jinja2 Templates, Vanilla CSS | Interactive single-page UI, partial HTML updates, and typography. |
| **DevOps / Infra** | Docker, Nginx, Kubernetes (Helm), Terraform | Container builds, reverse proxy/SSL, orchestration, and AWS ECS IaC. |
| **Security** | Redis, Slowapi, PyJWT, Bandit, Pip-Audit | Rate-limiting, token-based auth, SAST, and dependency verification. |
| **Monitoring** | Prometheus Client, Grafana | Custom metrics logging, scraping dashboarding. |

---

##  Getting Started (Local Development)

### Prerequisites
*   Python 3.12 or 3.13
*   macOS or Linux shell environment
*   Docker & Docker Compose (Optional, for containerized run)
*   Tesseract OCR (Required locally for NLP document parser: `brew install tesseract` on macOS / `apt-get install tesseract-ocr` on Linux)

### 1. Setup Virtual Environment & Install Dependencies
Clone the repository and initialize a virtual environment:
```bash
git clone <repo-url>
cd Healthcare-Risk-Prediction

# Option A: Standard Python venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements-dev.txt

# Option B: Conda (Recommended for scripts referencing .venv-1)
conda create -p .venv-1 python=3.13 -y
conda activate ./.venv-1
python -m pip install --upgrade pip
python -m pip install -r backend/requirements-dev.txt
```

### 2. Configure Environment Variables
Copy the template configuration files and modify environment variables as required:
```bash
# Setup root, backend, and config environment files
cp .env.example .env
cp backend/.env.example backend/.env
```

### 3. Generate Local Stub Models (DVC Pipeline)
Before first launch, run DVC to generate the offline-friendly deterministic stub models required to boot the application and pass smoke tests:
```bash
# Install DVC dependencies (kept separate due to upstream security-alert isolation)
python -m pip install -r ml/requirements-dvc.txt

# Regenerate local stub model artifacts
dvc repro ml/dvc.yaml
dvc status ml/dvc.yaml
```

### 4. Run the Development Server
You can launch the server using our dev start script or execute Uvicorn directly:
```bash
# Workflow A: Via startup utility script (checks port 8000, runs live hot-reload)
chmod +x deployment/scripts/start.sh
./deployment/scripts/start.sh

# Workflow B: Via direct Uvicorn execution
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Once running, navigate to:
*   **Web Portal UI:** [http://localhost:8000/](http://localhost:8000/)
*   **JSON API Base:** [http://localhost:8000/api](http://localhost:8000/api)
*   **Interactive API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs) (or `/api/docs`)

---

##  REST API Reference

All production-grade JSON API requests (under `/api/v1/`) require authentication. Provide your API Key in the `X-API-Key` header.
> [!NOTE]
> During development, if `API_KEY` is not set in `.env`, define a key in `DEV_API_KEY` and use that for local authorization.

### Route Mapping Summary
| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| **GET** | `/healthz` | Public | Liveness check (shallow). |
| **GET** | `/api/v1/health/ready` | Public | Readiness check (validates model weights & DB connection status). |
| **GET** | `/metrics` | Public | Prometheus raw metrics endpoint. |
| **POST** | `/api/predict` | Legacy/Public | Predicts Diabetes risk (legacy input format). |
| **POST** | `/api/predict/diabetes` | `X-API-Key` | Predicts Diabetes risk. |
| **POST** | `/api/predict/heart` | `X-API-Key` | Predicts Heart Disease risk. |
| **POST** | `/api/predict/lung` | `X-API-Key` | Predicts Lung Cancer risk (calibrated). |
| **POST** | `/api/upload` | `X-API-Key` | Uploads clinical PDFs/images for automated NLP feature extraction. |

### cURL CLI Examples

<details>
<summary><b>1. Readiness & Model Diagnostic Check</b></summary>

```bash
curl -X GET http://localhost:8000/api/v1/health/ready
```
*Response:*
```json
{
  "status": "ready",
  "database": "connected",
  "models": {
    "diabetes": { "status": "loaded", "version": "v1.0-stub" },
    "heart_disease": { "status": "loaded", "version": "v1.0-stub" },
    "lung_cancer": { "status": "loaded", "version": "v1.0-stub" }
  }
}
```
</details>

<details>
<summary><b>2. Predict Diabetes Risk</b></summary>

```bash
curl -X POST http://localhost:8000/api/predict/diabetes \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-dev-api-key" \
  -d '{
    "age": 45,
    "bmi": 28.4,
    "bp": 1,
    "cholesterol": 1,
    "smoker": 0,
    "activity": 1,
    "health": 3,
    "mental": 2
  }'
```
</details>

<details>
<summary><b>3. Clinical Document Parsing</b></summary>

```bash
curl -X POST http://localhost:8000/api/upload \
  -H "X-API-Key: your-dev-api-key" \
  -F "file=@/path/to/patient_report.pdf"
```
</details>

---

##  MLflow Experiment Tracking & Registry

The platform is integrated with **MLflow** for tracking parameter tunings and registering verified classifiers. 
*   **Start MLflow Server locally:**
    ```bash
    mlflow ui --host 127.0.0.1 --port 5000
    ```
*   **Migrate local stub models to MLflow:**
    Run the migration utility script to log local stub artifacts directly into your MLflow instance so they can be registered and warmed up by the API:
    ```bash
    python ml/scripts/migrate_to_mlflow.py
    ```

For detailed guides on model configurations, calibration curves, and fairness checks, refer to [ml/README.md](file:///Users/theogengineer/Projects/Healthcare-Risk-Prediction/ml/README.md) (if present) or our [Troubleshooting Guide](file:///Users/theogengineer/Projects/Healthcare-Risk-Prediction/docs/TROUBLESHOOTING.md).

---

##  Production Deployment & Orchestration

### 1. Docker Compose
Containerized builds include an Nginx SSL termination reverse proxy, Redis cache, Prometheus exporter, Grafana dashboards, and the FastAPI application.

```bash
# Build and spin up the core platform (App + Nginx Proxy)
docker compose -f deployment/docker/docker-compose.yml up -d --build

# Launch with full telemetry support (Prometheus + Grafana enabled)
./deployment/scripts/deploy.sh --with-monitoring

# Tear down all running containers
docker compose -f deployment/docker/docker-compose.yml down
```

### 2. Kubernetes (Helm Chart)
Deploy HealthPredict AI dynamically to a Kubernetes cluster using the configured Helm chart inside `deployment/kubernetes/healthpredict`:
```bash
# Validate chart configurations
helm lint deployment/kubernetes/healthpredict

# Install / Upgrade release on cluster
helm upgrade --install healthpredict deployment/kubernetes/healthpredict \
  --namespace production --create-namespace \
  -f deployment/kubernetes/healthpredict/values.yaml
```

### 3. Terraform (Cloud Infrastructure)
Manage cloud infrastructure (AWS ECS, VPC, ALB, Security Groups) using Terraform configurations located in `deployment/infrastructure/`:
```bash
cd deployment/infrastructure
terraform init
terraform plan
terraform apply
```

###  Production Deployment Considerations
*   **Render Cold Starts:** In resource-constrained environments (like Render free tiers), XGBoost models and SHAP explainers might trigger slow initialization. The production Gunicorn wrapper in the `Dockerfile` sets `--timeout 120` to prevent worker OOM crashes.
*   **Out of Memory (OOM) Safety:** Concurrent loads of multi-model XGBoost/sklearn weights can spike past 512MB RAM. If memory footprints exceed limits, consult [TROUBLESHOOTING.md](file:///Users/theogengineer/Projects/Healthcare-Risk-Prediction/docs/TROUBLESHOOTING.md) to disable unused predictors or adjust worker allocations.

---

##  Testing & Code Quality Assurance

To keep code robust, secure, and compliant, run verification suites before pushing updates:

```bash
# Run the entire test suite (Unit, Integration, & E2E)
pytest

# Run tests with test-coverage report
pytest --cov=backend/app --cov-report=html tests/

# Scan backend code for security vulnerabilities (SAST)
bandit -r backend/app ml shared -x tests,ml/experiments

# Check dependencies for known CVEs / vulnerabilities
pip-audit -r backend/requirements.txt
pip-audit -r backend/requirements-dev.txt
```

---

##  Additional Resources
*   [Security Architecture Guide](file:///Users/theogengineer/Projects/Healthcare-Risk-Prediction/docs/SECURITY.md) — Comprehensive overview of multi-layered security.
*   [Troubleshooting & Recovery](file:///Users/theogengineer/Projects/Healthcare-Risk-Prediction/docs/TROUBLESHOOTING.md) — Common error resolution steps, cold-start limits, and MLflow setups.
*   [Contributing Guidelines](file:///Users/theogengineer/Projects/Healthcare-Risk-Prediction/docs/CONTRIBUTING.md) — Code styles, DVC model workflows, and guidelines.
