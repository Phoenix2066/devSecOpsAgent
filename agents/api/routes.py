from fastapi import APIRouter, HTTPException

from base.types import AgentTask
from core.memory.agent import MemoryAgent
from core.orchestrator.spawner import spawn_worker
from shadow.environment import ShadowEnvironment
from shadow.feedback import FeedbackLoop

from .events import EVENTS

router = APIRouter()
SHADOWS: dict[str, ShadowEnvironment] = {}


@router.post("/agent/spawn")
async def spawn_agent(task: AgentTask) -> dict:
    result = await spawn_worker(task.agent_type, task)
    return result.model_dump()


@router.post("/agent/kill/{agent_id}")
async def kill_agent(agent_id: str) -> dict:
    return {"agent_id": agent_id, "status": "kill_requested"}


@router.get("/agent/{agent_id}/status")
async def agent_status(agent_id: str) -> dict:
    return {"agent_id": agent_id, "status": "complete"}


@router.post("/memory/search")
async def memory_search(payload: dict) -> dict:
    task = AgentTask(pipeline_id=payload.get("pipeline_id", "memory"), agent_type="memory", payload=payload)
    result = await MemoryAgent(task).search_incidents(payload.get("error_signature", ""))
    return result


@router.post("/memory/store")
async def memory_store(payload: dict) -> dict:
    return await MemoryAgent.store_incident(payload)


@router.post("/shadow/create")
async def shadow_create(payload: dict) -> dict:
    pipeline_id = payload.get("pipeline_id")
    if not pipeline_id:
        raise HTTPException(status_code=400, detail="pipeline_id required")
    env = ShadowEnvironment(pipeline_id, None, None)
    await env.create(payload.get("repo_url", ""), payload.get("branch", "main"))
    SHADOWS[pipeline_id] = env
    return {"pipeline_id": pipeline_id, "container_id": env.container_id, "network_id": env.network_id}


@router.post("/shadow/run/{pipeline_id}")
async def shadow_run(pipeline_id: str) -> dict:
    env = SHADOWS.get(pipeline_id)
    if env is None:
        raise HTTPException(status_code=404, detail="shadow env not found")
    passed = await FeedbackLoop(pipeline_id, env, None, None).run()
    return {"pipeline_id": pipeline_id, "passed": passed}


@router.post("/shadow/destroy/{pipeline_id}")
async def shadow_destroy(pipeline_id: str) -> dict:
    env = SHADOWS.pop(pipeline_id, None)
    if env:
        await env.destroy()
    return {"pipeline_id": pipeline_id, "destroyed": True}


@router.get("/events")
async def events() -> list[dict]:
    return EVENTS
