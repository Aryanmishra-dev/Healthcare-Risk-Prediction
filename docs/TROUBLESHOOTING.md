# Troubleshooting & MLflow Migration Guide

This document outlines common issues when running the Healthcare Risk Prediction platform with MLflow tracking and the Render production environment.

## Render Cold Starts and Timeouts

> [!WARNING]
> Render's free tier or standard web services spin down after inactivity. On the next request, the server will cold start.
> Since models are fetched from MLflow and warmed up, it may take 10-30 seconds to fully initialize.

**Symptom:** You receive a `502 Bad Gateway` or `504 Gateway Timeout` when first loading the site after a long time.
**Solution:** 
- The `Dockerfile` has been updated with `gunicorn --timeout 120` to prevent the app from killing the worker during model load.
- If you rely on Render health checks, wait ~30 seconds for the `/health` endpoint to turn green.
- If it still fails, ensure your `MLFLOW_TRACKING_URI` is reachable.

## Why Models Go Offline

**Symptom:** Endpoint returns `{"detail": "Diabetes model temporarily offline."}` or `503 Service Unavailable`.
**Reason:** 
- The `ModelManager` singleton failed to load the model during the background warmup task.
- By default, it retries up to 3 times with exponential backoff.
- If the model files/artifacts are missing from the MLflow registry (or `mlruns` dir), the model's status stays `"failed"`.

**Solution:**
1. Check the `/health/models` endpoint for specific loading errors and latency.
2. Run the `python ml/scripts/migrate_to_mlflow.py` script to ensure local MLflow artifacts are generated.
3. If running in production (where `APP_ENV=production`), the server will crash on startup rather than running without models, enforcing a strict health requirement.

## Memory Crashes

**Symptom:** Render deployment fails with `OOM (Out of Memory)` error.
**Reason:** Loading multiple XGBoost and Scikit-Learn models concurrently alongside FastAPI can spike memory usage.
**Solution:**
- Check the startup diagnostics printed in your logs or via `/health/models` to see `memory_usage_mb`.
- If memory exceeds 512MB (Render Free/Starter tier limit), consider upgrading to the standard plan or removing unused models.

## Missing MLflow Artifacts

**Symptom:** MLflow `download_artifacts` fails with `FileNotFoundError` or HTTP 404.
**Solution:**
- The MLflow UI (`mlflow ui`) can be used to inspect if the feature arrays/scalers were uploaded correctly.
- When running the `migrate_to_mlflow.py` script locally, verify that the `mlruns/` directory has proper read/write permissions.

---

## Useful cURL Commands

### Health Checks

**Basic API Health (Liveness)**
```bash
curl -X GET http://localhost:8000/health
```

**Model Health & Diagnostics**
```bash
curl -X GET http://localhost:8000/health/models
```
*Expected output: JSON containing inference readiness, model version, stage, latency, and memory diagnostics.*

**Database Health**
```bash
curl -X GET http://localhost:8000/health/database
```

### Predictions

**Predict Diabetes**
```bash
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "age": 5,
    "bmi": 26.5,
    "bp": 0,
    "cholesterol": 0,
    "smoker": 0,
    "activity": 1,
    "health": 3,
    "mental": 0
  }'
```

**Predict Heart Disease**
```bash
curl -X POST http://localhost:8000/api/predict-heart \
  -H "Content-Type: application/json" \
  -d '{
    "age": 60,
    "sex": 1,
    "bmi": 28.0,
    "high_bp": 1,
    "high_chol": 1,
    "smoker": 1,
    "phys_activity": 0,
    "fruits": 1,
    "veggies": 1,
    "heavy_drinker": 0,
    "gen_health": 4,
    "ment_health": 5,
    "phys_health": 2,
    "diabetes": 0
  }'
```
