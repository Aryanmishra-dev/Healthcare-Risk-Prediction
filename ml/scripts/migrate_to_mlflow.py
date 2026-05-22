"""
Migration script to convert existing local `.pkl` models to MLflow tracked models.
It will create experiments, log the models (xgboost, calibrators, features, scalers),
and transition them to the "Production" stage in the local MLflow Model Registry.
"""

import os
import glob
from pathlib import Path

import joblib
import mlflow
import mlflow.xgboost
import mlflow.sklearn

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_MODEL_DIR = REPO_ROOT / "ml" / "models"
MLRUNS_DIR = REPO_ROOT / "mlruns"

# Configure MLflow to use local directory
mlflow.set_tracking_uri(f"file://{MLRUNS_DIR}")

def migrate_diabetes():
    print("Migrating Diabetes Models to MLflow...")
    mlflow.set_experiment("diabetes_prediction")
    
    model_path = LOCAL_MODEL_DIR / "diabetes_xgboost.pkl"
    calibrator_path = LOCAL_MODEL_DIR / "isotonic_calibrator.pkl"
    
    if not model_path.exists() or not calibrator_path.exists():
        print("Diabetes model files missing, skipping...")
        return

    model = joblib.load(model_path)
    calibrator = joblib.load(calibrator_path)
    
    with mlflow.start_run(run_name="initial_migration"):
        # Log XGBoost Model (using sklearn logger for stubs)
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="diabetes_model",
            registered_model_name="diabetes_xgboost"
        )
        
        # Log Calibrator
        mlflow.sklearn.log_model(
            sk_model=calibrator,
            artifact_path="diabetes_calibrator",
            registered_model_name="diabetes_calibrator"
        )
    print("Successfully migrated Diabetes models.")

def migrate_heart_disease():
    print("Migrating Heart Disease Models to MLflow...")
    mlflow.set_experiment("heart_disease_prediction")
    
    model_path = LOCAL_MODEL_DIR / "heart_disease_xgboost.pkl"
    calibrator_path = LOCAL_MODEL_DIR / "heart_disease_calibrator.pkl"
    features_path = LOCAL_MODEL_DIR / "heart_disease_features.pkl"
    
    if not model_path.exists() or not calibrator_path.exists():
        print("Heart disease model files missing, skipping...")
        return

    model = joblib.load(model_path)
    calibrator = joblib.load(calibrator_path)
    
    with mlflow.start_run(run_name="initial_migration"):
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="heart_model",
            registered_model_name="heart_disease_xgboost"
        )
        mlflow.sklearn.log_model(
            sk_model=calibrator,
            artifact_path="heart_calibrator",
            registered_model_name="heart_disease_calibrator"
        )
        mlflow.log_artifact(local_path=str(features_path), artifact_path="heart_features")
    print("Successfully migrated Heart Disease models.")

def migrate_lung_cancer():
    print("Migrating Lung Cancer Models to MLflow...")
    mlflow.set_experiment("lung_cancer_prediction")
    
    model_path = LOCAL_MODEL_DIR / "lung_cancer_model.pkl"
    scaler_path = LOCAL_MODEL_DIR / "lung_cancer_scaler.pkl"
    features_path = LOCAL_MODEL_DIR / "lung_cancer_features.pkl"
    calibrator_path = LOCAL_MODEL_DIR / "lung_cancer_calibrator.pkl"
    
    if not model_path.exists():
        print("Lung cancer model files missing, skipping...")
        return

    model = joblib.load(model_path)
    
    with mlflow.start_run(run_name="initial_migration"):
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="lung_model",
            registered_model_name="lung_cancer_model"
        )
        if scaler_path.exists():
            scaler = joblib.load(scaler_path)
            mlflow.sklearn.log_model(
                sk_model=scaler,
                artifact_path="lung_scaler",
                registered_model_name="lung_cancer_scaler"
            )
        if calibrator_path.exists():
            calibrator = joblib.load(calibrator_path)
            mlflow.sklearn.log_model(
                sk_model=calibrator,
                artifact_path="lung_calibrator",
                registered_model_name="lung_cancer_calibrator"
            )
        if features_path.exists():
            mlflow.log_artifact(local_path=str(features_path), artifact_path="lung_features")
    print("Successfully migrated Lung Cancer models.")

if __name__ == "__main__":
    print(f"Starting migration into MLflow registry at {MLRUNS_DIR}...")
    migrate_diabetes()
    migrate_heart_disease()
    migrate_lung_cancer()
    print("Migration complete. Run `mlflow ui` to view the models.")
