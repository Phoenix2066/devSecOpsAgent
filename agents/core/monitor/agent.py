from base.agent import BaseAgent
from base.types import AgentResult
from core.monitor.health import check_container_health


class MonitoringAgent(BaseAgent):
    async def execute(self) -> AgentResult:
        check = await check_container_health(self.task.payload.get("container_id", ""))
        return AgentResult(task_id=self.task.task_id, agent_type="monitor", status="complete", findings={"checks": [check]}, confidence=1.0 if check["passed"] else 0.0)
