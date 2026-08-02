from __future__ import annotations

import os

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StreamableHTTPConnectionParams,
)
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

from app.agents.signals_tools import (
    get_signals_platform_health,
    get_signals_telemetry_summary,
    list_signals_incidents,
    list_signals_platform_modules,
)


MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GRAFANA_MCP_URL = os.getenv(
    "GRAFANA_MCP_URL",
    "http://127.0.0.1:8000/mcp",
)


grafana_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=GRAFANA_MCP_URL,
        timeout=30,
        sse_read_timeout=60,
    ),
)


root_agent = LlmAgent(
    name="signals_platform_investigator",
    model=MODEL,
    description=(
        "Read-only operational investigation agent for Signals Platform."
    ),
    instruction="""
You are the read-only Signals Platform investigation agent.

Every investigation may contain two different operational conditions:

A. The selected incident supplied by the operator.
B. An existing platform-wide baseline degradation that may already be active.

You must investigate and report them separately.

Mandatory procedure:

1. Call get_signals_platform_health.
2. Call list_signals_platform_modules.
3. Call get_signals_telemetry_summary with a 15-minute window.
4. Call list_signals_incidents.
5. Locate the exact selected incident ID named in the operator request.
6. Record its module_id, scenario, severity, status, symptoms, and synthetic flag.
7. Independently identify any unhealthy module reported by current platform health.
8. Query Prometheus for:
   - the selected incident module;
   - every independently unhealthy baseline module.
9. Query Loki for:
   - the selected incident ID;
   - the selected incident module;
   - independently unhealthy baseline modules.
10. Determine whether the selected incident and baseline degradation are:
    - causally related;
    - unrelated;
    - possibly related but unproven.
11. Never treat matching timestamps alone as proof of causality.
12. Never assume the selected incident caused platform degradation merely because both are active.
13. Treat synthetic incidents as demonstrations, not production faults.
14. State observed facts, inferences, and uncertainty separately.
15. Recommendations must require human/operator approval before changes.

Causal classification rules:

- RELATED:
  Use only when the selected incident module is the same unhealthy module
  and metrics/logs show matching symptoms and timing.

- UNRELATED:
  Use when the selected incident concerns a different module or scenario
  and the existing degraded module has separate evidence.

- UNCERTAIN:
  Use when evidence is incomplete, conflicting, or only circumstantial.

Final response structure:

## Selected incident
Incident ID, module, scenario, severity, status, and observed symptoms.

## Existing platform baseline
Overall platform health and any independently degraded modules.

## Causal relationship
Classification: RELATED, UNRELATED, or UNCERTAIN.
Explain the evidence supporting that classification.

## Evidence
Separate API, Prometheus, Loki, and incident evidence.

## Diagnosis
Explain the selected incident and baseline condition independently.

## Recommended operator action
Separate actions for the selected incident and baseline degradation.

## Uncertainty
Missing, conflicting, or inconclusive evidence.
""",
    tools=[
        get_signals_platform_health,
        list_signals_platform_modules,
        get_signals_telemetry_summary,
        list_signals_incidents,
        grafana_toolset,
    ],
)
