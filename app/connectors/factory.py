from __future__ import annotations

from app.connectors.signals_platform_http import (
    RestrictedSignalsPlatformHttpClient,
)
from app.services.settings import settings


def create_signals_platform_client(
) -> RestrictedSignalsPlatformHttpClient:
    return RestrictedSignalsPlatformHttpClient(
        base_url=settings.signals_platform_base_url,
        api_token=settings.restricted_api_token,
        timeout_seconds=settings.signals_platform_timeout_seconds,
    )
