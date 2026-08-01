from __future__ import annotations

from typing import Protocol

from app.models.contracts import (
    IncidentDetail,
    IncidentStatus,
    ModuleHealth,
    PlatformHealth,
    SyntheticIncidentRequest,
    TelemetrySummary,
)


class SignalsPlatformClient(Protocol):
    async def get_health(self) -> PlatformHealth:
        """Return sanitised platform health."""

    async def list_modules(self) -> list[ModuleHealth]:
        """Return only approved module health records."""

    async def list_incidents(
        self,
        *,
        limit: int = 20,
        status: IncidentStatus | None = None,
    ) -> list[IncidentDetail]:
        """Return sanitised operational incidents."""

    async def get_incident(self, incident_id: str) -> IncidentDetail:
        """Return one sanitised incident."""

    async def get_telemetry_summary(
        self,
        *,
        window_minutes: int = 15,
    ) -> TelemetrySummary:
        """Return aggregated, non-sensitive telemetry."""

    async def create_synthetic_incident(
        self,
        request: SyntheticIncidentRequest,
    ) -> IncidentDetail:
        """Create a demo-only synthetic incident."""
