from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agents.investigation_agent import root_agent
from app.agents.telemetry_client import emit_agent_event


APP_NAME = "signals_platform_devpost"
USER_ID = "operator-cli"


def _tool_result_failed(function_response: object) -> bool:
    response = getattr(function_response, "response", None)

    if isinstance(response, dict):
        if response.get("ok") is False:
            return True

        text = str(response).lower()

        return any(
            marker in text
            for marker in (
                "403 forbidden",
                "permission denied",
                "unauthorized",
                '"error"',
                "'error'",
            )
        )

    return False


async def run_agent(
    question: str,
    *,
    investigation_id: str | None = None,
    incident_id: str | None = None,
) -> str:
    investigation_id = investigation_id or (
        f"INV-{uuid4().hex[:14].upper()}"
    )

    started = time.perf_counter()

    await emit_agent_event(
        event_type="investigation_started",
        investigation_id=investigation_id,
        incident_id=incident_id,
        outcome="started",
    )

    session_service = InMemorySessionService()
    session_id = f"investigation-{uuid4().hex[:12]}"

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text=question)],
    )

    final_text = "No final response was produced."

    try:
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    function_call = getattr(
                        part,
                        "function_call",
                        None,
                    )
                    function_response = getattr(
                        part,
                        "function_response",
                        None,
                    )

                    if function_call:
                        print(
                            f"[tool call] {function_call.name}",
                            file=sys.stderr,
                        )

                        await emit_agent_event(
                            event_type="tool_called",
                            investigation_id=investigation_id,
                            incident_id=incident_id,
                            tool_name=function_call.name,
                            outcome="started",
                        )

                    if function_response:
                        failed = _tool_result_failed(
                            function_response
                        )

                        print(
                            f"[tool result] {function_response.name}",
                            file=sys.stderr,
                        )

                        await emit_agent_event(
                            event_type=(
                                "tool_failed"
                                if failed
                                else "tool_succeeded"
                            ),
                            investigation_id=investigation_id,
                            incident_id=incident_id,
                            tool_name=function_response.name,
                            outcome=(
                                "failure"
                                if failed
                                else "success"
                            ),
                        )

            if (
                event.is_final_response()
                and event.content
                and event.content.parts
            ):
                text_parts = [
                    part.text
                    for part in event.content.parts
                    if getattr(part, "text", None)
                ]

                if text_parts:
                    final_text = "\n".join(text_parts).strip()

        duration = time.perf_counter() - started

        await emit_agent_event(
            event_type="investigation_completed",
            investigation_id=investigation_id,
            incident_id=incident_id,
            outcome="success",
            duration_seconds=duration,
        )

        return final_text

    except Exception as exc:
        duration = time.perf_counter() - started

        await emit_agent_event(
            event_type="investigation_failed",
            investigation_id=investigation_id,
            incident_id=incident_id,
            outcome="failure",
            duration_seconds=duration,
            error_type=type(exc).__name__,
        )
        raise

    finally:
        close_method = getattr(runner, "close", None)

        if close_method is not None:
            result = close_method()

            if asyncio.iscoroutine(result):
                await result


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Signals Platform Gemini investigator."
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="Operator investigation question.",
    )
    parser.add_argument(
        "--incident-id",
        default=None,
        help="Optional incident identifier.",
    )
    args = parser.parse_args()

    question = " ".join(args.question).strip()

    if not question:
        question = (
            "Why is the Signals Platform degraded? "
            "Identify the affected module, inspect Grafana metrics "
            "and Loki logs, and recommend the next operator action."
        )

    required = (
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "GEMINI_MODEL",
        "GRAFANA_MCP_URL",
    )

    missing = [
        name
        for name in required
        if not os.getenv(name)
    ]

    if missing:
        raise SystemExit(
            "Missing environment variables: "
            + ", ".join(missing)
        )

    investigation_id = f"INV-{uuid4().hex[:14].upper()}"

    result = await run_agent(
        question,
        investigation_id=investigation_id,
        incident_id=args.incident_id,
    )

    print("\n" + "=" * 72)
    print("SIGNALS PLATFORM INVESTIGATION")
    print(f"Investigation ID: {investigation_id}")
    print("=" * 72)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
