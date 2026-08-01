from __future__ import annotations

from datetime import datetime, timezone, timedelta
from threading import Lock
from uuid import uuid4

from app.models.contracts import (
    HealthState,
    IncidentDetail,
    IncidentStatus,
    ModuleHealth,
    Severity,
    SyntheticIncidentRequest,
    SyntheticIncidentScenario,
    TelemetrySummary,
)


class MockStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._started_at = datetime.now(timezone.utc) - timedelta(hours=8)

        self._modules: list[ModuleHealth] = [
            ModuleHealth(
                module_id="object-tracker",
                display_name="Object Tracker",
                status=HealthState.HEALTHY,
                last_event_at=datetime.now(timezone.utc) - timedelta(seconds=18),
                request_count_15m=384,
                error_count_15m=1,
                latency_p95_ms=84.2,
            ),
            ModuleHealth(
                module_id="gps-live-map",
                display_name="GPS Live Map",
                status=HealthState.HEALTHY,
                last_event_at=datetime.now(timezone.utc) - timedelta(seconds=42),
                request_count_15m=215,
                error_count_15m=0,
                latency_p95_ms=63.7,
            ),
            ModuleHealth(
                module_id="rf-adapter-test",
                display_name="RF Adapter Test",
                status=HealthState.DEGRADED,
                last_event_at=datetime.now(timezone.utc) - timedelta(minutes=7),
                request_count_15m=46,
                error_count_15m=5,
                latency_p95_ms=421.4,
            ),
            ModuleHealth(
                module_id="telescope-dslr-observation",
                display_name="Telescope DSLR Observation",
                status=HealthState.HEALTHY,
                last_event_at=datetime.now(timezone.utc) - timedelta(minutes=2),
                request_count_15m=91,
                error_count_15m=0,
                latency_p95_ms=112.8,
            ),
        ]

        self._incidents: list[IncidentDetail] = [
            IncidentDetail(
                incident_id="INC-DEMO-RF-001",
                created_at=datetime.now(timezone.utc) - timedelta(minutes=12),
                status=IncidentStatus.INVESTIGATING,
                severity=Severity.MEDIUM,
                module_id="rf-adapter-test",
                title="Elevated RF adapter response latency",
                synthetic=True,
                summary=(
                    "Synthetic demonstration incident showing elevated "
                    "response latency and intermittent adapter errors."
                ),
                symptoms=[
                    "Latency p95 exceeded 400 ms.",
                    "Five errors detected during the last 15 minutes.",
                    "Last successful event is older than expected.",
                ],
                telemetry_labels={
                    "service": "signals-platform",
                    "module": "rf-adapter-test",
                    "environment": "demo",
                },
                grafana_dashboard_path="/d/signals-platform-demo/overview",
            )
        ]

    @property
    def uptime_seconds(self) -> int:
        return max(
            0,
            int((datetime.now(timezone.utc) - self._started_at).total_seconds()),
        )

    def list_modules(self) -> list[ModuleHealth]:
        with self._lock:
            return [module.model_copy(deep=True) for module in self._modules]

    def list_incidents(
        self,
        *,
        limit: int,
        status: IncidentStatus | None,
    ) -> list[IncidentDetail]:
        with self._lock:
            incidents = self._incidents

            if status is not None:
                incidents = [
                    incident
                    for incident in incidents
                    if incident.status == status
                ]

            incidents = sorted(
                incidents,
                key=lambda incident: incident.created_at,
                reverse=True,
            )

            return [
                incident.model_copy(deep=True)
                for incident in incidents[:limit]
            ]

    def get_incident(self, incident_id: str) -> IncidentDetail | None:
        with self._lock:
            for incident in self._incidents:
                if incident.incident_id == incident_id:
                    return incident.model_copy(deep=True)

        return None

    def telemetry_summary(self, window_minutes: int) -> TelemetrySummary:
        factor = max(1, window_minutes // 5)

        return TelemetrySummary(
            generated_at=datetime.now(timezone.utc),
            window_minutes=window_minutes,
            requests_total=214 * factor,
            errors_total=3 * factor,
            latency_p50_ms=41.8,
            latency_p95_ms=118.6,
            events_received_total=93 * factor,
            media_failures_total=1 if window_minutes >= 15 else 0,
            active_observation_sessions=2,
        )

    def create_synthetic_incident(
        self,
        request: SyntheticIncidentRequest,
    ) -> IncidentDetail:
        incident = self._build_incident(request)

        with self._lock:
            self._incidents.append(incident)

        return incident.model_copy(deep=True)

    def _build_incident(
        self,
        request: SyntheticIncidentRequest,
    ) -> IncidentDetail:
        incident_id = f"INC-DEMO-{uuid4().hex[:10].upper()}"

        scenario_map: dict[
            SyntheticIncidentScenario,
            tuple[str, str, list[str]],
        ] = {
            SyntheticIncidentScenario.MODULE_TIMEOUT: (
                "Module response timeout",
                "The selected module exceeded its response-time threshold.",
                [
                    "No successful response was recorded within the threshold.",
                    "The module health state changed to degraded.",
                    "A timeout signature was observed in synthetic telemetry.",
                ],
            ),
            SyntheticIncidentScenario.ELEVATED_API_LATENCY: (
                "Elevated API latency",
                "Synthetic API latency increased above the expected range.",
                [
                    "Latency p95 exceeded the demonstration threshold.",
                    "Request volume remained within the normal demo range.",
                    "No production traffic was involved.",
                ],
            ),
            SyntheticIncidentScenario.EVENT_INGESTION_STALLED: (
                "Event ingestion stalled",
                "The synthetic event stream stopped advancing.",
                [
                    "No new synthetic events were received.",
                    "The last-event timestamp exceeded the freshness limit.",
                    "The affected module remained reachable.",
                ],
            ),
            SyntheticIncidentScenario.MEDIA_PROCESSING_FAILURE: (
                "Media processing failure",
                "A synthetic media-processing task failed validation.",
                [
                    "The synthetic processor returned an error.",
                    "No production media or evidence was accessed.",
                    "The failure was recorded only in the demo incident store.",
                ],
            ),
            SyntheticIncidentScenario.SERVICE_RESTART: (
                "Service restart detected",
                "A synthetic service restart was recorded.",
                [
                    "The simulated restart counter increased.",
                    "A short telemetry gap was observed.",
                    "Service health recovered after the synthetic event.",
                ],
            ),
        }

        title, summary, symptoms = scenario_map[request.scenario]

        return IncidentDetail(
            incident_id=incident_id,
            created_at=datetime.now(timezone.utc),
            status=IncidentStatus.OPEN,
            severity=request.severity,
            module_id=request.module_id,
            title=title,
            synthetic=True,
            summary=summary,
            symptoms=symptoms,
            telemetry_labels={
                "service": "signals-platform",
                "module": request.module_id,
                "scenario": request.scenario.value,
                "environment": "demo",
            },
            grafana_dashboard_path="/d/signals-platform-demo/overview",
        )


mock_store = MockStore()
