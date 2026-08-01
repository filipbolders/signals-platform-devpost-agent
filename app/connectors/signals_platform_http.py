from __future__ import annotations

from typing import Any

import httpx
from pydantic import ValidationError

from app.connectors.errors import (
    SignalsPlatformAuthenticationError,
    SignalsPlatformNotFoundError,
    SignalsPlatformRateLimitError,
    SignalsPlatformResponseError,
    SignalsPlatformUnavailableError,
)
from app.models.contracts import (
    IncidentDetail,
    IncidentStatus,
    ModuleHealth,
    PlatformHealth,
    SyntheticIncidentRequest,
    TelemetrySummary,
)


class RestrictedSignalsPlatformHttpClient:
    """Typed client for the restricted Signals Platform Devpost API."""

    def __init__(
        self,
        *,
        base_url: str,
        api_token: str,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("base_url must not be empty")

        if len(api_token) < 16:
            raise ValueError("api_token must be at least 16 characters")

        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            headers={
                "Authorization": f"Bearer {api_token}",
                "Accept": "application/json",
                "User-Agent": "signals-platform-devpost-agent/0.1",
            },
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
        )

    async def __aenter__(
        self,
    ) -> RestrictedSignalsPlatformHttpClient:
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_health(self) -> PlatformHealth:
        payload = await self._request_json("GET", "health")

        return self._validate_model(
            PlatformHealth,
            payload,
            resource="platform health",
        )

    async def list_modules(self) -> list[ModuleHealth]:
        payload = await self._request_json("GET", "modules")

        modules_payload = payload.get("modules")

        if not isinstance(modules_payload, list):
            raise SignalsPlatformResponseError(
                "Restricted API response does not contain a modules list"
            )

        try:
            return [
                ModuleHealth.model_validate(module)
                for module in modules_payload
            ]
        except ValidationError as exc:
            raise SignalsPlatformResponseError(
                "Restricted API returned invalid module data"
            ) from exc

    async def list_incidents(
        self,
        *,
        limit: int = 20,
        status: IncidentStatus | None = None,
    ) -> list[IncidentDetail]:
        if limit < 1 or limit > 50:
            raise ValueError("limit must be between 1 and 50")

        params: dict[str, str | int] = {
            "limit": limit,
        }

        if status is not None:
            params["status"] = status.value

        payload = await self._request_json(
            "GET",
            "incidents",
            params=params,
        )

        incidents_payload = payload.get("incidents")

        if not isinstance(incidents_payload, list):
            raise SignalsPlatformResponseError(
                "Restricted API response does not contain an incidents list"
            )

        try:
            return [
                IncidentDetail.model_validate(incident)
                for incident in incidents_payload
            ]
        except ValidationError as exc:
            raise SignalsPlatformResponseError(
                "Restricted API returned invalid incident data"
            ) from exc

    async def get_incident(
        self,
        incident_id: str,
    ) -> IncidentDetail:
        if not incident_id.startswith("INC-"):
            raise ValueError("incident_id must start with INC-")

        payload = await self._request_json(
            "GET",
            f"incidents/{incident_id}",
        )

        return self._validate_model(
            IncidentDetail,
            payload,
            resource="incident",
        )

    async def get_telemetry_summary(
        self,
        *,
        window_minutes: int = 15,
    ) -> TelemetrySummary:
        if window_minutes not in {5, 15, 30, 60}:
            raise ValueError(
                "window_minutes must be one of 5, 15, 30, or 60"
            )

        payload = await self._request_json(
            "GET",
            "telemetry-summary",
            params={"window_minutes": window_minutes},
        )

        return self._validate_model(
            TelemetrySummary,
            payload,
            resource="telemetry summary",
        )

    async def create_synthetic_incident(
        self,
        request: SyntheticIncidentRequest,
    ) -> IncidentDetail:
        payload = await self._request_json(
            "POST",
            "demo/incidents",
            json=request.model_dump(mode="json"),
        )

        return self._validate_model(
            IncidentDetail,
            payload,
            resource="synthetic incident",
        )

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self._client.request(
                method,
                path,
                params=params,
                json=json,
            )
        except httpx.TimeoutException as exc:
            raise SignalsPlatformUnavailableError(
                "Restricted Signals Platform API request timed out"
            ) from exc
        except httpx.RequestError as exc:
            raise SignalsPlatformUnavailableError(
                "Restricted Signals Platform API is unavailable"
            ) from exc

        if response.status_code == 401:
            raise SignalsPlatformAuthenticationError(
                "Restricted Signals Platform API authentication failed"
            )

        if response.status_code == 404:
            raise SignalsPlatformNotFoundError(
                "Restricted Signals Platform resource was not found"
            )

        if response.status_code == 429:
            raise SignalsPlatformRateLimitError(
                "Restricted Signals Platform API rate limit exceeded"
            )

        if response.status_code >= 500:
            raise SignalsPlatformUnavailableError(
                "Restricted Signals Platform API returned a server error"
            )

        if response.is_error:
            raise SignalsPlatformResponseError(
                "Restricted Signals Platform API returned "
                f"HTTP {response.status_code}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise SignalsPlatformResponseError(
                "Restricted Signals Platform API returned invalid JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise SignalsPlatformResponseError(
                "Restricted Signals Platform API returned an invalid payload"
            )

        return payload

    @staticmethod
    def _validate_model(
        model_type: type[Any],
        payload: dict[str, Any],
        *,
        resource: str,
    ) -> Any:
        try:
            return model_type.model_validate(payload)
        except ValidationError as exc:
            raise SignalsPlatformResponseError(
                f"Restricted API returned invalid {resource} data"
            ) from exc
