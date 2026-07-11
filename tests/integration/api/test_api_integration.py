import os
import sqlite3
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))

@pytest.fixture(scope="module")
def client():
    # Using TestClient within a context manager triggers the lifespan events (loads models)
    with TestClient(app) as c:
        yield c

# Test API key
VALID_API_KEY = os.environ.get("DEV_API_KEY", "test-dev-api-key")
INVALID_API_KEY = "wrong_key_123"

# Common test payloads
DIABETES_PAYLOAD = {
    "age": 7,
    "bmi": 25.0,
    "bp": 0,
    "cholesterol": 0,
    "smoker": 0,
    "activity": 1,
    "health": 3,
    "mental": 0
}

HEART_PAYLOAD = {
    "age": 7,
    "sex": 1,
    "bmi": 25.0,
    "high_bp": 0,
    "high_chol": 0,
    "smoker": 0,
    "phys_activity": 1,
    "fruits": 1,
    "veggies": 1,
    "heavy_drinker": 0,
    "gen_health": 3,
    "ment_health": 0,
    "phys_health": 0,
    "diabetes": 0
}

LUNG_PAYLOAD = {
    "age": 50,
    "gender": 1,
    "smoking": 0,
    "yellow_fingers": 0,
    "chronic_disease": 0,
    "fatigue": 0,
    "wheezing": 0,
    "shortness_of_breath": 0
}


class TestAPIAuthentication:
    """Test functionality of API key authentication on v1 endpoints."""

    def test_json_api_requires_auth(self, client):
        """Verify that JSON API endpoints reject requests without API key."""
        endpoints = [
            "/api/v1/predict/diabetes",
            "/api/v1/predict/heart",
            "/api/v1/predict/lung",
            "/api/v1/explain/diabetes",
        ]
        
        for endpoint in endpoints:
            # We just need to send basic valid JSON shapes; it should fail on auth first
            payload = DIABETES_PAYLOAD if "diabetes" in endpoint else (HEART_PAYLOAD if "heart" in endpoint else LUNG_PAYLOAD)
            
            response = client.post(endpoint, json=payload)
            assert response.status_code == 401
            assert response.json()["detail"] == "Invalid or missing API Key"

    def test_json_api_rejects_invalid_key(self, client):
        """Verify that JSON API endpoints reject invalid API keys."""
        headers = {"X-API-Key": INVALID_API_KEY}
        response = client.post("/api/v1/predict/diabetes", json=DIABETES_PAYLOAD, headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or missing API Key"

    def test_json_api_accepts_valid_key(self, client):
        """Verify that JSON API endpoints accept valid API keys."""
        headers = {"X-API-Key": VALID_API_KEY}
        
        # Test Diabetes
        resp_diab = client.post("/api/v1/predict/diabetes", json=DIABETES_PAYLOAD, headers=headers)
        assert resp_diab.status_code == 200
        assert "risk_percentage" in resp_diab.json()
        
        # Test Heart
        resp_heart = client.post("/api/v1/predict/heart", json=HEART_PAYLOAD, headers=headers)
        assert resp_heart.status_code == 200
        assert "risk_percentage" in resp_heart.json()
        
        # Test Lung
        resp_lung = client.post("/api/v1/predict/lung", json=LUNG_PAYLOAD, headers=headers)
        assert resp_lung.status_code == 200
        assert "risk_percentage" in resp_lung.json()

    def test_htmx_endpoints_do_not_require_auth(self, client):
        """Verify that UI (HTMX) endpoints are still accessible without API keys."""
        # HTMX endpoints use form data
        form_data = {
            "age": 7, "bmi": 25.0, "bp": 0, "cholesterol": 0, "smoker": 0,
            "activity": 1, "health": 3, "mental": 0
        }
        response = client.post("/predict/diabetes", data=form_data, cookies={"csrf_token": "test"}, headers={"X-CSRFToken": "test"})
        assert response.status_code == 200
        # Should return HTML
        assert "text/html" in response.headers["content-type"]
        assert "Risk" in response.text


class TestAuditLogging:
    """Test functionality of prediction audit logging."""
    
    def get_latest_log(self):
        import asyncio
        from sqlalchemy import select
        from tests.conftest import TestingSessionLocal
        from backend.app.models.prediction import PredictionAuditLog
        
        async def _get():
            async with TestingSessionLocal() as session:
                stmt = select(PredictionAuditLog).order_by(PredictionAuditLog.id.desc()).limit(1)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
        
        row = asyncio.run(_get())
        if row:
            return {"disease_model": row.disease_model, "source": row.source, "risk_percentage": row.risk_percentage}
        return None

    def test_json_api_logs_prediction(self, client):
        """Verify that a successful JSON API request creates a log entry."""
        headers = {"X-API-Key": VALID_API_KEY}
        client.post("/api/v1/predict/diabetes", json=DIABETES_PAYLOAD, headers=headers)
        
        log = self.get_latest_log()
        assert log is not None
        assert log["disease_model"] == "diabetes"
        assert log["source"] == "api_v1"
        assert isinstance(log["risk_percentage"], float)

    def test_htmx_api_logs_prediction(self, client):
        """Verify that a successful HTMX form request creates a log entry."""
        form_data = {
            "lc_age": 50, "lc_gender": 1, "lc_smoking": 1,
            "lc_yellow_fingers": 0, "lc_chronic_disease": 0,
            "lc_fatigue": 0, "lc_wheezing": 0, "lc_shortness_of_breath": 0
        }
        client.post("/predict/lung", data=form_data, cookies={"csrf_token": "test"}, headers={"X-CSRFToken": "test"})
        
        log = self.get_latest_log()
        assert log is not None
        assert log["disease_model"] == "lung_cancer"
        assert log["source"] == "htmx"


class TestPrometheusMetrics:
    """Test new Prometheus custom metrics."""

    def test_metrics_endpoint_has_prediction_histogram(self, client):
        """Verify the custom /metrics endpoint exports the expected prediction histograms."""
        headers = {"X-API-Key": VALID_API_KEY}
        client.post("/api/v1/predict/heart", json=HEART_PAYLOAD, headers=headers)
        
        response = client.get("/metrics")
        assert response.status_code == 200
        
        text = response.text
        assert "model_prediction_probability_bucket" in text
        assert 'model_name="heart_disease"' in text
