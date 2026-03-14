"""Tests for new infrastructure: versioned API, model registry, monitoring,
A/B testing, feature store, and SHAP endpoints."""

import json
import os

import pytest


# ══════════════════════════════════════════════════════════════════════════
#  Versioned API (/api/v1/)
# ══════════════════════════════════════════════════════════════════════════

class TestVersionedAPI:
    def test_v1_root(self, client):
        resp = client.get("/api/v1/", headers={"X-API-Key": "healthpredict_dev_key_2026"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["version"] == "v1"
        assert body["status"] == "running"

    def test_v1_predict_diabetes(self, client):
        resp = client.post("/api/v1/predict/diabetes", json={
            "age": 7, "bmi": 25.0, "bp": 0, "cholesterol": 0,
            "smoker": 0, "activity": 1, "health": 3, "mental": 0,
        }, headers={"X-API-Key": "healthpredict_dev_key_2026"})
        assert resp.status_code == 200
        body = resp.json()
        assert "risk_percentage" in body
        assert "risk_level" in body

    def test_v1_predict_heart(self, client):
        resp = client.post("/api/v1/predict/heart", json={
            "age": 7, "sex": 1, "bmi": 25.0, "high_bp": 0, "high_chol": 0,
            "smoker": 0, "phys_activity": 1, "fruits": 1, "veggies": 1,
            "heavy_drinker": 0, "gen_health": 3, "ment_health": 0,
            "phys_health": 0, "diabetes": 0,
        }, headers={"X-API-Key": "healthpredict_dev_key_2026"})
        assert resp.status_code == 200
        body = resp.json()
        assert "risk_percentage" in body

    def test_v1_predict_lung(self, client):
        resp = client.post("/api/v1/predict/lung", json={
            "age": 50, "gender": 1, "smoking": 0, "yellow_fingers": 0,
            "chronic_disease": 0, "fatigue": 0, "wheezing": 0,
            "shortness_of_breath": 0,
        }, headers={"X-API-Key": "healthpredict_dev_key_2026"})
        assert resp.status_code == 200
        body = resp.json()
        assert "risk_percentage" in body

    @pytest.mark.skip(reason="Event loop issues with TestClient and Redis")
    def test_v1_backwards_compat(self, client):
        """Old /api/predict still works alongside /api/v1/predict/diabetes."""
        pass


# ══════════════════════════════════════════════════════════════════════════
#  Model Registry
# ══════════════════════════════════════════════════════════════════════════

class TestModelRegistry:
    def test_registry_endpoint(self, client):
        resp = client.get("/api/v1/models", headers={"X-API-Key": "healthpredict_dev_key_2026"})
        assert resp.status_code == 200
        body = resp.json()
        assert "registry_version" in body
        assert "models" in body
        assert "diabetes_xgboost" in body["models"]
        assert "heart_disease_xgboost" in body["models"]
        assert "lung_cancer_logreg" in body["models"]

    def test_registry_does_not_expose_hashes(self, client):
        resp = client.get("/api/v1/models", headers={"X-API-Key": "healthpredict_dev_key_2026"})
        body = resp.json()
        # SHA-256 hashes should NOT be in the public response
        for model_info in body["models"].values():
            assert "sha256" not in model_info

    def test_registry_file_valid_json(self):
        registry_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "models", "model_registry.json",
        )
        with open(registry_path) as f:
            data = json.load(f)
        assert "models" in data
        for model in data["models"].values():
            assert "version" in model
            assert "algorithm" in model
            assert "status" in model

    def test_registry_verify_script(self):
        """model_registry.py verify should return 0 (all hashes match)."""
        import subprocess
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            ["python", "scripts/model_registry.py", "verify"],
            cwd=root, capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "MISMATCH" not in result.stdout


# ══════════════════════════════════════════════════════════════════════════
#  Monitoring & Health
# ══════════════════════════════════════════════════════════════════════════

class TestMonitoring:
    def test_healthz(self, client):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_prometheus_metrics_endpoint(self, client):
        # Hit an endpoint first so metrics are generated
        client.get("/api")
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "http_request" in resp.text or "http_requests" in resp.text


# ══════════════════════════════════════════════════════════════════════════
#  Security Headers & Middleware
# ══════════════════════════════════════════════════════════════════════════

class TestSecurityHeaders:
    def test_request_id_header_present(self, client):
        """Every response should include an X-Request-ID header."""
        resp = client.get("/healthz")
        assert "X-Request-ID" in resp.headers
        # Should be a valid UUID-like string
        assert len(resp.headers["X-Request-ID"]) >= 32

    def test_request_id_preserved_when_sent(self, client):
        """If client sends X-Request-ID, server should echo it back."""
        custom_id = "test-request-12345"
        resp = client.get("/healthz", headers={"X-Request-ID": custom_id})
        assert resp.headers["X-Request-ID"] == custom_id

    def test_cors_rejects_disallowed_origin(self, client):
        """CORS should reject requests from unlisted origins."""
        resp = client.options(
            "/api/predict",
            headers={
                "Origin": "https://evil-site.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        # Should NOT include the evil origin in allow-origin
        allow_origin = resp.headers.get("access-control-allow-origin", "")
        assert "evil-site.com" not in allow_origin

    @pytest.mark.skip(reason="Rate limiting now uses Redis via fastapi_limiter")
    def test_rate_limiting_returns_429(self, client):
        """Exceeding rate limit should return 429 status."""
        pass


# ══════════════════════════════════════════════════════════════════════════
#  Production Readiness
# ══════════════════════════════════════════════════════════════════════════

class TestProductionReadiness:
    def test_readiness_endpoint(self, client):
        """Readiness probe should confirm models are loaded."""
        resp = client.get("/api/v1/health/ready", headers={"X-API-Key": "healthpredict_dev_key_2026"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"

    def test_nginx_config_exists(self):
        """Nginx production config file should exist."""
        nginx_conf = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "nginx", "nginx.conf",
        )
        assert os.path.isfile(nginx_conf), "nginx/nginx.conf not found"

    def test_nginx_dev_config_exists(self):
        """Nginx development config file should exist."""
        nginx_conf = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "nginx", "nginx.dev.conf",
        )
        assert os.path.isfile(nginx_conf), "nginx/nginx.dev.conf not found"

    def test_docker_compose_no_exposed_backend_port(self):
        """docker-compose.yml should NOT publish port 8000 to host."""
        compose_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docker-compose.yml",
        )
        with open(compose_path) as f:
            content = f.read()
        # The web service should use 'expose' not 'ports' for 8000
        # Check that "8000:8000" is NOT in the file (direct port mapping)
        assert '"8000:8000"' not in content, "Port 8000 should not be published to host"

    def test_security_md_exists(self):
        """SECURITY.md documentation should exist."""
        sec_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "SECURITY.md",
        )
        assert os.path.isfile(sec_path), "SECURITY.md not found"


# ══════════════════════════════════════════════════════════════════════════
#  Structured Logging
# ══════════════════════════════════════════════════════════════════════════

class TestStructuredLogging:
    def test_setup_logging_does_not_crash(self):
        from app.logging_config import setup_logging
        setup_logging()  # should be idempotent

    def test_get_logger(self):
        from app.logging_config import get_logger
        logger = get_logger("test_module")
        assert logger is not None


# ══════════════════════════════════════════════════════════════════════════
#  A/B Testing Framework
# ══════════════════════════════════════════════════════════════════════════

class TestABTesting:
    def test_register_experiment(self):
        from app.ab_testing import ABRouter
        router = ABRouter()
        router.register(
            "test_model",
            champion_fn=lambda: {"risk_percentage": 10, "risk_level": "Low"},
            challenger_fn=lambda: {"risk_percentage": 15, "risk_level": "Low"},
            traffic_pct=50,
        )
        assert "test_model" in router.active_experiments

    def test_route_returns_result(self):
        from app.ab_testing import ABRouter
        router = ABRouter()
        router.register(
            "test_model",
            champion_fn=lambda: {"risk_percentage": 10, "risk_level": "Low"},
            challenger_fn=lambda: {"risk_percentage": 15, "risk_level": "Low"},
            traffic_pct=50,
        )
        result, variant = router.route("test_model", request_id="abc123")
        assert variant in ("champion", "challenger")
        assert "risk_percentage" in result

    def test_deterministic_routing(self):
        from app.ab_testing import ABRouter
        router = ABRouter()
        router.register(
            "test_model",
            champion_fn=lambda: {"risk_percentage": 10, "risk_level": "Low"},
            challenger_fn=lambda: {"risk_percentage": 15, "risk_level": "Low"},
            traffic_pct=50,
        )
        _, v1 = router.route("test_model", request_id="fixed_id")
        _, v2 = router.route("test_model", request_id="fixed_id")
        assert v1 == v2  # same request_id → same variant

    def test_summary(self):
        from app.ab_testing import ABRouter
        router = ABRouter()
        router.register(
            "test_model",
            champion_fn=lambda: {"risk_percentage": 10, "risk_level": "Low"},
            challenger_fn=lambda: {"risk_percentage": 15, "risk_level": "Low"},
            traffic_pct=50,
        )
        for i in range(10):
            router.route("test_model", request_id=f"req_{i}")
        summary = router.get_summary("test_model")
        assert summary["total_requests"] == 10
        assert summary["champion"]["count"] + summary["challenger"]["count"] == 10

    def test_invalid_traffic_pct(self):
        from app.ab_testing import ABRouter
        router = ABRouter()
        with pytest.raises(ValueError):
            router.register(
                "bad", champion_fn=lambda: {}, challenger_fn=lambda: {},
                traffic_pct=150,
            )

    def test_unknown_model_route(self):
        from app.ab_testing import ABRouter
        router = ABRouter()
        with pytest.raises(KeyError):
            router.route("nonexistent", request_id="x")


# ══════════════════════════════════════════════════════════════════════════
#  Feature Store
# ══════════════════════════════════════════════════════════════════════════

class TestFeatureStore:
    def test_get_feature_names(self):
        from feature_store import FeatureStore
        store = FeatureStore()
        names = store.get_feature_names("diabetes")
        assert len(names) == 13
        assert "bmi" in names
        assert "bmi_age" in names

    def test_get_specs_heart(self):
        from feature_store import FeatureStore
        store = FeatureStore()
        specs = store.get_specs("heart")
        assert len(specs) == 14

    def test_get_specs_lung(self):
        from feature_store import FeatureStore
        store = FeatureStore()
        specs = store.get_specs("lung")
        assert len(specs) == 8

    def test_unknown_model_raises(self):
        from feature_store import FeatureStore
        store = FeatureStore()
        with pytest.raises(KeyError):
            store.get_specs("unknown")

    def test_compute_diabetes(self):
        from feature_store import FeatureStore
        store = FeatureStore()
        df = store.compute_diabetes({
            "bmi": 25.0, "age_group": 7, "high_bp": 0, "smoker": 0,
            "high_cholesterol": 0, "physical_activity": 1,
            "general_health": 3, "mental_health": 0,
        })
        assert df.shape == (1, 13)
        assert df["bmi_age"].iloc[0] == 25.0 * 7

    def test_validate_valid_data(self):
        from feature_store import FeatureStore
        store = FeatureStore()
        df = store.compute_diabetes({
            "bmi": 25.0, "age_group": 7, "high_bp": 0, "smoker": 0,
            "high_cholesterol": 0, "physical_activity": 1,
            "general_health": 3, "mental_health": 0,
        })
        errors = store.validate("diabetes", df)
        assert errors == []

    def test_validate_catches_out_of_range(self):
        import pandas as pd
        from feature_store import FeatureStore
        store = FeatureStore()
        df = pd.DataFrame([{"bmi": 200.0, "age_group": 7, "high_bp": 0,
            "smoker": 0, "high_cholesterol": 0, "physical_activity": 1,
            "general_health": 3, "mental_health": 0, "bmi_age": 0,
            "bmi_bp": 0, "age_bp": 0, "chol_bmi": 0, "health_bmi": 0}])
        errors = store.validate("diabetes", df)
        assert any("bmi" in e for e in errors)


# ══════════════════════════════════════════════════════════════════════════
#  SHAP Explain Endpoints
# ══════════════════════════════════════════════════════════════════════════

class TestSHAPEndpoints:
    def test_explain_diabetes(self, client):
        resp = client.post("/api/v1/explain/diabetes", json={
            "age": 7, "bmi": 25.0, "bp": 0, "cholesterol": 0,
            "smoker": 0, "activity": 1, "health": 3, "mental": 0,
        }, headers={"X-API-Key": "healthpredict_dev_key_2026"})
        assert resp.status_code == 200
        body = resp.json()
        assert "explanation" in body
        assert "features" in body["explanation"]
        assert "shap_values" in body["explanation"]

    def test_explain_heart(self, client):
        resp = client.post("/api/v1/explain/heart", json={
            "age": 7, "sex": 1, "bmi": 25.0, "high_bp": 0, "high_chol": 0,
            "smoker": 0, "phys_activity": 1, "fruits": 1, "veggies": 1,
            "heavy_drinker": 0, "gen_health": 3, "ment_health": 0,
            "phys_health": 0, "diabetes": 0,
        }, headers={"X-API-Key": "healthpredict_dev_key_2026"})
        assert resp.status_code == 200
        body = resp.json()
        assert "explanation" in body

    def test_explain_lung(self, client):
        resp = client.post("/api/v1/explain/lung", json={
            "age": 50, "gender": 1, "smoking": 0, "yellow_fingers": 0,
            "chronic_disease": 0, "fatigue": 0, "wheezing": 0,
            "shortness_of_breath": 0,
        }, headers={"X-API-Key": "healthpredict_dev_key_2026"})
        assert resp.status_code == 200
        body = resp.json()
        assert "explanation" in body
