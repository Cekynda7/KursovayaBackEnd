import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from auth_service.main import app


client = TestClient(app)


def _unique_email() -> str:
    return f"test_{uuid4().hex}@example.com"


@pytest.mark.asyncio
async def test_register_and_login():
    email = _unique_email()
    password = "password123"

    response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code in (201, 409)

    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password_returns_json_error():
    email = _unique_email()
    password = "password123"

    response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code in (201, 409)

    response = client.post(
        "/auth/login",
        json={"email": email, "password": "wrong-password"},
    )
    assert response.status_code in (401, 422)
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_invalid_json_returns_422():
    response = client.post(
        "/auth/login",
        data="{",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert data.get("error_code") == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_token_endpoint_returns_access_token():
    email = _unique_email()
    password = "password123"

    response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code in (201, 409)

    response = client.post(
        "/auth/token",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
