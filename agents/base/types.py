from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    spawned = "spawned"
    running = "running"
    complete = "complete"
    failed = "failed"


class AgentTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    pipeline_id: str
    agent_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    task_id: str
    agent_type: str
    status: Literal["complete", "failed"]
    findings: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    suggested_repairs: list[str] = Field(default_factory=list)
    error: str | None = None
