from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

class AgentStatus(Enum):
    SPAWNED = "spawned"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"

class AgentType(Enum):
    # Fixed agents
    ORCHESTRATOR = "orchestrator"
    COORDINATOR = "coordinator"
    MEMORY = "memory"
    MONITOR = "monitor"
    # Dynamic workers
    LOG_ANALYZER = "log_analyzer"
    DEPENDENCY_INSPECTOR = "dependency_inspector"
    WEB_SEARCH = "web_search"
    CONFIG_ANALYZER = "config_analyzer"
    CODE_ANALYZER = "code_analyzer"
    REPAIR_DOCKER = "repair_docker"
    REPAIR_YAML = "repair_yaml"
    REPAIR_IMPORTS = "repair_imports"

@dataclass
class AgentTask:
    task_id: str
    pipeline_id: str
    task_type: str           # matches AgentType.value
    payload: dict
    iteration: int = 1
    parent_agent_id: Optional[str] = None

@dataclass
class AgentResult:
    task_id: str
    agent_id: str
    agent_type: str
    pipeline_id: str
    status: AgentStatus
    findings: dict
    confidence: float        # 0.0–1.0
    suggested_repairs: List[str]
    error: Optional[str] = None
    duration_seconds: float = 0.0
