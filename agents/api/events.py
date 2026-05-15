from datetime import datetime, timezone
from typing import Any


EVENTS: list[dict[str, Any]] = []


async def emit_event(event: str, pipeline_id: str, data: dict[str, Any]) -> dict[str, Any]:
    message = {
        "event": event,
        "pipeline_id": pipeline_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    EVENTS.append(message)
    return message
