from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict

from app.api.dependencies import require_restricted_token
from app.models.contracts import (
    Severity,
    SyntheticIncidentScenario,
)
from app.operator.manager import (
    PROJECT_ROOT,
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


@api_router.get(
    "/investigations/{investigation_id}/reports/{report_format}",
)
async def download_investigation_report(
    investigation_id: str,
    report_format: str,
) -> FileResponse:
    if report_format not in {"json", "markdown"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report format must be json or markdown",
        )

    job = await get_investigation(investigation_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )

    report_files = job.get("report_files")

    if not isinstance(report_files, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation report is not available",
        )

    relative_path = report_files.get(report_format)

    if not isinstance(relative_path, str):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested report format is unavailable",
        )

    file_path = (PROJECT_ROOT / relative_path).resolve()
    report_root = (
        PROJECT_ROOT / "artifacts" / "investigations"
    ).resolve()

    if report_root not in file_path.parents:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid report path",
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file no longer exists",
        )

    media_type = (
        "application/json"
        if report_format == "json"
        else "text/markdown"
    )

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=file_path.name,
    )

