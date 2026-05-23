from fastapi.testclient import TestClient

from backend.app.main import app


def test_login_and_register_smoke():
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    payload = {
        "email": "test@example.com",
        "password": "Password123!",
        "full_name": "Test User",
    }

    with TestClient(app) as client:
        register = client.post("/auth/register", json=payload, headers=headers)
        assert register.status_code in (201, 409)

        login = client.post(
            "/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
            headers=headers,
        )
        assert login.status_code == 200
        body = login.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]
