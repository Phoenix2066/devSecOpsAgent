from base.agent import BaseAgent
from base.types import AgentResult, AgentTask
from core.coordinator.agent import CoordinatorAgent
from core.memory.agent import MemoryAgent
from core.orchestrator.spawner import spawn_worker


class OrchestratorAgent(BaseAgent):
    async def execute(self) -> AgentResult:
        log_result = await spawn_worker("log_analyzer", AgentTask(pipeline_id=self.task.pipeline_id, agent_type="log_analyzer", payload=self.task.payload))
        dep_result = await spawn_worker("dependency_inspector", AgentTask(pipeline_id=self.task.pipeline_id, agent_type="dependency_inspector", payload=self.task.payload))
        signature = log_result.findings.get("error_signature", "")
        memory = await MemoryAgent(self.task).search_incidents(signature)
        if not memory.get("hit"):
            await spawn_worker("web_search", AgentTask(pipeline_id=self.task.pipeline_id, agent_type="web_search", payload={"query": signature}))
        coordinator_payload = {"results": [log_result.model_dump(), dep_result.model_dump()], "memory": memory}
        return await CoordinatorAgent(AgentTask(pipeline_id=self.task.pipeline_id, agent_type="coordinator", payload=coordinator_payload)).execute()
