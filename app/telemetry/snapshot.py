from __future__ import annotations

from collections import Counter

from app.services.mock_store import mock_store
from app.telemetry.metrics import (
    ACTIVE_MODULES,
    ACTIVE_OBSERVATION_SESSIONS,
    EVENTS_RECEIVED_TOTAL,
    HEALTH_VALUES,
    INCIDENTS_CURRENT,
    MEDIA_FAILURES_TOTAL,
    MODULE_ERRORS_15M,
    MODULE_HEALTH,
    MODULE_LATENCY_P95_MS,
    MODULE_REQUESTS_15M,
    PLATFORM_HEALTH,
    UNHEALTHY_MODULES,
)


def refresh_application_metrics() -> None:
    modules = mock_store.list_modules()

    unhealthy_count = sum(
        module.status.value != "healthy"
        for module in modules
    )

    overall_status = "healthy" if unhealthy_count == 0 else "degraded"

    PLATFORM_HEALTH.set(HEALTH_VALUES[overall_status])
    ACTIVE_MODULES.set(len(modules))
    UNHEALTHY_MODULES.set(unhealthy_count)

    for module in modules:
        module_id = module.module_id

        MODULE_HEALTH.labels(
            module_id=module_id,
        ).set(HEALTH_VALUES[module.status.value])

        MODULE_REQUESTS_15M.labels(
            module_id=module_id,
        ).set(module.request_count_15m)

        MODULE_ERRORS_15M.labels(
            module_id=module_id,
        ).set(module.error_count_15m)

        MODULE_LATENCY_P95_MS.labels(
            module_id=module_id,
        ).set(module.latency_p95_ms)

    telemetry = mock_store.telemetry_summary(15)

    EVENTS_RECEIVED_TOTAL.labels(
        window_minutes="15",
    ).set(telemetry.events_received_total)

    MEDIA_FAILURES_TOTAL.labels(
        window_minutes="15",
    ).set(telemetry.media_failures_total)

    ACTIVE_OBSERVATION_SESSIONS.set(
        telemetry.active_observation_sessions
    )

    incidents = mock_store.list_incidents(
        limit=50,
        status=None,
    )

    incident_counts = Counter(
        (incident.status.value, incident.severity.value)
        for incident in incidents
    )

    for status in (
        "open",
        "investigating",
        "mitigated",
        "resolved",
    ):
        for severity in (
            "info",
            "low",
            "medium",
            "high",
            "critical",
        ):
            INCIDENTS_CURRENT.labels(
                status=status,
                severity=severity,
            ).set(incident_counts[(status, severity)])
