from __future__ import annotations

import os
from typing import Any

import httpx


async def emit_agent_event(
    *,
    event_type: str,
    investigation_id: str,
    incident_id: str | None = None,
    tool_name: str | None = None,
    outcome: str | None = None,
    duration_seconds: float | None = None,
    error_type: str | None = None,
    report_path: str | None = None,
) -> None:
    base_url = os.getenv(
        "SIGNALS_PLATFORM_BASE_URL",
        "http://127.0.0.1:8030/api/devpost/v1",
    ).rstrip("/")

    token = os.getenv("RESTRICTED_API_TOKEN")

    if not token:
        return

    payload: dict[str, Any] = {
        "event_type": event_type,
        "investigation_id": investigation_id,
        "incident_id": incident_id,
        "tool_name": tool_name,
        "outcome": outcome,
        "duration_seconds": duration_seconds,
        "error_type": error_type,
        "report_path": report_path,
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{base_url}/internal/agent-events",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except httpx.HTTPError:
        # Telemetry must never prevent an investigation from completing.
        return
