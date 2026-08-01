from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.contracts import (
    HealthState,
    PlatformHealth,
    SyntheticIncidentRequest,
)


def test_platform_health_accepts_sanitised_data() -> None:
    model = PlatformHealth(
        generated_at=datetime.now(timezone.utc),
        status=HealthState.HEALTHY,
        version="0.1.0",
        uptime_seconds=3600,
        api_latency_ms=12.4,
        active_modules=4,
        unhealthy_modules=0,
    )

    assert model.platform == "signals-platform"
    assert model.status == HealthState.HEALTHY


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        PlatformHealth(
            generated_at=datetime.now(timezone.utc),
            status=HealthState.HEALTHY,
            uptime_seconds=3600,
            api_latency_ms=12.4,
            active_modules=4,
            unhealthy_modules=0,
            customer_email="must-not-be-exposed",
        )


def test_synthetic_scenario_is_restricted() -> None:
    with pytest.raises(ValidationError):
        SyntheticIncidentRequest(
            scenario="execute-shell-command",
        )
