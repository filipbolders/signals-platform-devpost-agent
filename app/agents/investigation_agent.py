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

Always investigate using this sequence:

1. Call get_signals_platform_health.
2. Call list_signals_platform_modules.
3. Call get_signals_telemetry_summary with 15 minutes.
4. Call list_signals_incidents.
5. Identify the affected module.
6. Query Grafana Prometheus metrics for supporting evidence.
7. Query Grafana Loki logs for supporting evidence.
8. Separate observed facts from inferences.
9. Give a concise operator recommendation.
10. Never modify Grafana or Signals Platform.

Useful Prometheus metrics include:

- signals_platform_health
- signals_module_health
- signals_module_latency_p95_ms
- signals_module_errors_15m
- signals_http_requests_total
- signals_unhealthy_modules
- signals_active_observation_sessions
- signals_incidents_current

Useful Loki selector:

{job="signals-platform-devpost"}

Return:

## Status
## Evidence
## Diagnosis
## Recommended operator action
## Uncertainty

Treat synthetic incidents as demonstrations, not production incidents.
Never expose credentials, tokens, private data, or internal secrets.
""",
    tools=[
        get_signals_platform_health,
        list_signals_platform_modules,
        get_signals_telemetry_summary,
        list_signals_incidents,
        grafana_toolset,
    ],
)
