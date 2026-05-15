from api.events import emit_event
from shadow.environment import BuildResult, ShadowEnvironment

MAX_ITERATIONS = 2


class FeedbackLoop:
    def __init__(self, pipeline_id: str, shadow_env: ShadowEnvironment, orchestrator, redis_client):
        self.pipeline_id = pipeline_id
        self.shadow_env = shadow_env
        self.orchestrator = orchestrator
        self.redis = redis_client
        self.history: list[dict] = []

    async def run(self) -> bool:
        for iteration in range(1, MAX_ITERATIONS + 1):
            result = await self.shadow_env.run_build()
            self.history.append(result.model_dump())
            await emit_event("repair_iteration", self.pipeline_id, {"iteration": iteration, "status": "passed" if result.passed else "failed", "logs_summary": result.output, "next_action": "promote" if result.passed else "repair_imports"})
            if result.passed:
                await emit_event("validation_passed", self.pipeline_id, {"iteration": iteration})
                return True
            await self.shadow_env.apply_patches({"requirements.txt": "requests==2.31.0\nflask==2.3.0\n"})
        await emit_event("validation_failed", self.pipeline_id, {"iterations": MAX_ITERATIONS})
        return False

    def build_context(self, build_result: BuildResult) -> dict:
        previous = self.history[-1]["output"] if self.history else ""
        return {
            "current_logs": build_result.output,
            "previous_attempts": self.history,
            "iteration_count": len(self.history),
            "error_signature_delta": build_result.output != previous,
        }
