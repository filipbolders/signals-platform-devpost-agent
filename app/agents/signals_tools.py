from __future__ import annotations

from typing import Any

from app.connectors.errors import SignalsPlatformClientError
from app.connectors.factory import create_signals_platform_client
from app.models.contracts import IncidentStatus


async def get_signals_platform_health() -> dict[str, Any]:
    """Return sanitised current health for Signals Platform."""
    try:
        async with create_signals_platform_client() as client:
            health = await client.get_health()

        return {
            "ok": True,
            "health": health.model_dump(mode="json"),
        }
    except SignalsPlatformClientError as exc:
        return {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }


async def list_signals_platform_modules() -> dict[str, Any]:
    """Return sanitised health information for approved modules."""
    try:
        async with create_signals_platform_client() as client:
            modules = await client.list_modules()

        return {
            "ok": True,
            "modules": [
                module.model_dump(mode="json")
                for module in modules
            ],
        }
    except SignalsPlatformClientError as exc:
        return {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }


async def get_signals_telemetry_summary(
    window_minutes: int = 15,
) -> dict[str, Any]:
    """Return aggregate telemetry for a supported time window."""
    if window_minutes not in {5, 15, 30, 60}:
        return {
            "ok": False,
            "error": "InvalidWindow",
            "message": "window_minutes must be 5, 15, 30, or 60",
        }

    try:
        async with create_signals_platform_client() as client:
            telemetry = await client.get_telemetry_summary(
                window_minutes=window_minutes,
            )

        return {
            "ok": True,
            "telemetry": telemetry.model_dump(mode="json"),
        }
    except SignalsPlatformClientError as exc:
        return {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }


async def list_signals_incidents(
    limit: int = 10,
    status: str | None = None,
) -> dict[str, Any]:
    """Return recent sanitised Signals Platform incidents."""
    if limit < 1 or limit > 50:
        return {
            "ok": False,
            "error": "InvalidLimit",
            "message": "limit must be between 1 and 50",
        }

    incident_status: IncidentStatus | None = None

    if status:
        try:
            incident_status = IncidentStatus(status)
        except ValueError:
            return {
                "ok": False,
                "error": "InvalidStatus",
                "message": (
                    "status must be open, investigating, "
                    "mitigated, or resolved"
                ),
            }

    try:
        async with create_signals_platform_client() as client:
            incidents = await client.list_incidents(
                limit=limit,
                status=incident_status,
            )

        return {
            "ok": True,
            "incidents": [
                incident.model_dump(mode="json")
                for incident in incidents
            ],
        }
    except SignalsPlatformClientError as exc:
        return {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }
