# Healthcare Risk Prediction — End-to-End ML Pipeline

A production-grade machine learning system for predicting **diabetes**, **heart disease**, and **lung cancer** risk from patient health indicators. Built with FastAPI, Django, and XGBoost.

> **Status:** Three models live — localhost deployment. API v2.0.0.

---

## Models at a Glance

| Disease | Dataset | Algorithm | ROC AUC | Notes |
|---|---|---|---|---|
| **Diabetes** | CDC BRFSS 2015 (441,456 rows) | XGBoost + Isotonic calibration | 0.879 | Calibrated probabilities, SHAP explanations |
| **Heart Disease** | CDC BRFSS (derived) | XGBoost + calibration | — | 14 clinical features |
| **Lung Cancer** | Survey dataset | XGBoost + StandardScaler | — | 8 symptom/demographic features |

---

## Repository Structure

```
Healthcare_risk_prediction/
│
├── fastapi_backend/
│   ├── main.py                        # FastAPI prediction service (v2.0.0)
│   ├── model_loader.py                # Model loading & inference for all 3 diseases
│   ├── schemas.py                     # Pydantic request/response schemas
│   └── requirements.txt               # Backend-specific dependencies
│
├── django_ui/
│   ├── manage.py                      # Django management script
│   └── risk_ui/
│       ├── settings.py                # Django settings
│       ├── urls.py                    # URL routing
│       ├── views.py                   # Prediction form view
│       └── templates/
│           └── predict.html           # Prediction UI template
│
├── notebooks/
│   ├── brfss_cleaning.ipynb           # Diabetes: cleaning → training → SHAP
│   ├── train_heart_disease_model.ipynb  # Heart disease pipeline
│   └── train_lung_cancer_model.py     # Lung cancer pipeline
│
├── models/
│   ├── diabetes_xgboost.pkl           # Diabetes XGBoost model
│   ├── isotonic_calibrator.pkl        # Diabetes probability calibrator
│   ├── shap_explainer.pkl             # SHAP TreeExplainer (diabetes)
│   ├── heart_disease_xgboost.pkl      # Heart disease XGBoost model
│   ├── heart_disease_calibrator.pkl   # Heart disease calibrator
│   ├── heart_disease_features.pkl     # Heart disease feature list
│   ├── lung_cancer_model.pkl          # Lung cancer XGBoost model
│   ├── lung_cancer_scaler.pkl         # Lung cancer StandardScaler
│   └── lung_cancer_features.pkl       # Lung cancer feature list
│
├── app/
│   └── risk_assistant.py              # CLI + Gradio diabetes risk calculator
│
├── utils/
│   └── feature_engineering.py         # Reusable feature pipeline
│
├── data_raw/                          # Raw BRFSS SAS file (not tracked — 1.1 GB)
├── data_processed/                    # Cleaned CSVs (not tracked)
│
├── retrain.py                         # One-shot retraining script (auto-downloads data)
├── requirements.txt
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
- XGBoost with calibrated probabilities
- Stratified 80/20 split + cross-validation

### Lung Cancer

- 8 features: age, gender, smoking, yellow fingers, chronic disease, fatigue, wheezing, shortness of breath
- XGBoost + StandardScaler pipeline
- Multi-model comparison (Logistic Regression, RF, SVM, KNN, Naive Bayes, GBM, XGBoost) with GridSearchCV tuning

---

## API Endpoints

All endpoints accept POST requests with JSON bodies. Swagger UI: `http://127.0.0.1:8000/api/docs`

| Endpoint | Disease | Schema fields |
|---|---|---|
| `POST /api/predict` | Diabetes | `age`, `bmi`, `bp`, `cholesterol`, `smoker`, `activity`, `health`, `mental` |
| `POST /api/predict-heart` | Heart Disease | `age`, `sex`, `bmi`, `high_bp`, `high_chol`, `smoker`, `phys_activity`, `fruits`, `veggies`, `heavy_drinker`, `gen_health`, `ment_health`, `phys_health`, `diabetes` |
| `POST /api/predict-lung` | Lung Cancer | `age`, `gender`, `smoking`, `yellow_fingers`, `chronic_disease`, `fatigue`, `wheezing`, `shortness_of_breath` |

**Response format (all endpoints):**
```json
{
  "risk_percent": 72.0,
  "risk_level": "HIGH"
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

### Train Models

**Option A — Automated retraining script (downloads BRFSS data automatically):**
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

### Diabetes Risk Calculator (CLI / Gradio)
```bash
# CLI mode
python app/risk_assistant.py

# Gradio web UI (requires: pip install gradio)
python app/risk_assistant.py --ui
```

**Sample output:**
```
====================================================
   DIABETES RISK ASSESSMENT
====================================================

   Estimated Diabetes Risk : 0.72  (72.0%)
   Risk Level              : HIGH
   Model Confidence        : calibrated probability
   (Raw model score        : 0.31)

   Top Contributing Factors:
   ------------------------------------------
   + Bmi Age..........................  43.5%
   + Age Group........................  13.2%
   + General Health...................  11.3%
   + Health Bmi.......................   8.8%
   + Chol Bmi.........................   5.1%

====================================================
```

### FastAPI + Django (Web Deployment)

**Terminal 1 — FastAPI prediction API:**
```bash
uvicorn fastapi_backend.main:app --reload --port 8000
```
Swagger docs: http://127.0.0.1:8000/api/docs

**Terminal 2 — Django UI:**
```bash
cd django_ui
python manage.py runserver 8001
```
Open http://127.0.0.1:8001 in your browser.

**Or use the convenience script:**
```bash
bash start.sh
```

### System Architecture
```
User Browser
      │
      ▼
Django UI (port 8001)   →   Form input / result display
      │
      ▼
FastAPI API (port 8000) →   ML inference / JSON response
      │
      ├── diabetes_xgboost.pkl + isotonic_calibrator.pkl
      ├── heart_disease_xgboost.pkl + heart_disease_calibrator.pkl
      └── lung_cancer_model.pkl + lung_cancer_scaler.pkl
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| ML | XGBoost 3.2, scikit-learn 1.8, SHAP 0.51 |
| Data | pandas 3.0, NumPy 2.4, pyreadstat |
| API | FastAPI 0.135, Uvicorn 0.41, Pydantic 2.12 |
| UI | Django 6.0 |
| Visualisation | matplotlib 3.10, seaborn 0.13 |
| Serialisation | joblib 1.5 |
| Optional | Gradio (interactive local UI) |

---

## Evaluation Strategy

- Stratified 80/20 train-test split across all models
- 5-fold cross-validation (Diabetes: Mean AUC 0.860 ± 0.010)
- Confusion matrix, precision/recall/F1, ROC-AUC
- ROC curve comparison across model families
- **Reliability diagram** — calibration curve + Brier score
- SHAP global feature importance + per-patient local explanations

---

## Security

- **Rate limiting** — 60 requests/minute per IP (configurable via `RATE_LIMIT_PER_MINUTE` env var)
- **CORS** — restricted to localhost origins by default (configurable via `CORS_ORIGINS` env var)
- Input validation enforced by Pydantic schemas on all endpoints

---

## Author

**Aryan Mishra**  
Data Science Student — focused on ML Engineering & Deployment

---

## License

This project is for educational and portfolio purposes.
