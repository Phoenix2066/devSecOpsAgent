from api.events import emit_event
from base.types import AgentResult
from base.worker import BaseWorker
from tools.search_tool import search


class WebSearchWorker(BaseWorker):
    worker_type = "web_search"

    async def execute(self) -> AgentResult:
        query = self.task.payload.get("query", "python requests dependency conflict")
        await emit_event("web_search_started", self.task.pipeline_id, {"query": query})
        results = await search(query)
        await emit_event("web_search_complete", self.task.pipeline_id, {"query": query, "results": results})
        return AgentResult(
            task_id=self.task.task_id,
            agent_type=self.worker_type,
            status="complete",
            findings={"query": query, "results": results, "summary": "Use a compatible requests version and regenerate lock files."},
            confidence=0.7,
            suggested_repairs=["repair_imports"],
        )
