# ML Model Weights

This directory stores trained model artefacts (`.pkl` / `.joblib` / `.pt` files).

## Required Files

| File | Model | Purpose |
|------|-------|---------|
| `diabetes_xgboost.pkl` | Diabetes | XGBoost classifier |
| `isotonic_calibrator.pkl` | Diabetes | Probability calibrator |
| `heart_disease_xgboost.pkl` | Heart Disease | XGBoost classifier |
| `heart_disease_calibrator.pkl` | Heart Disease | Probability calibrator |
| `heart_disease_features.pkl` | Heart Disease | Feature name list |
| `lung_cancer_model.pkl` | Lung Cancer | Classifier |
| `lung_cancer_scaler.pkl` | Lung Cancer | Age scaler |
| `lung_cancer_features.pkl` | Lung Cancer | Feature name list |
| `lung_cancer_calibrator.pkl` | Lung Cancer | Probability calibrator (optional) |

## How to Download

Model weights are tracked with DVC and stored in the configured remote:

```bash
dvc pull
```

Or download manually from S3 (requires `AWS_PROFILE` or credentials):

```bash
aws s3 sync s3://$S3_MODEL_BUCKET/ ml/models/
```

## Notes

- These files are **git-ignored** — do NOT commit `.pkl` files to the repo.
- In CI, tests use deterministic stub models (see `tests/unit/ml/conftest.py`).
- In production, missing weights cause the app to crash at startup (`APP_ENV=production`).
