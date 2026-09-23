import sys
import os

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/ai_platform"

from fastapi.testclient import TestClient

from app.main import app
from app.auth import create_access_token


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "database" in data
    assert "redis" in data


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "api_request_count" in response.text


def test_chat_without_authentication():
    response = client.post(
        "/chat",
        json={"question": "What is Docker?"},
    )
    assert response.status_code == 401


def test_chat_with_invalid_token():
    response = client.post(
        "/chat",
        headers={"Authorization": "Bearer invalid-token"},
        json={"question": "What is Docker?"},
    )
    assert response.status_code == 401


def test_create_access_token():
    token = create_access_token(
        username="testuser",
        role="user",
    )
    assert token
    assert isinstance(token, str)


def test_chat_with_valid_token():
    token = create_access_token(username="alice", role="user")
    response = client.post(
        "/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Explain Docker containers."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "alice"
    assert "answer" in data
    assert "tokens_used" in data
    assert "model" in data


def test_rbac_admin_endpoint():
    # User role should be forbidden (403)
    user_token = create_access_token(username="regular_user", role="user")
    resp_user = client.get(
        "/admin/system-status",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp_user.status_code == 403

    # Admin role should succeed (200)
    admin_token = create_access_token(username="admin_user", role="admin")
    resp_admin = client.get(
        "/admin/system-status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_admin.status_code == 200
    assert resp_admin.json()["role"] == "admin"