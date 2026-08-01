import httpx
import pytest

from app.connectors.errors import (
    SignalsPlatformAuthenticationError,
    SignalsPlatformNotFoundError,
)
from app.connectors.signals_platform_http import (
    RestrictedSignalsPlatformHttpClient,
)
from app.main import app
from app.models.contracts import (
    HealthState,
    IncidentStatus,
    Severity,
    SyntheticIncidentRequest,
    SyntheticIncidentScenario,
)
from app.services.settings import settings


@pytest.fixture
def transport() -> httpx.ASGITransport:
    return httpx.ASGITransport(app=app)


@pytest.mark.asyncio
async def test_client_reads_platform_health(
    transport: httpx.ASGITransport,
) -> None:
    async with RestrictedSignalsPlatformHttpClient(
        base_url="http://test/api/devpost/v1",
        api_token=settings.restricted_api_token,
        transport=transport,
    ) as client:
        health = await client.get_health()

    assert health.platform == "signals-platform"
    assert health.status in {
        HealthState.HEALTHY,
        HealthState.DEGRADED,
    }


@pytest.mark.asyncio
async def test_client_lists_approved_modules(
    transport: httpx.ASGITransport,
) -> None:
    async with RestrictedSignalsPlatformHttpClient(
        base_url="http://test/api/devpost/v1",
        api_token=settings.restricted_api_token,
        transport=transport,
    ) as client:
        modules = await client.list_modules()

    assert len(modules) == 4
    assert modules[0].module_id in {
        "object-tracker",
        "gps-live-map",
        "rf-adapter-test",
        "telescope-dslr-observation",
    }


@pytest.mark.asyncio
async def test_client_lists_incidents(
    transport: httpx.ASGITransport,
) -> None:
    async with RestrictedSignalsPlatformHttpClient(
        base_url="http://test/api/devpost/v1",
        api_token=settings.restricted_api_token,
        transport=transport,
    ) as client:
        incidents = await client.list_incidents(
            limit=10,
            status=IncidentStatus.INVESTIGATING,
        )

    assert incidents
    assert all(
        incident.status == IncidentStatus.INVESTIGATING
        for incident in incidents
    )


@pytest.mark.asyncio
async def test_client_creates_synthetic_incident(
    transport: httpx.ASGITransport,
) -> None:
    request = SyntheticIncidentRequest(
        scenario=SyntheticIncidentScenario.EVENT_INGESTION_STALLED,
        module_id="object-tracker",
        severity=Severity.HIGH,
    )

    async with RestrictedSignalsPlatformHttpClient(
        base_url="http://test/api/devpost/v1",
        api_token=settings.restricted_api_token,
        transport=transport,
    ) as client:
        incident = await client.create_synthetic_incident(request)

    assert incident.synthetic is True
    assert incident.module_id == "object-tracker"
    assert incident.severity == Severity.HIGH


@pytest.mark.asyncio
async def test_client_rejects_invalid_token(
    transport: httpx.ASGITransport,
) -> None:
    async with RestrictedSignalsPlatformHttpClient(
        base_url="http://test/api/devpost/v1",
        api_token="incorrect-token-value",
        transport=transport,
    ) as client:
        with pytest.raises(SignalsPlatformAuthenticationError):
            await client.get_health()


@pytest.mark.asyncio
async def test_client_handles_missing_incident(
    transport: httpx.ASGITransport,
) -> None:
    async with RestrictedSignalsPlatformHttpClient(
        base_url="http://test/api/devpost/v1",
        api_token=settings.restricted_api_token,
        transport=transport,
    ) as client:
        with pytest.raises(SignalsPlatformNotFoundError):
            await client.get_incident("INC-DEMO-NOTFOUND")
