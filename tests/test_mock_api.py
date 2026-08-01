from fastapi.testclient import TestClient

from app.main import app
from app.services.settings import settings


client = TestClient(app)

AUTH_HEADERS = {
    "Authorization": f"Bearer {settings.restricted_api_token}",
}


def test_health_requires_authentication() -> None:
    response = client.get("/api/devpost/v1/health")

    assert response.status_code == 401


def test_health_returns_sanitised_status() -> None:
    response = client.get(
        "/api/devpost/v1/health",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["platform"] == "signals-platform"
    assert payload["status"] in {"healthy", "degraded"}
    assert "customer_email" not in payload
    assert "latitude" not in payload
    assert "longitude" not in payload


def test_modules_returns_only_approved_modules() -> None:
    response = client.get(
        "/api/devpost/v1/modules",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200

    module_ids = {
        module["module_id"]
        for module in response.json()["modules"]
    }

    assert module_ids == {
        "object-tracker",
        "gps-live-map",
        "rf-adapter-test",
        "telescope-dslr-observation",
    }


def test_create_synthetic_incident() -> None:
    response = client.post(
        "/api/devpost/v1/demo/incidents",
        headers=AUTH_HEADERS,
        json={
            "scenario": "event-ingestion-stalled",
            "module_id": "object-tracker",
            "severity": "high",
        },
    )

    assert response.status_code == 201

    payload = response.json()

    assert payload["synthetic"] is True
    assert payload["module_id"] == "object-tracker"
    assert payload["incident_id"].startswith("INC-DEMO-")


def test_unknown_synthetic_scenario_is_rejected() -> None:
    response = client.post(
        "/api/devpost/v1/demo/incidents",
        headers=AUTH_HEADERS,
        json={
            "scenario": "run-shell-command",
        },
    )

    assert response.status_code == 422
