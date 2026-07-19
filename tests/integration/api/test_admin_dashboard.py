import pytest
from httpx import AsyncClient


def test_admin_dashboard_overview_admin_only(client):
    response = client.get("/api/v1/admin/dashboard/overview")
    assert response.status_code == 401
