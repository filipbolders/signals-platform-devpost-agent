from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router


app = FastAPI(
    title="Signals Platform Devpost Mock API",
    version="0.1.0",
    description=(
        "Synthetic implementation of the restricted Signals Platform "
        "Devpost API contract."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.include_router(router)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "service": "signals-platform-devpost-mock",
        "status": "running",
        "mode": "synthetic",
    }
