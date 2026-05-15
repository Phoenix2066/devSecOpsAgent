from abc import ABC, abstractmethod

from .types import AgentResult, AgentTask


class BaseAgent(ABC):
    def __init__(self, task: AgentTask):
        self.task = task

    @abstractmethod
    async def execute(self) -> AgentResult:
        raise NotImplementedError
