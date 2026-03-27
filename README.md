# Healthcare Risk Prediction

An end-to-end, production-grade Machine Learning system designed to predict the risk of **Diabetes**, **Heart Disease**, and **Lung Cancer** based on patient health indicators. 

## What is the Project?
This project is a unified health risk assessment platform. It takes patient telemetry (like BMI, blood pressure, smoking status, and general health metrics) and uses machine learning to provide instant risk probabilities for three major diseases. It features a fast, responsive web interface and a localized AI "Virtual Doctor" that dictates results via text-to-speech.

## What We Achieved
- **High-Accuracy Models**: Deployed three separate models achieving strong predictive power (Diabetes ROC-AUC: 0.87, Heart Disease ROC-AUC: 0.85, Lung Cancer ROC-AUC: 0.97).
- **Explainable AI**: Integrated SHAP (SHapley Additive exPlanations) so doctors and patients can see *exactly* which health factors drove their specific prediction.
- **Production-Ready MLOps**: Built an enterprise-grade backend with FastAPI, secured behind an Nginx reverse proxy with HTTPS, CSRF protection, and Redis-backed rate limiting.
- **Accessibility**: Integrated native web speech APIs to read out clinical predictions to patients.

## The Datasets We Used
- **Diabetes & Heart Disease**: Derived from the massive **CDC BRFSS 2015 dataset** (Behavioral Risk Factor Surveillance System), utilizing over 400,000 real-world patient records.
- **Lung Cancer**: Trained on a specialized clinical survey dataset encompassing key respiratory indicators (wheezing, shortness of breath, chronic fatigue).

## Tech Stack
- **Machine Learning**: XGBoost, Scikit-Learn, SHAP, Isotonic Regression (for probability calibration)
- **Backend & API**: FastAPI, Pydantic, Python 3.12+
- **Frontend**: HTMX, Tailwind CSS, Vanilla JS
- **Infrastructure & MLOps**: Docker, Nginx, Redis, Prometheus/Grafana (Monitoring), DVC (Data Versioning), GitHub Actions (CI/CD)

## Challenges We Faced
- **Data Imbalance**: Medical datasets are fiercely imbalanced (e.g., heavily skewed toward healthy patients). We tackled this using computed `scale_pos_weight` and Isotonic Regression so the models return realistic real-world risk percentages rather than uncalibrated raw scores.
- **Architecture Complexity**: Merging three different models into one cohesive API without blocking the event loop. We designed concurrent, asynchronous wrappers and a unified model loader to handle inference efficiently.
- **Security vs. Speed**: Maintaining a sub-100ms response time while passing the request through HTTPS, an Nginx reverse proxy, a Redis rate limiter, and a SHAP explainer matrix.

---

### Quick Start
Want to run this locally? 
```bash
# 1. Install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Start the local server
bash start.sh
```
Visit `http://127.0.0.1:8000` to interact with the web UI.

---

### Enterprise Deployment (PostgreSQL, AWS S3, Kubernetes)
For Fortune 500 scale, the infrastructure is architected via Terraform and Kubernetes Helm Charts:
- **Terraform:** Navigate to `infrastructure/` and run `terraform apply` to provision a distributed AWS EKS Cluster, an RDS PostgreSQL Database, and an S3 Bucket.
- **S3 Model Storage:** Upload models to your cloud blob via `python scripts/upload_models_to_s3.py --bucket <your-bucket>`. The FastAPI backend will pull them into active memory dynamically at boot if `S3_MODEL_BUCKET` is set in your environment.
- **Kubernetes:** Deploy the completely distributed application utilizing Helm: `helm install healthpredict ./kubernetes/healthpredict`
