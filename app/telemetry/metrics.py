from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram


HTTP_REQUESTS_TOTAL = Counter(
    "signals_http_requests_total",
    "Total HTTP requests handled by the Devpost Signals Platform API.",
    ["method", "route", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "signals_http_request_duration_seconds",
    "HTTP request duration for the Devpost Signals Platform API.",
    ["method", "route"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
    ),
)

HTTP_EXCEPTIONS_TOTAL = Counter(
    "signals_http_exceptions_total",
    "Unhandled HTTP request exceptions.",
    ["method", "route", "exception_type"],
)

PLATFORM_HEALTH = Gauge(
    "signals_platform_health",
    "Signals Platform health: 1 healthy, 0.5 degraded, 0 unavailable.",
)

ACTIVE_MODULES = Gauge(
    "signals_active_modules",
    "Number of approved Signals Platform modules.",
)

UNHEALTHY_MODULES = Gauge(
    "signals_unhealthy_modules",
    "Number of approved modules not currently healthy.",
)

MODULE_HEALTH = Gauge(
    "signals_module_health",
    "Module health: 1 healthy, 0.5 degraded, 0 unavailable.",
    ["module_id"],
)

MODULE_REQUESTS_15M = Gauge(
    "signals_module_requests_15m",
    "Synthetic module requests during the latest 15-minute window.",
    ["module_id"],
)

MODULE_ERRORS_15M = Gauge(
    "signals_module_errors_15m",
    "Synthetic module errors during the latest 15-minute window.",
    ["module_id"],
)

MODULE_LATENCY_P95_MS = Gauge(
    "signals_module_latency_p95_ms",
    "Synthetic module p95 latency in milliseconds.",
    ["module_id"],
)

EVENTS_RECEIVED_TOTAL = Gauge(
    "signals_events_received_window_total",
    "Synthetic events received during the selected telemetry window.",
    ["window_minutes"],
)

MEDIA_FAILURES_TOTAL = Gauge(
    "signals_media_failures_window_total",
    "Synthetic media failures during the selected telemetry window.",
    ["window_minutes"],
)

ACTIVE_OBSERVATION_SESSIONS = Gauge(
    "signals_active_observation_sessions",
    "Current synthetic observation sessions.",
)

SYNTHETIC_INCIDENTS_CREATED_TOTAL = Counter(
    "signals_synthetic_incidents_created_total",
    "Synthetic incidents created for demonstrations.",
    ["scenario", "module_id", "severity"],
)

INCIDENTS_CURRENT = Gauge(
    "signals_incidents_current",
    "Current number of synthetic incidents by status and severity.",
    ["status", "severity"],
)


HEALTH_VALUES = {
    "healthy": 1.0,
    "degraded": 0.5,
    "unavailable": 0.0,
    "unknown": 0.0,
}


AGENT_INVESTIGATIONS_TOTAL = Counter(
    "signals_agent_investigations_total",
    "Total Gemini investigations by outcome.",
    ["outcome"],
)

AGENT_INVESTIGATION_DURATION_SECONDS = Histogram(
    "signals_agent_investigation_duration_seconds",
    "Gemini investigation duration in seconds.",
    buckets=(1, 2.5, 5, 10, 20, 30, 60, 120, 300),
)

AGENT_TOOL_CALLS_TOTAL = Counter(
    "signals_agent_tool_calls_total",
    "Total tool calls made by the Gemini investigation agent.",
    ["tool_name"],
)

AGENT_TOOL_RESULTS_TOTAL = Counter(
    "signals_agent_tool_results_total",
    "Agent tool results by tool name and outcome.",
    ["tool_name", "outcome"],
)

AGENT_REPORTS_SAVED_TOTAL = Counter(
    "signals_agent_reports_saved_total",
    "Investigation reports successfully saved.",
)
