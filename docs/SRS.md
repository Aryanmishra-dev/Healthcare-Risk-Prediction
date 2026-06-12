# Software Requirements Specification
## Healthcare Risk Prediction System
### Version 1.0 | 2026-06-12
### Prepared by: AI Code Analysis Agent

---

### 1. INTRODUCTION

#### 1.1 Purpose of the Document
The purpose of this Software Requirements Specification (SRS) is to define the functional, non-functional, interface, and performance requirements for the HealthPredict AI system. This document is intended for software engineers, data scientists, DevOps personnel, and clinical stakeholders involved in the development, deployment, and operation of the platform.

#### 1.2 Scope of the Software
HealthPredict AI is an enterprise-grade, end-to-end Machine Learning, Web, and MLOps platform designed to predict patient risks for Diabetes, Heart Disease, and Lung Cancer based on clinical indicators. It provides a highly interactive FastAPI & HTMX web interface, robust versioned REST APIs, natural language clinical document ingestion via OCR, A/B testing capability, model explainability using SHAP, algorithmic fairness calibration, and comprehensive observability via Prometheus and Grafana.

#### 1.3 Definitions, Acronyms, and Abbreviations
*   **API:** Application Programming Interface
*   **BMI:** Body Mass Index *(inferred)*
*   **BRFSS:** Behavioral Risk Factor Surveillance System *(inferred)*
*   **CORS:** Cross-Origin Resource Sharing
*   **CSRF:** Cross-Site Request Forgery
*   **DVC:** Data Version Control
*   **FastAPI:** High-performance web framework for building APIs with Python
*   **Grafana:** Open-source platform for monitoring and observability
*   **HTMX:** Library that allows access to AJAX, CSS Transitions, WebSockets, and Server Sent Events directly in HTML
*   **JWT:** JSON Web Token
*   **MLflow:** Open-source platform for the machine learning lifecycle
*   **MLOps:** Machine Learning Operations
*   **NLP:** Natural Language Processing
*   **OCR:** Optical Character Recognition (specifically Tesseract)
*   **PyMuPDF:** Python binding for the MuPDF library, used for PDF parsing
*   **SAST:** Static Application Security Testing (e.g., Bandit)
*   **SHAP:** SHapley Additive exPlanations (Feature importance visualization)
*   **XGBoost:** Extreme Gradient Boosting algorithm

