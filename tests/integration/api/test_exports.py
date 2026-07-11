import pytest
import pytest_asyncio
import uuid
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from backend.app.main import app

@pytest_asyncio.fixture(scope="module")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"User-Agent": "HealthPredictTestSuite/1.0"},
    ) as ac:
        yield ac

@pytest.mark.asyncio
class TestDataExports:
    async def get_token(self, client: AsyncClient) -> str:
        unique_email = f"export_test_{uuid.uuid4()}@example.com"
        await client.post(
            "/auth/register",
            json={
                "email": unique_email,
                "password": "Password123!",
                "full_name": "Export Test User"
            }
        )
        login_response = await client.post(
            "/auth/login",
            json={
                "email": unique_email,
                "password": "Password123!"
            }
        )
        data = login_response.json()
        if "access_token" not in data:
            raise RuntimeError(f"Login failed: {data}")
        return data["access_token"]

    async def test_request_export(self, client: AsyncClient):
        token = await self.get_token(client)
        headers = {"Authorization": f"Bearer {token}", "X-API-Key": "test-dev-api-key"}
        
        response = await client.post(
            "/api/v1/exports",
            json={"export_format": "json"},
            headers=headers,
        )
        if response.status_code != 202:
            print("Export request failed. Status:", response.status_code, "Body:", response.json())
        assert response.status_code == 202
        data = response.json()
        assert data["export_format"] == "json"
    async def test_request_export_duplicate(self, client: AsyncClient):
        token = await self.get_token(client)
        headers = {"Authorization": f"Bearer {token}", "X-API-Key": "test-dev-api-key"}
        
        with patch("fastapi.BackgroundTasks.add_task"):
            await client.post("/api/v1/exports", json={"export_format": "json"}, headers=headers)
            
            response = await client.post(
                "/api/v1/exports",
                json={"export_format": "json"},
                headers=headers,
            )
        assert response.status_code == 409
        
    async def test_list_exports(self, client: AsyncClient):
        token = await self.get_token(client)
        headers = {"Authorization": f"Bearer {token}", "X-API-Key": "test-dev-api-key"}
        
        # Create one export
        await client.post("/api/v1/exports", json={"export_format": "json"}, headers=headers)
        
        response = await client.get("/api/v1/exports", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 1
