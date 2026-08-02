from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.routes import router
from app.operator.routes import api_router, page_router
from app.telemetry.logging import configure_json_logging
from app.telemetry.middleware import RequestTelemetryMiddleware
from app.telemetry.snapshot import refresh_application_metrics


configure_json_logging()


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    refresh_application_metrics()
    yield


app = FastAPI(
    title="Signals Platform Devpost Mock API",
    version="0.2.0",
    description=(
        "Synthetic implementation of the restricted Signals Platform "
        "Devpost API contract."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(RequestTelemetryMiddleware)
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)
app.include_router(router)
app.include_router(page_router)
app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "service": "signals-platform-devpost-mock",
        "status": "running",
        "mode": "synthetic",
    }


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    refresh_application_metrics()

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
