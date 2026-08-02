from fastapi.testclient import TestClient

from app.main import app
from app.services.settings import settings


client = TestClient(app)

AUTH_HEADERS = {
    "Authorization": f"Bearer {settings.restricted_api_token}",
}


def test_agent_event_endpoint_records_tool_call() -> None:
    response = client.post(
        "/api/devpost/v1/internal/agent-events",
        headers=AUTH_HEADERS,
        json={
            "event_type": "tool_called",
            "investigation_id": "INV-TEST-123456",
            "incident_id": "INC-DEMO-RF-001",
            "tool_name": "query_prometheus",
            "outcome": "started",
        },
    )

    assert response.status_code == 204


def test_agent_metrics_are_exposed() -> None:
    client.post(
        "/api/devpost/v1/internal/agent-events",
        headers=AUTH_HEADERS,
        json={
            "event_type": "investigation_completed",
            "investigation_id": "INV-TEST-123457",
            "outcome": "success",
            "duration_seconds": 3.2,
        },
    )

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "signals_agent_investigations_total" in response.text
    assert "signals_agent_tool_calls_total" in response.text
    assert "signals_agent_investigation_duration_seconds" in response.text
