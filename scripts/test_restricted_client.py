from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.connectors.factory import create_signals_platform_client


async def main() -> None:
    async with create_signals_platform_client() as client:
        health = await client.get_health()
        modules = await client.list_modules()
        telemetry = await client.get_telemetry_summary(
            window_minutes=15,
        )
        incidents = await client.list_incidents(limit=5)

    result = {
        "health": health.model_dump(mode="json"),
        "modules": [
            module.model_dump(mode="json")
            for module in modules
        ],
        "telemetry": telemetry.model_dump(mode="json"),
        "incidents": [
            incident.model_dump(mode="json")
            for incident in incidents
        ],
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
