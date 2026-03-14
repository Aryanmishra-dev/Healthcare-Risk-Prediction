"""Tests for the FastAPI JSON API + HTMX endpoints.

Covers:
  - Root/info endpoints & OpenAPI spec
  - JSON API: all 3 disease predictions (valid, invalid, boundary, schema)
  - HTMX endpoints: all 3 form-based predictions
  - Rate limiting middleware
  - CORS headers
  - Pydantic schema validation edge cases
"""

import pytest
from unittest.mock import patch


# ── Root & Info ────────────────────────────────────────────────────────────

class TestRootEndpoints:
    def test_homepage_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "HealthPredict" in resp.text

    def test_homepage_content_type_html(self, client):
        resp = client.get("/")
        assert "text/html" in resp.headers["content-type"]

    def test_api_root(self, client):
        resp = client.get("/api")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "running"
        assert set(body["models"]) == {"diabetes", "heart_disease", "lung_cancer"}

    def test_swagger_docs(self, client):
        resp = client.get("/api/docs")
        assert resp.status_code == 200

    def test_openapi_json(self, client):
        resp = client.get("/api/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        assert "paths" in spec
        assert "/api/predict" in spec["paths"]
        assert "/api/predict-heart" in spec["paths"]
        assert "/api/predict-lung" in spec["paths"]

    def test_nonexistent_route_returns_404(self, client):
        resp = client.get("/nonexistent")
        assert resp.status_code == 404


# ── Diabetes JSON API ─────────────────────────────────────────────────────

class TestDiabetesAPI:
    VALID_PAYLOAD = {
        "age": 7, "bmi": 25.0, "bp": 0, "cholesterol": 0,
        "smoker": 0, "activity": 1, "health": 3, "mental": 0,
    }

    def test_predict_returns_200(self, client):
        resp = client.post("/api/predict", json=self.VALID_PAYLOAD)
        assert resp.status_code == 200

    def test_response_schema(self, client):
        resp = client.post("/api/predict", json=self.VALID_PAYLOAD)
        body = resp.json()
        assert "risk_percentage" in body
        assert "risk_level" in body
        assert isinstance(body["risk_percentage"], float)
        assert body["risk_level"] in ("Low", "Moderate", "High")

    def test_risk_percentage_range(self, client):
        resp = client.post("/api/predict", json=self.VALID_PAYLOAD)
        pct = resp.json()["risk_percentage"]
        assert 0.0 <= pct <= 100.0

    def test_high_risk_patient(self, client):
        payload = {
            "age": 13, "bmi": 45.0, "bp": 1, "cholesterol": 1,
            "smoker": 1, "activity": 0, "health": 5, "mental": 30,
        }
        resp = client.post("/api/predict", json=payload)
        body = resp.json()
        assert body["risk_percentage"] > 10

    def test_low_risk_patient(self, client):
        payload = {
            "age": 1, "bmi": 22.0, "bp": 0, "cholesterol": 0,
            "smoker": 0, "activity": 1, "health": 1, "mental": 0,
        }
        resp = client.post("/api/predict", json=payload)
        assert resp.json()["risk_level"] == "Low"

    def test_invalid_age_too_high(self, client):
        bad = {**self.VALID_PAYLOAD, "age": 99}
        resp = client.post("/api/predict", json=bad)
        assert resp.status_code == 422

    def test_invalid_age_too_low(self, client):
        bad = {**self.VALID_PAYLOAD, "age": 0}
        resp = client.post("/api/predict", json=bad)
        assert resp.status_code == 422

    def test_invalid_bmi_zero(self, client):
        bad = {**self.VALID_PAYLOAD, "bmi": 0}
        resp = client.post("/api/predict", json=bad)
        assert resp.status_code == 422

    def test_invalid_bmi_negative(self, client):
        bad = {**self.VALID_PAYLOAD, "bmi": -5}
        resp = client.post("/api/predict", json=bad)
        assert resp.status_code == 422

    def test_invalid_mental_health_over_30(self, client):
        bad = {**self.VALID_PAYLOAD, "mental": 31}
        resp = client.post("/api/predict", json=bad)
        assert resp.status_code == 422

    def test_missing_field_rejected(self, client):
        incomplete = {"age": 7, "bmi": 25.0}
        resp = client.post("/api/predict", json=incomplete)
        assert resp.status_code == 422

    def test_empty_body_rejected(self, client):
        resp = client.post("/api/predict", json={})
        assert resp.status_code == 422

    def test_boundary_age_min(self, client):
        payload = {**self.VALID_PAYLOAD, "age": 1}
        resp = client.post("/api/predict", json=payload)
        assert resp.status_code == 200

    def test_boundary_age_max(self, client):
        payload = {**self.VALID_PAYLOAD, "age": 13}
        resp = client.post("/api/predict", json=payload)
        assert resp.status_code == 200

    def test_boundary_health_min(self, client):
        payload = {**self.VALID_PAYLOAD, "health": 1}
        resp = client.post("/api/predict", json=payload)
        assert resp.status_code == 200

    def test_boundary_health_max(self, client):
        payload = {**self.VALID_PAYLOAD, "health": 5}
        resp = client.post("/api/predict", json=payload)
        assert resp.status_code == 200

    def test_response_content_type_json(self, client):
        resp = client.post("/api/predict", json=self.VALID_PAYLOAD)
        assert "application/json" in resp.headers["content-type"]

    def test_deterministic_response(self, client):
        r1 = client.post("/api/predict", json=self.VALID_PAYLOAD).json()
        r2 = client.post("/api/predict", json=self.VALID_PAYLOAD).json()
        assert r1["risk_percentage"] == r2["risk_percentage"]

    def test_wrong_http_method(self, client):
        resp = client.get("/api/predict")
        assert resp.status_code == 405


# ── Heart Disease JSON API ────────────────────────────────────────────────

class TestHeartDiseaseAPI:
    VALID_PAYLOAD = {
        "age": 7, "sex": 1, "bmi": 25.0, "high_bp": 0, "high_chol": 0,
        "smoker": 0, "phys_activity": 1, "fruits": 1, "veggies": 1,
        "heavy_drinker": 0, "gen_health": 3, "ment_health": 0,
        "phys_health": 0, "diabetes": 0,
    }

    def test_predict_returns_200(self, client):
        resp = client.post("/api/predict-heart", json=self.VALID_PAYLOAD)
        assert resp.status_code == 200

    def test_response_schema(self, client):
        resp = client.post("/api/predict-heart", json=self.VALID_PAYLOAD)
        body = resp.json()
        assert "risk_percentage" in body
        assert body["risk_level"] in ("Low", "Moderate", "High")

    def test_risk_percentage_range(self, client):
        resp = client.post("/api/predict-heart", json=self.VALID_PAYLOAD)
        pct = resp.json()["risk_percentage"]
        assert 0.0 <= pct <= 100.0

    def test_invalid_sex_rejected(self, client):
        bad = {**self.VALID_PAYLOAD, "sex": 5}
        resp = client.post("/api/predict-heart", json=bad)
        assert resp.status_code == 422

    def test_invalid_gen_health_too_high(self, client):
        bad = {**self.VALID_PAYLOAD, "gen_health": 10}
        resp = client.post("/api/predict-heart", json=bad)
        assert resp.status_code == 422

    def test_invalid_phys_health_negative(self, client):
        bad = {**self.VALID_PAYLOAD, "phys_health": -1}
        resp = client.post("/api/predict-heart", json=bad)
        assert resp.status_code == 422

    def test_missing_field_rejected(self, client):
        incomplete = {"age": 7, "sex": 1}
        resp = client.post("/api/predict-heart", json=incomplete)
        assert resp.status_code == 422

    def test_high_risk_patient(self, client):
        payload = {
            "age": 13, "sex": 1, "bmi": 42.0, "high_bp": 1, "high_chol": 1,
            "smoker": 1, "phys_activity": 0, "fruits": 0, "veggies": 0,
            "heavy_drinker": 1, "gen_health": 5, "ment_health": 30,
            "phys_health": 30, "diabetes": 1,
        }
        resp = client.post("/api/predict-heart", json=payload)
        assert resp.json()["risk_percentage"] > 5

    def test_deterministic_response(self, client):
        r1 = client.post("/api/predict-heart", json=self.VALID_PAYLOAD).json()
        r2 = client.post("/api/predict-heart", json=self.VALID_PAYLOAD).json()
        assert r1["risk_percentage"] == r2["risk_percentage"]

    def test_wrong_http_method(self, client):
        resp = client.get("/api/predict-heart")
        assert resp.status_code == 405


# ── Lung Cancer JSON API ─────────────────────────────────────────────────

class TestLungCancerAPI:
    VALID_PAYLOAD = {
        "age": 50, "gender": 1, "smoking": 0, "yellow_fingers": 0,
        "chronic_disease": 0, "fatigue": 0, "wheezing": 0,
        "shortness_of_breath": 0,
    }

    def test_predict_returns_200(self, client):
        resp = client.post("/api/predict-lung", json=self.VALID_PAYLOAD)
        assert resp.status_code == 200

    def test_response_schema(self, client):
        resp = client.post("/api/predict-lung", json=self.VALID_PAYLOAD)
        body = resp.json()
        assert "risk_percentage" in body
        assert body["risk_level"] in ("Low", "Moderate", "High")

    def test_risk_percentage_range(self, client):
        resp = client.post("/api/predict-lung", json=self.VALID_PAYLOAD)
        pct = resp.json()["risk_percentage"]
        assert 0.0 <= pct <= 100.0

    def test_invalid_age_under_18(self, client):
        bad = {**self.VALID_PAYLOAD, "age": 5}
        resp = client.post("/api/predict-lung", json=bad)
        assert resp.status_code == 422

    def test_invalid_age_over_100(self, client):
        bad = {**self.VALID_PAYLOAD, "age": 150}
        resp = client.post("/api/predict-lung", json=bad)
        assert resp.status_code == 422

    def test_invalid_gender_value(self, client):
        bad = {**self.VALID_PAYLOAD, "gender": 3}
        resp = client.post("/api/predict-lung", json=bad)
        assert resp.status_code == 422

    def test_missing_field_rejected(self, client):
        incomplete = {"age": 50, "gender": 1}
        resp = client.post("/api/predict-lung", json=incomplete)
        assert resp.status_code == 422

    def test_boundary_age_min(self, client):
        payload = {**self.VALID_PAYLOAD, "age": 18}
        resp = client.post("/api/predict-lung", json=payload)
        assert resp.status_code == 200

    def test_boundary_age_max(self, client):
        payload = {**self.VALID_PAYLOAD, "age": 100}
        resp = client.post("/api/predict-lung", json=payload)
        assert resp.status_code == 200

    def test_deterministic_response(self, client):
        r1 = client.post("/api/predict-lung", json=self.VALID_PAYLOAD).json()
        r2 = client.post("/api/predict-lung", json=self.VALID_PAYLOAD).json()
        assert r1["risk_percentage"] == r2["risk_percentage"]

    def test_wrong_http_method(self, client):
        resp = client.get("/api/predict-lung")
        assert resp.status_code == 405


# ── HTMX Endpoints ────────────────────────────────────────────────────────

class TestHTMXEndpoints:
    def test_diabetes_htmx_returns_html(self, client):
        resp = client.post("/predict/diabetes", data={
            "age": "7", "bmi": "25.0", "bp": "0", "cholesterol": "0",
            "smoker": "0", "activity": "1", "health": "3", "mental": "0",
        }, cookies={"csrf_token": "test"}, headers={"X-CSRFToken": "test"})
        assert resp.status_code == 200
        assert "Risk" in resp.text
        assert "text/html" in resp.headers["content-type"]

    def test_heart_htmx_returns_html(self, client):
        resp = client.post("/predict/heart", data={
            "hd_age": "7", "hd_sex": "1", "hd_bmi": "25.0",
            "hd_high_bp": "0", "hd_high_chol": "0", "hd_smoker": "0",
            "hd_phys_activity": "1", "hd_fruits": "1", "hd_veggies": "1",
            "hd_heavy_drinker": "0", "hd_gen_health": "3",
            "hd_ment_health": "0", "hd_phys_health": "0", "hd_diabetes": "0",
        }, cookies={"csrf_token": "test"}, headers={"X-CSRFToken": "test"})
        assert resp.status_code == 200
        assert "Risk" in resp.text

    def test_lung_htmx_returns_html(self, client):
        resp = client.post("/predict/lung", data={
            "lc_age": "50", "lc_gender": "1", "lc_smoking": "0",
            "lc_yellow_fingers": "0", "lc_chronic_disease": "0",
            "lc_fatigue": "0", "lc_wheezing": "0",
            "lc_shortness_of_breath": "0",
        }, cookies={"csrf_token": "test"}, headers={"X-CSRFToken": "test"})
        assert resp.status_code == 200
        assert "Risk" in resp.text

    def test_diabetes_htmx_gauge_content(self, client):
        resp = client.post("/predict/diabetes", data={
            "age": "7", "bmi": "25.0", "bp": "0", "cholesterol": "0",
            "smoker": "0", "activity": "1", "health": "3", "mental": "0",
        }, cookies={"csrf_token": "test"}, headers={"X-CSRFToken": "test"})
        assert "%" in resp.text

    def test_htmx_high_risk_returns_result(self, client):
        resp = client.post("/predict/diabetes", data={
            "age": "13", "bmi": "45.0", "bp": "1", "cholesterol": "1",
            "smoker": "1", "activity": "0", "health": "5", "mental": "30",
        }, cookies={"csrf_token": "test"}, headers={"X-CSRFToken": "test"})
        assert resp.status_code == 200
        assert "Risk" in resp.text


# ── Rate Limiting ─────────────────────────────────────────────────────────

class TestRateLimiting:
    @pytest.mark.skip(reason="Rate limiting now uses Redis via fastapi_limiter")
    def test_rate_limit_returns_429(self, client):
        """When rate limit is set to 2, the third request should be rejected."""
        pass


# ── CORS & Security ───────────────────────────────────────────────────────

class TestCORSSecurity:
    def test_cors_allowed_origin(self, client):
        resp = client.options(
            "/api/predict",
            headers={
                "Origin": "http://localhost:8000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.status_code == 200

    def test_post_only_on_predict_endpoints(self, client):
        for path in ["/api/predict", "/api/predict-heart", "/api/predict-lung"]:
            resp = client.get(path)
            assert resp.status_code == 405


# ── Pydantic Schema Validation ────────────────────────────────────────────

class TestSchemaValidation:
    def test_diabetes_string_type_rejected(self, client):
        bad = {"age": "seven", "bmi": 25, "bp": 0, "cholesterol": 0,
               "smoker": 0, "activity": 1, "health": 3, "mental": 0}
        resp = client.post("/api/predict", json=bad)
        assert resp.status_code == 422

    def test_heart_float_sex_coerced(self, client):
        payload = {
            "age": 7, "sex": 1.0, "bmi": 25.0, "high_bp": 0, "high_chol": 0,
            "smoker": 0, "phys_activity": 1, "fruits": 1, "veggies": 1,
            "heavy_drinker": 0, "gen_health": 3, "ment_health": 0,
            "phys_health": 0, "diabetes": 0,
        }
        resp = client.post("/api/predict-heart", json=payload)
        assert resp.status_code == 200

    def test_lung_null_field_rejected(self, client):
        bad = {"age": 50, "gender": None, "smoking": 0, "yellow_fingers": 0,
               "chronic_disease": 0, "fatigue": 0, "wheezing": 0,
               "shortness_of_breath": 0}
        resp = client.post("/api/predict-lung", json=bad)
        assert resp.status_code == 422

    def test_422_response_has_detail(self, client):
        resp = client.post("/api/predict", json={})
        assert resp.status_code == 422
        body = resp.json()
        assert "detail" in body
        assert len(body["detail"]) > 0
