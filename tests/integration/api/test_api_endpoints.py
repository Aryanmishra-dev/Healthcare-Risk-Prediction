import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

VALID_API_KEY = "healthpredict_dev_key_2026"

def test_explain_diabetes_json_api(client):
    headers = {"X-API-Key": VALID_API_KEY}
    payload = {
        "age": 7, "bmi": 25.0, "bp": 0, "cholesterol": 0, "smoker": 0,
        "activity": 1, "health": 3, "mental": 0
    }
    response = client.post("/api/v1/explain/diabetes", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "explanation" in data
    assert "features" in data["explanation"]
    assert "shap_values" in data["explanation"]
    assert "base_value" in data["explanation"]

def test_explain_heart_json_api(client):
    headers = {"X-API-Key": VALID_API_KEY}
    payload = {
        "age": 7, "sex": 1, "bmi": 25.0, "high_bp": 0, "high_chol": 0,
        "smoker": 0, "phys_activity": 1, "fruits": 1, "veggies": 1,
        "heavy_drinker": 0, "gen_health": 3, "ment_health": 0,
        "phys_health": 0, "diabetes": 0
    }
    response = client.post("/api/v1/explain/heart", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "explanation" in data

def test_explain_lung_json_api(client):
    headers = {"X-API-Key": VALID_API_KEY}
    payload = {
        "age": 50, "gender": 1, "smoking": 0, "yellow_fingers": 0,
        "chronic_disease": 0, "fatigue": 0, "wheezing": 0, "shortness_of_breath": 0
    }
    response = client.post("/api/v1/explain/lung", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "explanation" in data

def test_api_root():
    # Not using 'client' fixture because this doesn't need models loaded
    with TestClient(app) as local_client:
        response = local_client.get("/api")
        assert response.status_code == 200
        assert response.json()["service"] == "Healthcare Risk Prediction API"

def test_v1_root():
    with TestClient(app) as local_client:
        headers = {"X-API-Key": VALID_API_KEY}
        response = local_client.get("/api/v1/", headers=headers)
        assert response.status_code == 200

def test_v1_model_registry():
    with TestClient(app) as local_client:
        headers = {"X-API-Key": VALID_API_KEY}
        response = local_client.get("/api/v1/models", headers=headers)
        assert response.status_code == 200
        assert "models" in response.json()

def test_healthz():
    with TestClient(app) as local_client:
        response = local_client.get("/healthz")
        assert response.status_code == 200


