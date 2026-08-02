from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agents.investigation_agent import root_agent


APP_NAME = "signals_platform_devpost"
USER_ID = "operator-cli"


async def run_agent(question: str) -> str:
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
                    function_call = getattr(part, "function_call", None)
                    function_response = getattr(part, "function_response", None)

                    if function_call:
                        print(
                            f"[tool call] {function_call.name}",
                            file=sys.stderr,
                        )

                    if function_response:
                        print(
                            f"[tool result] {function_response.name}",
                            file=sys.stderr,
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
    finally:
        close_method = getattr(runner, "close", None)
        if close_method is not None:
            result = close_method()
            if asyncio.iscoroutine(result):
                await result

    return final_text


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Signals Platform Gemini investigator."
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="Operator investigation question.",
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

    missing = [name for name in required if not os.getenv(name)]

    if missing:
        raise SystemExit(
            "Missing environment variables: " + ", ".join(missing)
        )

    result = await run_agent(question)

    print("\n" + "=" * 72)
    print("SIGNALS PLATFORM INVESTIGATION")
    print("=" * 72)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
