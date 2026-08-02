from __future__ import annotations

from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import require_restricted_token
from app.models.contracts import (
    HealthState,
    IncidentDetail,
    IncidentStatus,
    ModuleHealth,
    PlatformHealth,
    SyntheticIncidentRequest,
    TelemetrySummary,
    AgentTelemetryEvent,
    AgentEventType,
)
from app.services.mock_store import mock_store
from app.services.settings import settings
from app.telemetry.metrics import (
    SYNTHETIC_INCIDENTS_CREATED_TOTAL,
    AGENT_INVESTIGATIONS_TOTAL,
    AGENT_INVESTIGATION_DURATION_SECONDS,
    AGENT_TOOL_CALLS_TOTAL,
    AGENT_TOOL_RESULTS_TOTAL,
    AGENT_REPORTS_SAVED_TOTAL,
)


logger = logging.getLogger("signals.agent.telemetry")


router = APIRouter(
    prefix="/api/devpost/v1",
    dependencies=[Depends(require_restricted_token)],
)


@router.get(
    "/health",
    response_model=PlatformHealth,
)
async def get_platform_health() -> PlatformHealth:
    modules = mock_store.list_modules()
    unhealthy_modules = sum(
        module.status != HealthState.HEALTHY
        for module in modules
    )

    status_value = (
        HealthState.HEALTHY
        if unhealthy_modules == 0
        else HealthState.DEGRADED
    )

    return PlatformHealth(
        generated_at=datetime.now(timezone.utc),
        status=status_value,
        version="0.1.0-demo",
        uptime_seconds=mock_store.uptime_seconds,
        api_latency_ms=18.4,
        active_modules=len(modules),
        unhealthy_modules=unhealthy_modules,
    )


@router.get("/modules")
async def list_module_health() -> dict[str, object]:
    return {
        "generated_at": datetime.now(timezone.utc),
        "modules": mock_store.list_modules(),
    }


@router.get("/incidents")
async def list_sanitised_incidents(
    limit: int = Query(default=20, ge=1, le=50),
    incident_status: IncidentStatus | None = Query(
        default=None,
        alias="status",
    ),
) -> dict[str, object]:
    incidents = mock_store.list_incidents(
        limit=limit,
        status=incident_status,
    )

    return {
        "generated_at": datetime.now(timezone.utc),
        "incidents": incidents,
    }


@router.get(
    "/incidents/{incident_id}",
    response_model=IncidentDetail,
)
async def get_sanitised_incident(
    incident_id: str,
) -> IncidentDetail:
    incident = mock_store.get_incident(incident_id)

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    return incident


@router.get(
    "/telemetry-summary",
    response_model=TelemetrySummary,
)
async def get_telemetry_summary(
    window_minutes: int = Query(
        default=15,
        enum=[5, 15, 30, 60],
    ),
) -> TelemetrySummary:
    return mock_store.telemetry_summary(window_minutes)


@router.post(
    "/demo/incidents",
    response_model=IncidentDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_synthetic_incident(
    request: SyntheticIncidentRequest,
) -> IncidentDetail:
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo mode is disabled",
        )

    incident = mock_store.create_synthetic_incident(request)

    SYNTHETIC_INCIDENTS_CREATED_TOTAL.labels(
        scenario=request.scenario.value,
        module_id=request.module_id,
        severity=request.severity.value,
    ).inc()

    logger.warning(
        "synthetic_incident_created",
        extra={
            "event": "synthetic_incident_created",
            "incident_id": incident.incident_id,
            "module_id": incident.module_id,
            "scenario": request.scenario.value,
            "severity": request.severity.value,
            "incident_status": incident.status.value,
            "synthetic": True,
        },
    )

    return incident


@router.post(
    "/internal/agent-events",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
async def record_agent_event(
    event: AgentTelemetryEvent,
) -> None:
    if event.event_type == AgentEventType.INVESTIGATION_STARTED:
        AGENT_INVESTIGATIONS_TOTAL.labels(
            outcome="started",
        ).inc()

    elif event.event_type == AgentEventType.INVESTIGATION_COMPLETED:
        AGENT_INVESTIGATIONS_TOTAL.labels(
            outcome="success",
        ).inc()

        if event.duration_seconds is not None:
            AGENT_INVESTIGATION_DURATION_SECONDS.observe(
                event.duration_seconds
            )

    elif event.event_type == AgentEventType.INVESTIGATION_FAILED:
        AGENT_INVESTIGATIONS_TOTAL.labels(
            outcome="failure",
        ).inc()

        if event.duration_seconds is not None:
            AGENT_INVESTIGATION_DURATION_SECONDS.observe(
                event.duration_seconds
            )

    elif (
        event.event_type == AgentEventType.TOOL_CALLED
        and event.tool_name
    ):
        AGENT_TOOL_CALLS_TOTAL.labels(
            tool_name=event.tool_name,
        ).inc()

    elif (
        event.event_type
        in {
            AgentEventType.TOOL_SUCCEEDED,
            AgentEventType.TOOL_FAILED,
        }
        and event.tool_name
    ):
        outcome = (
            "success"
            if event.event_type == AgentEventType.TOOL_SUCCEEDED
            else "failure"
        )

        AGENT_TOOL_RESULTS_TOTAL.labels(
            tool_name=event.tool_name,
            outcome=outcome,
        ).inc()

    elif event.event_type == AgentEventType.REPORT_SAVED:
        AGENT_REPORTS_SAVED_TOTAL.inc()

    logger.info(
        event.event_type.value,
        extra={
            "event": event.event_type.value,
            "investigation_id": event.investigation_id,
            "incident_id": event.incident_id,
            "tool_name": event.tool_name,
            "outcome": event.outcome,
            "duration_seconds": event.duration_seconds,
            "error_type": event.error_type,
            "report_path": event.report_path,
        },
    )
