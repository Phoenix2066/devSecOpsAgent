import time
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional
from .types import AgentStatus
from db.redis import set_agent_status
from api.events import emit

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Abstract base for all fixed agents (Orchestrator, Coordinator, Memory, Monitor).
    Fixed agents run continuously in an event loop.
    """

    def __init__(self, agent_id: str, pipeline_id: Optional[str] = None):
        self.agent_id = agent_id
        self.pipeline_id = pipeline_id
        self.status = AgentStatus.SPAWNED
        self._started_at: Optional[float] = None

    @abstractmethod
    async def execute(self) -> None:
        """Fixed agents implement this as an infinite loop."""
        raise NotImplementedError

    async def start(self) -> None:
        """Lifecycle entry point. Call this to start the agent."""
        self.status = AgentStatus.RUNNING
        self._started_at = time.monotonic()
        await set_agent_status(self.agent_id, "running")
        logger.info(f"Agent {self.agent_id} ({self.__class__.__name__}) started")
        
        try:
            await self.execute()
        except asyncio.CancelledError:
            self.status = AgentStatus.COMPLETE
            raise
        except Exception as e:
            self.status = AgentStatus.FAILED
            logger.error(f"Agent {self.agent_id} encountered an error: {e}", exc_info=True)
            raise

    async def emit(self, event: str, data: dict,
                   pipeline_id: Optional[str] = None) -> None:
        """Convenience wrapper around events.emit()."""
        target_pipeline = pipeline_id or self.pipeline_id
        if target_pipeline:
            await emit(target_pipeline, event, data)

    async def update_status(self, status: AgentStatus) -> None:
        """Update self.status and Redis."""
        self.status = status
        await set_agent_status(self.agent_id, status.value)

    def elapsed(self) -> float:
        """Return seconds since _started_at. Return 0.0 if not started."""
        if self._started_at is None:
            return 0.0
        return time.monotonic() - self._started_at
