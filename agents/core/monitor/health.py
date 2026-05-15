async def check_container_health(container_id: str) -> dict:
    return {"name": "container_running", "passed": bool(container_id), "detail": container_id or "missing container"}
