import time
import logging
from abc import abstractmethod
from typing import List, Dict, Any
from .agent import BaseAgent
from .types import AgentTask, AgentResult, AgentStatus
from db.redis import get_state, enqueue
from api.events import emit_agent_complete, emit_agent_failed

logger = logging.getLogger(__name__)

class BaseWorker(BaseAgent):
    """
    Abstract base for all dynamic worker agents.
    Workers are spawned per-task and terminated after completion.
    They run execute() once and exit — not an infinite loop.
    """

    def __init__(self, task: AgentTask):
        super().__init__(
            agent_id=task.task_id,
            pipeline_id=task.pipeline_id
        )
        self.task = task

    @abstractmethod
    async def execute(self) -> AgentResult:
        """Workers implement this to return a single AgentResult."""
        raise NotImplementedError

    async def run(self) -> AgentResult:
        """Full worker lifecycle — call this, not execute() directly."""
        await self.start()  # Sets status to RUNNING
        start_time = time.monotonic()
        
        try:
            result = await self.execute()
            result.duration_seconds = time.monotonic() - start_time
            
            await self.update_status(AgentStatus.COMPLETE)
            await self._publish_result(result)
            await emit_agent_complete(self.pipeline_id, self.agent_id, self.task.task_type, result.confidence)
            
            return result
        except Exception as e:
            logger.error(f"Worker {self.agent_id} ({self.task.task_type}) failed: {e}", exc_info=True)
            await self.update_status(AgentStatus.FAILED)
            await emit_agent_failed(self.pipeline_id, self.agent_id, self.task.task_type, str(e))
            
            failed_result = self._build_failed_result(str(e))
            failed_result.duration_seconds = time.monotonic() - start_time
            return failed_result

    async def request_context(self, keys: List[str]) -> Dict[str, Any]:
        """Fetch additional context from Redis shared state."""
        context = {}
        for key in keys:
            val = await get_state(key)
            context[key] = val
        return context

    async def _publish_result(self, result: AgentResult) -> None:
        """Publish result to coordinator queue for aggregation."""
        await enqueue("queue:coordinator", {
            "action": "worker_result",
            "pipeline_id": self.pipeline_id,
            "iteration": self.task.iteration,
            "result": {
                "task_id": result.task_id,
                "agent_type": result.agent_type,
                "status": result.status.value,
                "findings": result.findings,
                "confidence": result.confidence,
                "suggested_repairs": result.suggested_repairs,
                "error": result.error,
                "duration_seconds": result.duration_seconds
            }
        })

    def _build_failed_result(self, error: str) -> AgentResult:
        """Build a failed AgentResult for exception cases."""
        return AgentResult(
            task_id=self.task.task_id,
            agent_id=self.agent_id,
            agent_type=self.task.task_type,
            pipeline_id=self.pipeline_id,
            status=AgentStatus.FAILED,
            findings={},
            confidence=0.0,
            suggested_repairs=[],
            error=error,
            duration_seconds=0.0
        )
