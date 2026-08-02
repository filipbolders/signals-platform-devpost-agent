from fastapi.testclient import TestClient

from app.main import app
from app.services.settings import settings


client = TestClient(app)

AUTH_HEADERS = {
    "Authorization": f"Bearer {settings.restricted_api_token}",
}


def test_metrics_endpoint_exposes_application_metrics() -> None:
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "signals_platform_health" in response.text
    assert "signals_active_modules" in response.text
    assert "signals_module_health" in response.text
    assert "signals_http_requests_total" in response.text


def test_authenticated_request_updates_http_counter() -> None:
    health_response = client.get(
        "/api/devpost/v1/health",
        headers=AUTH_HEADERS,
    )

    assert health_response.status_code == 200
    assert "X-Request-ID" in health_response.headers

    metrics_response = client.get("/metrics")

    assert (
        'signals_http_requests_total{'
        in metrics_response.text
    )


def test_synthetic_incident_updates_counter() -> None:
    response = client.post(
        "/api/devpost/v1/demo/incidents",
        headers=AUTH_HEADERS,
        json={
            "scenario": "service-restart",
            "module_id": "object-tracker",
            "severity": "high",
        },
    )

    assert response.status_code == 201

    metrics_response = client.get("/metrics")

    assert "signals_synthetic_incidents_created_total" in (
        metrics_response.text
    )
    assert 'scenario="service-restart"' in metrics_response.text
