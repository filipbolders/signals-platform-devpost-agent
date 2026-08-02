import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.operator import manager
from app.services.settings import settings


client = TestClient(app)

AUTH_HEADERS = {
    "Authorization": f"Bearer {settings.restricted_api_token}",
}


def test_completed_job_can_be_loaded_from_state_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    state_file = tmp_path / "operator_jobs.json"

    payload = {
        "version": 1,
        "jobs": [
            {
                "investigation_id": "INV-PERSIST-123456",
                "status": "completed",
                "created_at": "2026-08-02T12:00:00+00:00",
                "updated_at": "2026-08-02T12:05:00+00:00",
                "scenario": "elevated-api-latency",
                "module_id": "rf-adapter-test",
                "severity": "medium",
                "incident": None,
                "report": "Stored report",
                "report_files": None,
                "grafana": None,
                "timeline": [],
                "error": None,
            }
        ],
    }

    state_file.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    monkeypatch.setattr(manager, "STATE_FILE", state_file)
    manager._JOBS.clear()
    manager.load_persisted_jobs()

    assert "INV-PERSIST-123456" in manager._JOBS
    assert (
        manager._JOBS["INV-PERSIST-123456"]["status"]
        == "completed"
    )


def test_invalid_report_format_is_rejected() -> None:
    response = client.get(
        "/api/operator/investigations/INV-NOTFOUND/"
        "reports/pdf",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 400
