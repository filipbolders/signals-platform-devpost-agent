from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.telemetry.metrics import (
    HTTP_EXCEPTIONS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
)


logger = logging.getLogger("signals.telemetry")


def _route_name(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)

    if isinstance(path, str):
        return path

    return "unmatched"


class RequestTelemetryMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next,
    ) -> Response:
        started = time.perf_counter()
        request_id = request.headers.get("x-request-id") or uuid4().hex

        try:
            response = await call_next(request)
        except Exception as exc:
            route = _route_name(request)
            duration = time.perf_counter() - started

            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                route=route,
                status_code="500",
            ).inc()

            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=request.method,
                route=route,
            ).observe(duration)

            HTTP_EXCEPTIONS_TOTAL.labels(
                method=request.method,
                route=route,
                exception_type=type(exc).__name__,
            ).inc()

            logger.exception(
                "request_failed",
                extra={
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "route": route,
                    "status_code": 500,
                    "duration_ms": round(duration * 1000, 3),
                },
            )
            raise

        route = _route_name(request)
        duration = time.perf_counter() - started

        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            route=route,
            status_code=str(response.status_code),
        ).inc()

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=request.method,
            route=route,
        ).observe(duration)

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request_completed",
            extra={
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "route": route,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 3),
            },
        )

        return response
