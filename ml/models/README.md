# ML Model Weights

This directory stores model artifacts (`.pkl` / `.joblib` / `.pt` files).
The small files committed in this repository are deterministic stubs used for
local launch, tests, and Docker smoke checks. Replace them with real trained
artifacts from the configured DVC remote for production model quality.

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

## How to Regenerate Local Stubs

```bash
python -m ml.models.generate_stubs
```

Or through DVC:

```bash
dvc repro ml/dvc.yaml
```

## How to Download Real Artifacts

Real model weights should be tracked with DVC and stored in the configured
remote:

```bash
dvc remote add -d <name> <remote-url>
dvc pull
```

Or download manually from S3 (requires `AWS_PROFILE` or credentials):

```bash
aws s3 sync s3://$S3_MODEL_BUCKET/ ml/models/
```

## Notes

- Keep only tiny deterministic stubs in Git. Do NOT commit large trained
  `.pkl` files to the repo.
- In CI, tests use deterministic stub models (see `tests/unit/ml/conftest.py`).
- In production, missing weights cause the app to crash at startup (`APP_ENV=production`).
