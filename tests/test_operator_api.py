from fastapi.testclient import TestClient

from app.main import app
from app.services.settings import settings


client = TestClient(app)

AUTH_HEADERS = {
    "Authorization": f"Bearer {settings.restricted_api_token}",
}


def test_operator_page_loads() -> None:
    response = client.get("/operator")

    assert response.status_code == 200
    assert "Signals Platform Investigation Console" in response.text


def test_operator_api_requires_authentication() -> None:
    response = client.get("/api/operator/investigations")

    assert response.status_code == 401


def test_operator_investigation_launches() -> None:
    response = client.post(
        "/api/operator/investigations",
        headers=AUTH_HEADERS,
        json={
            "scenario": "elevated-api-latency",
            "module_id": "rf-adapter-test",
            "severity": "medium",
        },
    )

    assert response.status_code == 202

    payload = response.json()

    assert payload["investigation_id"].startswith("INV-")
    assert payload["status"] == "queued"
