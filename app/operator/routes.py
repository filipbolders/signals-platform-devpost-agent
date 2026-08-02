from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict

from app.api.dependencies import require_restricted_token
from app.models.contracts import (
    Severity,
    SyntheticIncidentScenario,
)
from app.operator.manager import (
    create_investigation,
    get_investigation,
    list_investigations,
)


templates = Jinja2Templates(directory="app/templates")

page_router = APIRouter()
api_router = APIRouter(
    prefix="/api/operator",
    dependencies=[Depends(require_restricted_token)],
)


class LaunchInvestigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: SyntheticIncidentScenario = (
        SyntheticIncidentScenario.ELEVATED_API_LATENCY
    )
    module_id: str = "rf-adapter-test"
    severity: Severity = Severity.MEDIUM


@page_router.get(
    "/operator",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def operator_console(
    request: Request,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="operator.html",
        context={},
    )


@api_router.post(
    "/investigations",
    status_code=status.HTTP_202_ACCEPTED,
)
async def launch_investigation(
    payload: LaunchInvestigationRequest,
) -> dict[str, object]:
    job = await create_investigation(
        scenario=payload.scenario,
        module_id=payload.module_id,
        severity=payload.severity,
    )

    return job


@api_router.get("/investigations")
async def get_investigations() -> dict[str, object]:
    return {
        "investigations": await list_investigations(),
    }


@api_router.get("/investigations/{investigation_id}")
async def get_investigation_status(
    investigation_id: str,
) -> dict[str, object]:
    job = await get_investigation(investigation_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )

    return job
