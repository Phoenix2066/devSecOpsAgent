from api.events import emit_event
from base.agent import BaseAgent
from base.types import AgentResult
from core.memory.retrieval import search_seeded_incidents

INCIDENTS: list[dict] = []


class MemoryAgent(BaseAgent):
    async def execute(self) -> AgentResult:
        result = await self.search_incidents(self.task.payload.get("error_signature", ""))
        return AgentResult(task_id=self.task.task_id, agent_type="memory", status="complete", findings=result, confidence=result.get("confidence", 0))

    async def search_incidents(self, error_signature: str) -> dict:
        result = search_seeded_incidents(error_signature)
        await emit_event("memory_hit" if result.get("hit") else "memory_miss", self.task.pipeline_id, result)
        return result

    @staticmethod
    async def store_incident(incident: dict) -> dict:
        INCIDENTS.append(incident)
        return {"stored": True, "incident": incident}
