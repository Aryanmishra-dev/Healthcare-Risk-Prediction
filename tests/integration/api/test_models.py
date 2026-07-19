"""
Phase 3 Integration Tests — Model Registry, SHAP Explainability, Monitoring.

Tests model registration, promotion, archival, SHAP explanation endpoint,
and drift/monitoring service APIs.
"""

import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app

API_KEY = "test-dev-api-key"


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"User-Agent": "HealthPredictTestSuite/1.0"},
    ) as c:
        yield c


async def register_user_and_get_token(
    client: AsyncClient, role: str = "user"
) -> str:
    import random

    suffix = random.randint(10000, 99999)
    email = f"phase3_{role}_{suffix}@test.com"
    pw = "Test1234!@"

    reg_resp = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": pw,
            "full_name": f"Phase3 {role.title()}",
        },
        headers={"X-API-Key": API_KEY},
    )
    assert reg_resp.status_code in (201, 200, 400), reg_resp.text

    login_resp = await client.post(
        "/auth/login",
        json={"email": email, "password": pw},
        headers={"X-API-Key": API_KEY},
    )
    assert login_resp.status_code == 200, login_resp.text
    return login_resp.json()["access_token"]


class TestModelHealthEndpoint:
    @pytest.mark.anyio
    async def test_model_health(self, client: AsyncClient):
        token = await register_user_and_get_token(client)
        response = await client.get(
            "/api/v1/models/health",
            headers={"Authorization": f"Bearer {token}", "X-API-Key": API_KEY},
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "models" in data
        assert data["status"] in ("healthy", "degraded")


class TestModelRegistryAPI:
    @pytest.mark.anyio
    async def test_list_models_authenticated(self, client: AsyncClient):
        token = await register_user_and_get_token(client)
        response = await client.get(
            "/api/v1/models",
            headers={"Authorization": f"Bearer {token}", "X-API-Key": API_KEY},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.anyio
    async def test_register_model_requires_admin(self, client: AsyncClient):
        token = await register_user_and_get_token(client, "user")
        payload = {
            "model_name": "diabetes_xgboost",
            "model_version": "v2.0",
            "disease": "diabetes",
            "framework": "scikit-learn",
            "algorithm": "XGBoost",
        }
        response = await client.post(
            "/api/v1/models/register",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "X-API-Key": API_KEY},
        )
        # Non-admin should be forbidden
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_current_models(self, client: AsyncClient):
        token = await register_user_and_get_token(client)
        response = await client.get(
            "/api/v1/models/current",
            headers={"Authorization": f"Bearer {token}", "X-API-Key": API_KEY},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.anyio
    async def test_model_history_requires_model_name(
        self, client: AsyncClient
    ):
        token = await register_user_and_get_token(client)
        response = await client.get(
            "/api/v1/models/history",
            headers={"Authorization": f"Bearer {token}", "X-API-Key": API_KEY},
        )
        assert response.status_code == 422  # missing required query param

    @pytest.mark.anyio
    async def test_model_history_valid(self, client: AsyncClient):
        token = await register_user_and_get_token(client)
        response = await client.get(
            "/api/v1/models/history?model_name=diabetes_xgboost",
            headers={"Authorization": f"Bearer {token}", "X-API-Key": API_KEY},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.anyio
    async def test_model_not_found(self, client: AsyncClient):
        token = await register_user_and_get_token(client)
        random_id = str(uuid.uuid4())
        response = await client.get(
            f"/api/v1/models/{random_id}",
            headers={"Authorization": f"Bearer {token}", "X-API-Key": API_KEY},
        )
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_metrics_requires_admin(self, client: AsyncClient):
        token = await register_user_and_get_token(client, "user")
        response = await client.get(
            "/api/v1/models/metrics",
            headers={"Authorization": f"Bearer {token}", "X-API-Key": API_KEY},
        )
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_drift_requires_admin(self, client: AsyncClient):
        token = await register_user_and_get_token(client, "user")
        response = await client.get(
            "/api/v1/models/drift",
            headers={"Authorization": f"Bearer {token}", "X-API-Key": API_KEY},
        )
        assert response.status_code == 403


class TestModelMonitoringService:
    def test_record_and_get_metrics(self):
        from backend.app.services.model_monitoring_service import (
            ModelMonitoringService,
        )

        svc = ModelMonitoringService()
        svc.record_prediction("diabetes", 120, True)
        svc.record_prediction("diabetes", 80, True)
        svc.record_prediction("diabetes", 100, False)
        metrics = svc.get_metrics()
        assert "diabetes" in metrics
        dm = metrics["diabetes"]
        assert dm["prediction_count"] == 3
        assert dm["error_rate"] == pytest.approx(1 / 3, abs=0.01)
        assert dm["average_inference_time_ms"] == pytest.approx(100.0, abs=1.0)


class TestModelDriftService:
    def test_record_drift(self):
        from backend.app.services.model_drift_service import ModelDriftService

        svc = ModelDriftService()
        svc.record_drift(
            "diabetes",
            feature_drift=True,
            prediction_drift=False,
            data_drift=False,
        )
        records = svc.get_recent_drift()
        assert len(records) == 1
        assert records[0]["disease"] == "diabetes"
        assert records[0]["feature_drift"] is True

    def test_no_drift(self):
        from backend.app.services.model_drift_service import ModelDriftService

        svc = ModelDriftService()
        svc.record_drift(
            "heart_disease",
            feature_drift=False,
            prediction_drift=False,
            data_drift=False,
        )
        records = svc.get_recent_drift()
        assert records[0]["disease"] == "heart_disease"


class TestModelRegistryService:
    @pytest.mark.anyio
    async def test_register_and_get_model(self):
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker

        from backend.app.models.base import Base
        from backend.app.models.model_version import ModelVersion
        from backend.app.schemas.model_version import ModelVersionCreate
        from backend.app.services.model_registry_service import (
            ModelRegistryService,
        )

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", echo=False
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async with async_session() as session:
            svc = ModelRegistryService()
            schema = ModelVersionCreate(
                model_name="diabetes_xgboost",
                model_version="v3.0",
                disease="diabetes",
                framework="scikit-learn",
                algorithm="XGBoost",
            )
            registered = await svc.register_model(session, schema)
            assert registered.id is not None
            assert registered.status == "Training"

            fetched = await svc.get_model(session, registered.id)
            assert fetched.model_name == "diabetes_xgboost"

    @pytest.mark.anyio
    async def test_promote_model(self):
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker

        from backend.app.models.base import Base
        from backend.app.schemas.model_version import ModelVersionCreate
        from backend.app.services.model_registry_service import (
            ModelRegistryService,
        )

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", echo=False
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with async_session() as session:
            svc = ModelRegistryService()
            schema = ModelVersionCreate(
                model_name="diabetes_xgboost",
                model_version="v3.1",
                disease="diabetes",
                framework="scikit-learn",
                algorithm="XGBoost",
            )
            registered = await svc.register_model(session, schema)
            promoted = await svc.promote_model(session, registered.id)
            assert promoted.status == "Production"
            assert promoted.deployed_at is not None


class TestSHAPExplanationEndpoint:
    @pytest.mark.anyio
    async def test_explanation_404_for_missing_shap(self, client: AsyncClient):
        """Endpoint should return 404 when prediction has no SHAP data."""
        token = await register_user_and_get_token(client)
        # Use a non-existent prediction ID
        response = await client.get(
            "/api/v1/predictions/999999/explanation",
            headers={"Authorization": f"Bearer {token}", "X-API-Key": API_KEY},
        )
        # 404 — prediction doesn't exist for this user
        assert response.status_code == 404


class TestABTestingService:
    def test_default_group(self):
        from backend.app.services.ab_testing_service import ABTestingService

        svc = ABTestingService()
        group = svc.assign_group("diabetes")
        assert group == "Production"

    def test_configured_split(self):
        from backend.app.services.ab_testing_service import ABTestingService

        svc = ABTestingService()
        svc.set_config("diabetes", {"Production": 90, "Staging": 10})
        results = [svc.assign_group("diabetes") for _ in range(100)]
        assert "Production" in results
        # With 90/10 split, Production should dominate
        production_count = results.count("Production")
        assert production_count > 50  # at least majority

    def test_invalid_config_raises(self):
        from backend.app.services.ab_testing_service import ABTestingService

        svc = ABTestingService()
        with pytest.raises(ValueError):
            svc.set_config(
                "diabetes", {"Production": 80, "Staging": 5}
            )  # sums to 85, not 100
