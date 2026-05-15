from base.agent import BaseAgent
from base.types import AgentResult
from core.coordinator.aggregator import aggregate_results


class CoordinatorAgent(BaseAgent):
    async def execute(self) -> AgentResult:
        unified = aggregate_results(self.task.payload.get("results", []), self.task.payload.get("memory", {}))
        return AgentResult(
            task_id=self.task.task_id,
            agent_type="coordinator",
            status="complete",
            findings={"unified_findings": unified},
            confidence=unified["overall_confidence"],
            suggested_repairs=unified["repair_targets"],
        )
