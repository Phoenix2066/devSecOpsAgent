from base.types import AgentResult, AgentTask
from workers.dependency_inspector import DependencyInspectorWorker
from workers.log_analyzer import LogAnalyzerWorker
from workers.repair_imports import RepairImportsWorker
from workers.repair_yaml import RepairYamlWorker
from workers.web_search import WebSearchWorker
from api.events import emit_event

WORKER_MAP = {
    "log_analyzer": LogAnalyzerWorker,
    "dependency_inspector": DependencyInspectorWorker,
    "web_search": WebSearchWorker,
    "repair_imports": RepairImportsWorker,
    "repair_yaml": RepairYamlWorker,
}


async def spawn_worker(worker_type: str, task: AgentTask) -> AgentResult:
    worker_cls = WORKER_MAP.get(worker_type)
    if worker_cls is None:
        return AgentResult(
            task_id=task.task_id,
            agent_type=worker_type,
            status="failed",
            error=f"unknown worker type: {worker_type}",
        )
    await emit_event("agent_spawned", task.pipeline_id, {"agent_id": task.task_id, "agent_type": worker_type, "spawned_by": "orchestrator"})
    result = await worker_cls(task).execute()
    await emit_event("agent_complete" if result.status == "complete" else "agent_failed", task.pipeline_id, result.model_dump())
    return result