#### 1.4 References
*   [README.md](file:///Users/theogengineer/Projects/Healthcare-Risk-Prediction/README.md)
*   [SECURITY.md](file:///Users/theogengineer/Projects/Healthcare-Risk-Prediction/SECURITY.md)
*   mlruns / DVC artifact storage metadata
*   Tesseract OCR Documentation
*   FastAPI / HTMX Official Documentation

#### 1.5 Document Overview
This document is organized into ten main sections. Section 2 provides a high-level overview of the system architecture and constraints. Section 3 details the functional requirements. Section 4 covers external interfaces. Section 5 describes non-functional requirements including security and performance. Sections 6, 7, and 8 cover Database, Machine Learning, and Deployment requirements respectively. Section 9 outlines constraints, and Section 10 provides comprehensive appendices.

---

### 2. OVERALL DESCRIPTION

#### 2.1 Product Perspective
HealthPredict AI acts as a standalone decision support system within a broader healthcare ecosystem. It provides risk prediction via web-based user interfaces and programmatic REST APIs. The system interfaces externally with:
*   **Nginx Reverse Proxy:** Acts as the edge layer providing SSL termination and request filtering.
*   **Redis:** In-memory data structure store used for caching and rate limiting.
*   **PostgreSQL / SQLite:** Relational database for storing user authentication data, sessions, and prediction audit logs (via `DATABASE_URL` in `.env.example`).
*   **MLflow & DVC:** External machine learning artifact storage and tracking systems.
*   **AWS S3 (Optional):** Object storage for cloud model artifacts (`S3_MODEL_BUCKET` in `.env.example`).
*   **OpenAI API (Optional):** NLP assistant integrations (`OPENAI_API_KEY`).

#### 2.2 Product Functions (high-level summary)
*   **User Management:** Registration, login, session management, and profile updates.
*   **Risk Prediction:** Dedicated endpoints and forms for Diabetes, Heart Disease, and Lung Cancer.
*   **Clinical Document Parsing:** Automated extraction of patient metrics from uploaded PDF/image reports.
*   **Dashboard & History:** Viewing past predictions and tracking usage metrics.
*   **A/B Testing:** Dynamic routing between champion and challenger models for live performance comparison.
*   **Health & Diagnostics:** Readiness checks verifying database connectivity and model load states.

#### 2.3 User Classes and Characteristics
*   **Clinician/Provider:** Primary user of the HTMX web interface for submitting patient data and reviewing SHAP explanations. *(inferred from code)*
*   **Patient:** Potential user accessing limited self-assessment tools. *(inferred from auth/roles code)*
*   **Admin/System Operator:** Manages the deployment, views Prometheus metrics on Grafana, and tracks MLflow experiments. *(inferred from code)*
*   **API Consumer (Developer):** System or user interacting directly with the `/api/v1/` REST endpoints using an `X-API-Key`.

#### 2.4 Operating Environment
*   **Runtime:** Python 3.12 or 3.13 (`pyproject.toml`) and Node.js for frontend build scripts.
*   **Containerization:** Docker (`Dockerfile`) using `python:3.13-slim` base image.
*   **Orchestration:** Kubernetes (Helm chart) or Render.com (`render.yaml`).
*   **Database:** PostgreSQL 15 (Docker Compose) or SQLite (Local default).
*   **OS Packages:** `libgomp1` (required by XGBoost) and `tesseract-ocr` (required for NLP).

#### 2.5 Design and Implementation Constraints
*   **TLS Requirement:** Production traffic MUST terminate TLS at the platform or reverse proxy (`SECURITY.md`).
*   **Memory Constraints:** Concurrent loads of multi-model XGBoost/sklearn weights require at least 512MB RAM (`README.md`).
*   **Timeout Constraints:** Cold starts on platforms like Render require a 120-second Gunicorn worker timeout to prevent OOM/timeout crashes.
*   **Library Constraints:** Scikit-learn (1.8.0), XGBoost (3.2.0), and FastAPI (0.135.4) versions are strictly pinned (`requirements.txt`).
*   **Security Restrictions:** Must implement CSRF tokens, Trusted Host headers, and CORS restrictions (`.env.example`).

#### 2.6 Assumptions and Dependencies
*   It is assumed that a Redis server is available for rate-limiting in production environments, though an in-memory fallback exists (`main.py`).
*   MLflow tracking server is assumed to be running or a local `file://` directory is writable for model registration.
*   The system assumes Tesseract OCR is installed on the host system or container for clinical document parsing.

---

### 3. SYSTEM FEATURES (Functional Requirements)

**Feature ID:** FR-001
**Title:** User Registration
**Description:** Allows new users to create an account by providing an email, full name, and password.
**Stimulus/Response:** User submits registration form → System hashes password, stores in DB, and returns user ID.
**Evidence:** `[backend/app/auth/router.py:179]`
**Priority:** High

**Feature ID:** FR-002
**Title:** User Authentication and Session Management
**Description:** Authenticates users via email/password and issues JWT access and refresh tokens. Supports session revocation.
**Stimulus/Response:** User submits login credentials → System validates, creates session in DB, returns JWT.
**Evidence:** `[backend/app/auth/router.py:205]`
**Priority:** Critical

**Feature ID:** FR-003
**Title:** Diabetes Risk Prediction
**Description:** Calculates the probability of diabetes based on 8 clinical features (Age, BMI, BP, Cholesterol, Smoker, Activity, General Health, Mental Health).
**Stimulus/Response:** User submits features via HTMX or JSON API → System runs XGBoost inference, logs audit, returns risk percentage, level, and SVG gauge offset.
**Evidence:** `[backend/app/main.py:433]`, `[backend/app/schemas/prediction.py:16]`
**Priority:** Critical

**Feature ID:** FR-004
**Title:** Heart Disease Risk Prediction
**Description:** Calculates heart disease probability using 14 clinical features (including Trestbps, Chol, FBS, Thalach).
**Stimulus/Response:** User submits features → System runs inference, logs audit, returns predicted risk.
**Evidence:** `[backend/app/main.py:489]`, `[backend/app/schemas/prediction.py:50]`
**Priority:** Critical

**Feature ID:** FR-005
**Title:** Lung Cancer Risk Prediction
**Description:** Calculates lung cancer probability utilizing features like smoking, yellow fingers, chronic disease, and wheezing.
**Stimulus/Response:** User submits features → System runs calibrated inference, logs audit, returns predicted risk.
**Evidence:** `[backend/app/main.py:563]`, `[backend/app/schemas/prediction.py:92]`
**Priority:** Critical

**Feature ID:** FR-006
**Title:** Clinical Document Parsing (NLP)
**Description:** Ingests PDF or Image clinical reports, performs OCR, and extracts metrics (BMI, BP, Cholesterol, etc.) using regex heuristics.
**Stimulus/Response:** User uploads file → System extracts text via PyMuPDF/Tesseract, maps to entities, returns JSON structure.
**Evidence:** `[backend/app/services/medical_nlp.py:282]`, `[backend/app/main.py:781]`
**Priority:** High

**Feature ID:** FR-007
**Title:** A/B Testing Variant Routing
**Description:** Routes a deterministic percentage of prediction requests to a challenger model based on a hash of the request ID.
**Stimulus/Response:** System receives prediction request → Router computes hash, invokes either champion or challenger function, and records latency/risk metrics.
**Evidence:** `[backend/app/services/ab_testing.py:75]`
**Priority:** Medium

**Feature ID:** FR-008
**Title:** Model Health & Readiness Check
**Description:** Checks if all required ML models have been loaded into memory successfully before serving requests.
**Stimulus/Response:** K8s or Load Balancer queries `/api/v1/health/ready` → System queries `model_manager` state, returns 200 if loaded or 503 if not ready.
**Evidence:** `[backend/app/main.py:416]`
**Priority:** High

**Feature ID:** FR-009
**Title:** Dashboard Analytics & History
**Description:** Provides users with a history of their past prediction requests and usage statistics.
**Stimulus/Response:** User queries `/auth/history` or `/auth/stats` → System queries `prediction_audit_logs` DB table and returns aggregated statistics.
**Evidence:** `[backend/app/auth/router.py:287]`
**Priority:** Medium

**Feature ID:** FR-010
**Title:** Model Explanation (SHAP)
**Description:** Generates SHAP values for predictions to explain the impact of individual features on the final risk score. *(inferred from code presence)*
**Stimulus/Response:** System completes prediction → Explainer service computes SHAP values for feature importance.
**Evidence:** `[backend/app/services/shap_explainer.py]`
**Priority:** Medium

---

### 4. EXTERNAL INTERFACE REQUIREMENTS

#### 4.1 User Interface Requirements
*   **Web Framework:** The frontend must utilize HTMX for dynamic partial page updates without full reloads, combined with Jinja2 templating on the backend.
*   **Responsive Design:** The UI must be responsive, using vanilla CSS or equivalent, supporting clinical usage on both desktop and tablet devices. *(inferred from HTMX usage)*
*   **CSRF Protection:** All HTMX forms must include an `X-CSRFToken` header mapped from cookies.

#### 4.2 Hardware Interface Requirements
*   **CPU:** Kubernetes deployments require a minimum of 500m CPU (reservations) and a limit of 1000m CPU (`values.yaml`).
*   **Memory:** The application requires a minimum of 512Mi memory for ML model loading, with a recommended limit of 1Gi (`values.yaml`).
*   **Storage:** Write access is required to `/app/data` for local SQLite database creation if PostgreSQL is not used.

#### 4.3 Software Interface Requirements
*   **Database:** System must communicate with PostgreSQL or SQLite utilizing SQLAlchemy or native DB-API (sqlite3).
*   **Cache/Rate Limiting:** System interfaces with Redis via `redis://` URLs utilizing the `fastapi-limiter` and `fastapi-cache2` libraries.
*   **OCR Engine:** System must invoke the `tesseract` binary via the `pytesseract` wrapper.

#### 4.4 Communication Interface Requirements
*   **Protocol:** HTTP/1.1 and HTTP/2 supported behind Nginx.
*   **Encryption:** HTTPS must be strictly enforced via Nginx (`return 301 https://$host$request_uri;`).
*   **Data Format:** REST API responses must be formatted as `application/json`.
*   **File Uploads:** Document ingestion endpoints must accept `multipart/form-data`.

---

### 5. NON-FUNCTIONAL REQUIREMENTS

#### 5.1 Performance Requirements
*   **Rate Limiting:** API requests must be limited to 20 requests/second per IP at the Nginx level, and 60 requests/minute at the FastAPI application level.
*   **Prediction Latency:** Prediction endpoints must process requests within the Nginx 30-second proxy read timeout.
*   **Startup Time:** The application must account for up to 120 seconds of cold-start warmup due to model loading into memory (`Dockerfile` Gunicorn timeout).

#### 5.2 Safety Requirements
*   **Medical Disclaimer:** All prediction responses MUST include the standardized disclaimer: *"This prediction is educational decision support, not a diagnosis. Consult a qualified clinician for medical advice."*
*   **Input Validation:** Age, BMI, and other clinical parameters must be strictly bounded (e.g., BMI must be between 10 and 80) via Pydantic validators to prevent model extrapolation errors.

#### 5.3 Security Requirements
*   **Authentication:** Sensitive JSON APIs require an `X-API-Key` header. Web UI relies on JWTs signed with `HS256` using the `JWT_SECRET_KEY`.
*   **Data Encryption:** User passwords must be hashed using bcrypt before database storage.
*   **HTTP Security Headers:** Nginx must enforce `Strict-Transport-Security`, `X-XSS-Protection`, `X-Frame-Options: SAMEORIGIN`, and strict `Content-Security-Policy` directives.
*   **Vulnerability Scanning:** Code must pass `bandit` SAST checks and dependencies must pass `pip-audit`.

#### 5.4 Software Quality Attributes
*   **Test Coverage:** The test suite must maintain a minimum of 70% line coverage (`pyproject.toml` `cov-fail-under=70`), though current system coverage is approximately 41% (`htmlcov/index.html`).
*   **Type Hinting:** Backend code must utilize Python type hints for Pydantic V2 validation compatibility.
*   **Code Formatting:** Code must comply with standard Python linting (inferred usage of Ruff/Black).

#### 5.5 Scalability Requirements
*   **Horizontal Pod Autoscaling (HPA):** Kubernetes deployments must support automatic scaling between 2 and 10 replicas, triggering when CPU utilization reaches 80% (`values.yaml`).
*   **Statelessness:** The FastAPI backend must remain stateless (relying on Redis/Postgres for sessions and rate limits) to allow horizontal scaling.

#### 5.6 Maintainability
*   **Model Versioning:** ML models must be tracked utilizing DVC for large artifact stubs and MLflow for hyperparameter and metrics history.
*   **Telemetry:** Custom Prometheus metrics (e.g., `http_request_duration_seconds`, `model_prediction_probability`) must be exported at the `/metrics` endpoint.

---

### 6. DATABASE REQUIREMENTS

#### 6.1 Entity Descriptions
*(Inferred from `auth/router.py` and `audit_log.py` SQLite schemas)*

*   **User:**
    *   `id` (TEXT, Primary Key)
    *   `email` (TEXT, Unique, Not Null)
    *   `full_name` (TEXT)
    *   `password_hash` (TEXT, Not Null)
    *   `created_at` (TEXT, Not Null)
*   **AuthSession:**
    *   `id` (TEXT, Primary Key)
    *   `user_id` (TEXT, Foreign Key)
    *   `refresh_token_hash` (TEXT, Unique, Not Null)
    *   `user_agent` (TEXT)
    *   `created_at` (TEXT, Not Null)
    *   `expires_at` (TEXT, Not Null)
    *   `revoked` (INTEGER, Default 0)
*   **PredictionAuditLog:**
    *   `id` (INTEGER, Primary Key, Auto Increment)
    *   `request_id` (TEXT)
    *   `user_id` (TEXT)
    *   `disease_model` (TEXT, Not Null)
    *   `source` (TEXT, Not Null)
    *   `risk_percentage` (REAL, Not Null)
    *   `risk_level` (TEXT, Not Null)
    *   `input_json` (TEXT)
    *   `created_at` (TEXT, Not Null)

#### 6.2 Data Dictionary
| Field Name | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `email` | String | Lowercased, Unique | The user's primary login identifier. |
| `risk_percentage`| Float | 0.0 to 100.0 | The continuous probability generated by the ML model. |
| `risk_level` | String | Low, Moderate, High | Categorical representation of risk. |
| `disease_model` | String | Not Null | Identifier for the model (e.g., 'diabetes', 'lung_cancer'). |
| `source` | String | Not Null | Origin of prediction (e.g., 'htmx', 'api', 'api_audit'). |

#### 6.3 Data Retention and Archival
*   Audit logs and session history are persistently stored in the primary database.
*   There are no automated data pruning processes identified in the codebase. Users may manually delete history records via the `/auth/history/{history_id}` endpoint. *(inferred)*

---

### 7. ML SYSTEM REQUIREMENTS

#### 7.1 Data Requirements
*   The system utilizes structured tabular data for inference. The models expect engineered features mimicking established clinical datasets (such as BRFSS).
*   Data preprocessing pipelines are tracked utilizing DVC (`ml/dvc.yaml`).

#### 7.2 Model Training Requirements
*   **Algorithms:** Models utilize XGBoost Classifiers (`diabetes_xgboost.pkl`, `heart_disease_xgboost.pkl`).
*   **Calibration:** Probability outputs must be calibrated using Isotonic Regression (`isotonic_calibrator.pkl`) to ensure predicted probabilities match true risk distributions.
*   **Experiment Tracking:** All training runs must log parameters, metrics, and models to MLflow (`mlruns/`).

#### 7.3 Model Performance Requirements
*   Models must be evaluated using metrics such as AUC-ROC, Accuracy, and F1-Score. *(inferred)*
*   Models must undergo algorithmic fairness checks to evaluate prediction disparities across demographic groups before deployment.

#### 7.4 Model Serving Requirements
*   **Loading:** Models must be loaded asynchronously during application startup utilizing `ModelManager`.
*   **State Tracking:** The application must expose model load states (e.g., `loaded`, `ready`) to prevent routing traffic to uninitialized models.

#### 7.5 Explainability Requirements
*   **SHAP Integration:** The system must generate TreeExplainer SHAP values dynamically to identify which features (e.g., High BMI vs Age) contributed most heavily to the patient's risk score.

---

### 8. DEPLOYMENT REQUIREMENTS

#### 8.1 Container Requirements
*   The system must be packaged as a multi-stage Docker image (`Dockerfile`).
*   The final image must utilize a non-root user (`appuser` UID 1000) for security compliance.
*   Gunicorn must be configured to utilize `UvicornWorker` classes for ASGI compatibility.

#### 8.2 Kubernetes Requirements
*   **Manifests:** The application is deployed utilizing a Helm Chart (`deployment/kubernetes/healthpredict`).
*   **Services:** Must expose internal traffic on port 80/8000 using a `ClusterIP` service.
*   **Ingress:** External access should be managed by an Ingress controller or proxy layer terminating TLS.

#### 8.3 CI/CD Requirements
*   Continuous Integration pipelines must execute the `pytest` test suite, `bandit` SAST scanner, and `pip-audit` vulnerability checks prior to deployment. *(inferred from README)*
*   DVC must be executed (`dvc repro`) to instantiate stub models in CI environments missing full model artifacts.

#### 8.4 Monitoring Requirements
*   **Metrics Exporter:** The FastAPI application must expose Prometheus metrics at `/metrics` (e.g., `http_requests_total`, `http_request_duration_seconds`).
*   **Dashboarding:** Grafana must be provisioned with pre-configured JSON dashboards (`healthpredict.json`) representing request throughput, model latency, and distribution drift.

---

### 9. SYSTEM CONSTRAINTS AND LIMITATIONS
*   **Render Free Tier Limitations:** Memory limits on low-tier hosting providers may cause XGBoost loading to fail (OOM). The `timeout 120` in Gunicorn is a strict workaround.
*   **Tesseract Dependency:** The clinical document parsing feature strictly requires the C++ `tesseract-ocr` binary to be installed on the host OS; it cannot be installed purely via `pip`.
*   **Local Stub Models:** The default models generated by `dvc repro` are randomized stubs designed for CI/CD testing; true production predictive capability requires migrating real weights from an MLflow registry.

---

### 10. APPENDICES

#### Appendix A: Complete API Endpoint Inventory
| Method | Path | Auth Required | Request Schema | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| GET | `/healthz` | Public | None | Liveness JSON |
| GET | `/api/v1/health/ready` | Public | None | Readiness JSON |
| POST | `/api/predict` | API Key | `PredictionRequest` | `PredictionResponse` |
| POST | `/api/predict-heart` | API Key | `HeartDiseasePredictionRequest` | `PredictionResponse` |
| POST | `/api/predict-lung` | API Key | `LungCancerPredictionRequest` | `PredictionResponse` |
| POST | `/api/upload` | API Key | `Multipart/form-data` | Extracted NLP JSON |
| POST | `/auth/register` | Public | `RegisterRequest` | `UserResponse` |
| POST | `/auth/login` | Public | `LoginRequest` | `TokenResponse` |

#### Appendix B: Complete Database Schema
*Refer to Section 6.1 for DDL entity descriptions.*

#### Appendix C: ML Experiment Log
*Note: Due to environment limitations, exact MLflow `metrics.csv` and `params.json` values from `mlruns/` are archived locally and viewable via the `mlflow ui` command.*
Typical parameters logged: `max_depth`, `learning_rate`, `n_estimators`.

#### Appendix D: Test Coverage Summary
*Extracted from `htmlcov/index.html`*
*   **Overall Coverage:** 41%
*   **Total Statements:** 1,638
*   **Covered Statements:** 762
*   **backend/app/main.py Coverage:** 51% (186/367 lines)
*   **backend/app/auth/router.py Coverage:** 54% (98/182 lines)

---
*End of Document*
