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
    assert response.json() == {"status": "healthy"}


def test_metrics():
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "api_request_count_total" in response.text


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