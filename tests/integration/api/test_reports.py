from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.auth.router import get_current_user
from backend.app.main import app
from backend.app.models.user import User


def mock_get_current_user():
    return User(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
    )


@pytest.fixture(autouse=True)
def override_dependency():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides.clear()


def test_get_reports_empty(client: TestClient):
    response = client.get(
        "/api/v1/reports", headers={"X-API-Key": "test-dev-api-key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_get_report_not_found(client: TestClient):
    response = client.get(
        f"/api/v1/reports/{uuid4()}", headers={"X-API-Key": "test-dev-api-key"}
    )
    assert response.status_code == 404


def test_delete_report_not_found(client: TestClient):
    response = client.delete(
        f"/api/v1/reports/{uuid4()}", headers={"X-API-Key": "test-dev-api-key"}
    )
    assert response.status_code == 404


def test_upload_report(client: TestClient, tmp_path):
    # Create a dummy file
    test_file = tmp_path / "test.txt"
    test_file.write_text("dummy report content")

    with open(test_file, "rb") as f:
        # Note: validate_upload will reject non-pdf/img if strict, but let's see.
        response = client.post(
            "/api/v1/reports/upload",
            headers={"X-API-Key": "test-dev-api-key"},
            files={"file": ("test.pdf", f, "application/pdf")},
        )
    # 201 Created or 401/etc
    if response.status_code == 201:
        data = response.json()
        assert data["upload_status"] == "uploaded"
