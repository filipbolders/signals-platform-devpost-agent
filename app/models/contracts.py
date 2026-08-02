from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PlatformHealth(StrictModel):
    generated_at: datetime
    platform: Literal["signals-platform"] = "signals-platform"
    status: HealthState
    version: Annotated[str | None, Field(max_length=40)] = None
    uptime_seconds: Annotated[int, Field(ge=0)]
    api_latency_ms: Annotated[float, Field(ge=0)]
    active_modules: Annotated[int, Field(ge=0)]
    unhealthy_modules: Annotated[int, Field(ge=0)]


class ModuleHealth(StrictModel):
    module_id: Literal[
        "object-tracker",
        "gps-live-map",
        "rf-adapter-test",
        "telescope-dslr-observation",
    ]
    display_name: Annotated[str, Field(max_length=80)]
    status: HealthState
    last_event_at: datetime | None = None
    request_count_15m: Annotated[int, Field(ge=0)] = 0
    error_count_15m: Annotated[int, Field(ge=0)] = 0
    latency_p95_ms: Annotated[float, Field(ge=0)] = 0


class IncidentSummary(StrictModel):
    incident_id: Annotated[
        str,
        Field(pattern=r"^INC-[A-Z0-9-]{6,40}$"),
    ]
    created_at: datetime
    status: IncidentStatus
    severity: Severity
    module_id: str
    title: Annotated[str, Field(max_length=160)]
    synthetic: bool


class IncidentDetail(IncidentSummary):
    summary: Annotated[str, Field(max_length=1000)]
    symptoms: Annotated[list[Annotated[str, Field(max_length=240)]], Field(max_length=20)]
    telemetry_labels: dict[str, str]
    grafana_dashboard_path: Annotated[str | None, Field(max_length=300)] = None


class TelemetrySummary(StrictModel):
    generated_at: datetime
    window_minutes: Literal[5, 15, 30, 60]
    requests_total: Annotated[int, Field(ge=0)]
    errors_total: Annotated[int, Field(ge=0)]
    latency_p50_ms: Annotated[float, Field(ge=0)]
    latency_p95_ms: Annotated[float, Field(ge=0)]
    events_received_total: Annotated[int, Field(ge=0)]
    media_failures_total: Annotated[int, Field(ge=0)]
    active_observation_sessions: Annotated[int, Field(ge=0)] = 0


class SyntheticIncidentScenario(str, Enum):
    MODULE_TIMEOUT = "module-timeout"
    ELEVATED_API_LATENCY = "elevated-api-latency"
    EVENT_INGESTION_STALLED = "event-ingestion-stalled"
    MEDIA_PROCESSING_FAILURE = "media-processing-failure"
    SERVICE_RESTART = "service-restart"


class SyntheticIncidentRequest(StrictModel):
    scenario: SyntheticIncidentScenario
    module_id: Literal[
        "object-tracker",
        "gps-live-map",
        "rf-adapter-test",
        "telescope-dslr-observation",
    ] = "object-tracker"
    severity: Severity = Severity.MEDIUM


class AgentEventType(str, Enum):
    INVESTIGATION_STARTED = "investigation_started"
    TOOL_CALLED = "tool_called"
    TOOL_SUCCEEDED = "tool_succeeded"
    TOOL_FAILED = "tool_failed"
    INVESTIGATION_COMPLETED = "investigation_completed"
    INVESTIGATION_FAILED = "investigation_failed"
    REPORT_SAVED = "report_saved"


class AgentTelemetryEvent(StrictModel):
    event_type: AgentEventType
    investigation_id: Annotated[str, Field(min_length=8, max_length=80)]
    incident_id: Annotated[str | None, Field(max_length=80)] = None
    tool_name: Annotated[str | None, Field(max_length=120)] = None
    outcome: Literal["started", "success", "failure"] | None = None
    duration_seconds: Annotated[float | None, Field(ge=0)] = None
    error_type: Annotated[str | None, Field(max_length=160)] = None
    report_path: Annotated[str | None, Field(max_length=300)] = None
