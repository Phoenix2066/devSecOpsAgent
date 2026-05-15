class ValidationRunner:
    async def run_health_checks(self, container_id: str) -> dict:
        checks = [{"name": "container_running", "passed": bool(container_id), "detail": container_id or "missing container"}]
        return {"passed": all(check["passed"] for check in checks), "checks": checks}

    async def compute_promotion_confidence(self, validation: dict, iteration: int, memory_confidence: float) -> float:
        base = 1.0 if validation.get("passed") else 0.0
        penalty = 0.05 * max(iteration - 1, 0)
        boost = 0.1 if memory_confidence > 0.8 else 0.0
        return max(0.0, min(1.0, base - penalty + boost))
