from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.telemetry_client import emit_agent_event
from app.connectors.factory import create_signals_platform_client
from app.models.contracts import (
    Severity,
    SyntheticIncidentRequest,
    SyntheticIncidentScenario,
)
from scripts.run_investigation_agent import run_agent


REPORT_DIR = PROJECT_ROOT / "artifacts" / "investigations"


async def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    request = SyntheticIncidentRequest(
        scenario=SyntheticIncidentScenario.ELEVATED_API_LATENCY,
        module_id="rf-adapter-test",
        severity=Severity.MEDIUM,
    )

    async with create_signals_platform_client() as client:
        incident = await client.create_synthetic_incident(request)

    investigation_id = f"INV-{uuid4().hex[:14].upper()}"

    question = (
        f"Investigate synthetic incident {incident.incident_id}. "
        f"The affected module is {incident.module_id}. "
        "Verify the incident using the restricted Signals Platform API, "
        "Prometheus metrics, and Loki logs. Separate facts from "
        "inferences and recommend a human-approved operator action."
    )

    report_text = await run_agent(
        question,
        investigation_id=investigation_id,
        incident_id=incident.incident_id,
    )

    timestamp = datetime.now(timezone.utc)
    basename = (
        f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}-"
        f"{investigation_id}-{incident.incident_id}"
    )

    json_path = REPORT_DIR / f"{basename}.json"
    markdown_path = REPORT_DIR / f"{basename}.md"

    report_payload = {
        "generated_at": timestamp.isoformat(),
        "investigation_id": investigation_id,
        "incident": incident.model_dump(mode="json"),
        "question": question,
        "report": report_text,
        "synthetic": True,
    }

    json_path.write_text(
        json.dumps(report_payload, indent=2),
        encoding="utf-8",
    )

    markdown_path.write_text(
        "\n".join(
            [
                "# Signals Platform Investigation",
                "",
                f"- Investigation ID: `{investigation_id}`",
                f"- Incident ID: `{incident.incident_id}`",
                f"- Generated: `{timestamp.isoformat()}`",
                "- Environment: `demo`",
                "- Synthetic: `true`",
                "",
                report_text,
                "",
            ]
        ),
        encoding="utf-8",
    )

    await emit_agent_event(
        event_type="report_saved",
        investigation_id=investigation_id,
        incident_id=incident.incident_id,
        outcome="success",
        report_path=str(markdown_path.relative_to(PROJECT_ROOT)),
    )

    print("=" * 72)
    print("DETERMINISTIC DEMO ORCHESTRATION COMPLETE")
    print("=" * 72)
    print(f"Incident:      {incident.incident_id}")
    print(f"Investigation: {investigation_id}")
    print(f"JSON report:   {json_path}")
    print(f"Markdown:      {markdown_path}")


if __name__ == "__main__":
    asyncio.run(main())
