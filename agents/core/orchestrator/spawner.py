import asyncio
import importlib
import logging
from base.types import AgentTask
from db.postgres import create_agent_record, update_agent_status
from db.redis import add_active_agent, remove_active_agent
from api.events import emit_agent_spawned

logger = logging.getLogger(__name__)

WORKER_MAP = {
    "log_analyzer":           "workers.log_analyzer.LogAnalyzerWorker",
    "dependency_inspector":   "workers.dependency_inspector.DependencyInspectorWorker",
    "web_search":             "workers.web_search.WebSearchWorker",
    "config_analyzer":        "workers.config_analyzer.ConfigAnalyzerWorker",
    "code_analyzer":          "workers.code_analyzer.CodeAnalyzerWorker",
    "repair_docker":          "workers.repair_docker.RepairDockerWorker",
    "repair_yaml":            "workers.repair_yaml.RepairYamlWorker",
    "repair_imports":         "workers.repair_imports.RepairImportsWorker",
}

async def spawn_worker(worker_type: str, task: AgentTask,
                        db_pool, redis_client) -> str:
    """Spawn a dynamic worker agent as an asyncio task."""
    if worker_type not in WORKER_MAP:
        raise ValueError(f"Unknown worker type: {worker_type}")

    # 2. Import worker class dynamically
    module_path, class_name = WORKER_MAP[worker_type].rsplit(".", 1)
    module = importlib.import_module(module_path)
    worker_class = getattr(module, class_name)

    # 3. Create agent record in PostgreSQL
    agent_id = await create_agent_record(task.pipeline_id, worker_type)
    
    # 4. Update task metadata
    task.task_id = agent_id
    
    # 5. Add to Redis active agents
    await add_active_agent(task.pipeline_id, agent_id)
    
    # 6. Instantiate worker
    worker = worker_class(task)
    
    # 7. Launch as asyncio task (fire and forget)
    asyncio.create_task(worker.run())
    
    # 8. Emit agent_spawned WS event
    await emit_agent_spawned(
        task.pipeline_id, 
        agent_id, 
        worker_type, 
        task.parent_agent_id or "orchestrator"
    )
    
    return agent_id

async def spawn_workers_parallel(worker_types: list[str],
                                  base_task: AgentTask,
                                  db_pool, redis_client) -> list[str]:
    """Spawn multiple workers concurrently."""
    tasks = []
    for w_type in worker_types:
        # Create a copy of base_task for each worker
        from dataclasses import replace
        worker_task = replace(base_task)
        tasks.append(spawn_worker(w_type, worker_task, db_pool, redis_client))
        
    return await asyncio.gather(*tasks)

async def kill_worker(agent_id: str, pipeline_id: str,
                       redis_client, db_pool) -> None:
    """Forcefully terminate or mark a worker as failed."""
    # Note: Since workers are asyncio tasks, 'killing' usually means 
    # marking as failed in DB and removing from active set.
    await update_agent_status(agent_id, "failed")
    await remove_active_agent(pipeline_id, agent_id)
    logger.warning(f"Worker {agent_id} killed in pipeline {pipeline_id}")
