from __future__ import annotations

import asyncio
import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from app.agents.telemetry_client import emit_agent_event
from app.connectors.factory import create_signals_platform_client
from app.models.contracts import (
    Severity,
    SyntheticIncidentRequest,
    SyntheticIncidentScenario,
)
from scripts.run_investigation_agent import run_agent


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "artifacts" / "investigations"
STATE_FILE = PROJECT_ROOT / "artifacts" / "operator_jobs.json"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

_JOBS: dict[str, dict[str, Any]] = {}
_JOBS_LOCK = asyncio.Lock()
_PERSIST_LOCK = asyncio.Lock()



def load_persisted_jobs() -> None:
    """Restore operator jobs after an application restart."""
    if not STATE_FILE.exists():
        return

    try:
        payload = json.loads(
            STATE_FILE.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return

    if not isinstance(payload, dict):
        return

    jobs = payload.get("jobs")

    if not isinstance(jobs, list):
        return

    for job in jobs:
        if not isinstance(job, dict):
            continue

        investigation_id = job.get("investigation_id")

        if not isinstance(investigation_id, str):
            continue

        if job.get("status") in {
            "queued",
            "creating_incident",
            "investigating",
        }:
            job["status"] = "interrupted"
            job["error"] = {
                "type": "ServiceRestart",
                "message": (
                    "Investigation was interrupted by an "
                    "application restart."
                ),
            }
            job.setdefault("timeline", []).append({
                "timestamp": _now(),
                "event": "investigation_interrupted",
                "outcome": "failure",
                "error_type": "ServiceRestart",
            })

        _JOBS[investigation_id] = job


async def _persist_jobs() -> None:
    """Write operator state atomically."""
    async with _PERSIST_LOCK:
        async with _JOBS_LOCK:
            jobs = deepcopy(list(_JOBS.values()))

        payload = {
            "version": 1,
            "updated_at": _now(),
            "jobs": jobs,
        }

        temporary_path = STATE_FILE.with_suffix(".json.tmp")

        temporary_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

        temporary_path.replace(STATE_FILE)



def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _append_timeline(
    investigation_id: str,
    event: dict[str, object],
) -> None:
    entry = {
        "timestamp": _now(),
        **event,
    }

    async with _JOBS_LOCK:
        job = _JOBS.get(investigation_id)

        if job is not None:
            job["timeline"].append(entry)
            job["updated_at"] = entry["timestamp"]

    await _persist_jobs()


def _grafana_links(
    investigation_id: str,
    incident_id: str,
) -> dict[str, str]:
    base_url = os.getenv(
        "GRAFANA_URL",
        "https://eloquentyarrow3131.grafana.net",
    ).rstrip("/")

    dashboard = (
        f"{base_url}/d/signals-platform-devpost/"
        "signals-platform-devpost-operations"
        "?orgId=1&from=now-1h&to=now&refresh=15s"
    )

    metrics_query = quote(
        'signals_module_health{module_id="rf-adapter-test"}'
    )

    logs_query = quote(
        '{job="signals-platform-devpost"} '
        f'| json | investigation_id="{investigation_id}"'
    )

    return {
        "dashboard": dashboard,
        "prometheus_explore": (
            f"{base_url}/explore"
            f"?orgId=1&left=%7B%22datasource%22:"
            f"%22grafanacloud-prom%22,"
            f"%22queries%22:%5B%7B%22expr%22:"
            f"%22{metrics_query}%22%7D%5D%7D"
        ),
        "loki_explore": (
            f"{base_url}/explore"
            f"?orgId=1&left=%7B%22datasource%22:"
            f"%22grafanacloud-logs%22,"
            f"%22queries%22:%5B%7B%22expr%22:"
            f"%22{logs_query}%22%7D%5D%7D"
        ),
        "incident_id": incident_id,
    }


async def create_investigation(
    *,
    scenario: SyntheticIncidentScenario,
    module_id: str,
    severity: Severity,
) -> dict[str, Any]:
    investigation_id = f"INV-{uuid4().hex[:14].upper()}"

    job = {
        "investigation_id": investigation_id,
        "status": "queued",
        "created_at": _now(),
        "updated_at": _now(),
        "scenario": scenario.value,
        "module_id": module_id,
        "severity": severity.value,
        "incident": None,
        "report": None,
        "report_files": None,
        "grafana": None,
        "timeline": [],
        "error": None,
    }

    async with _JOBS_LOCK:
        _JOBS[investigation_id] = job

    await _persist_jobs()

    asyncio.create_task(
        _run_investigation(
            investigation_id=investigation_id,
            scenario=scenario,
            module_id=module_id,
            severity=severity,
        )
    )

    return deepcopy(job)


async def _run_investigation(
    *,
    investigation_id: str,
    scenario: SyntheticIncidentScenario,
    module_id: str,
    severity: Severity,
) -> None:
    try:
        await _set_status(investigation_id, "creating_incident")

        request = SyntheticIncidentRequest(
            scenario=scenario,
            module_id=module_id,
            severity=severity,
        )

        async with create_signals_platform_client() as client:
            incident = await client.create_synthetic_incident(request)

        await _update_job(
            investigation_id,
            incident=incident.model_dump(mode="json"),
            grafana=_grafana_links(
                investigation_id,
                incident.incident_id,
            ),
        )

        await _append_timeline(
            investigation_id,
            {
                "event": "synthetic_incident_created",
                "incident_id": incident.incident_id,
                "module_id": incident.module_id,
                "severity": incident.severity.value,
                "outcome": "success",
            },
        )

        await _set_status(investigation_id, "investigating")

        question = (
            f"Investigate synthetic incident {incident.incident_id}. "
            f"The affected module is {incident.module_id}. "
            "Verify the incident using the restricted Signals Platform "
            "API, Prometheus metrics, and Loki logs. Separate observed "
            "facts from inference and recommend a human-approved action."
        )

        async def on_agent_event(
            event: dict[str, object],
        ) -> None:
            await _append_timeline(investigation_id, event)

        report = await run_agent(
            question,
            investigation_id=investigation_id,
            incident_id=incident.incident_id,
            on_event=on_agent_event,
        )

        timestamp = datetime.now(timezone.utc)
        basename = (
            f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}-"
            f"{investigation_id}-{incident.incident_id}"
        )

        json_path = REPORT_DIR / f"{basename}.json"
        markdown_path = REPORT_DIR / f"{basename}.md"

        payload = {
            "generated_at": timestamp.isoformat(),
            "investigation_id": investigation_id,
            "incident": incident.model_dump(mode="json"),
            "question": question,
            "report": report,
            "synthetic": True,
        }

        json_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

        markdown_path.write_text(
            "\n".join(
                [
                    "# Signals Platform Investigation",
                    "",
                    f"- Investigation ID: `{investigation_id}`",
                    f"- Incident ID: `{incident.incident_id}`",
                    f"- Generated: `{timestamp.isoformat()}`",
                    "- Environment: `demo`",
                    "- Synthetic: `true`",
                    "",
                    report,
                    "",
                ]
            ),
            encoding="utf-8",
        )

        relative_json = str(json_path.relative_to(PROJECT_ROOT))
        relative_markdown = str(
            markdown_path.relative_to(PROJECT_ROOT)
        )

        await emit_agent_event(
            event_type="report_saved",
            investigation_id=investigation_id,
            incident_id=incident.incident_id,
            outcome="success",
            report_path=relative_markdown,
        )

        await _append_timeline(
            investigation_id,
            {
                "event": "report_saved",
                "outcome": "success",
                "report_path": relative_markdown,
            },
        )

        await _update_job(
            investigation_id,
            status="completed",
            report=report,
            report_files={
                "json": relative_json,
                "markdown": relative_markdown,
            },
        )

    except Exception as exc:
        await _append_timeline(
            investigation_id,
            {
                "event": "investigation_failed",
                "outcome": "failure",
                "error_type": type(exc).__name__,
            },
        )

        await _update_job(
            investigation_id,
            status="failed",
            error={
                "type": type(exc).__name__,
                "message": str(exc),
            },
        )


async def _set_status(
    investigation_id: str,
    status: str,
) -> None:
    await _update_job(
        investigation_id,
        status=status,
    )


async def _update_job(
    investigation_id: str,
    **values: object,
) -> None:
    async with _JOBS_LOCK:
        job = _JOBS.get(investigation_id)

        if job is None:
            return

        job.update(values)
        job["updated_at"] = _now()

    await _persist_jobs()


async def get_investigation(
    investigation_id: str,
) -> dict[str, Any] | None:
    async with _JOBS_LOCK:
        job = _JOBS.get(investigation_id)
        return deepcopy(job) if job else None


async def list_investigations() -> list[dict[str, Any]]:
    async with _JOBS_LOCK:
        jobs = list(_JOBS.values())

    jobs.sort(
        key=lambda item: item["created_at"],
        reverse=True,
    )

    return deepcopy(jobs[:20])
