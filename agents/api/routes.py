from fastapi import APIRouter, HTTPException, Request
from typing import Optional, Dict, Any
from pydantic import BaseModel

from base.types import AgentTask
from core.orchestrator.spawner import spawn_worker
from core.memory.retrieval import lookup_incident, store_incident
from shadow.environment import ShadowEnvironment
from db import redis, postgres

router = APIRouter()

class SpawnRequest(BaseModel):
    worker_type: str
    pipeline_id: str
    payload: Dict[str, Any]
    iteration: int = 1

class MemorySearchRequest(BaseModel):
    error_signature: str
    root_cause: Optional[str] = None

class MemoryStoreRequest(BaseModel):
    pipeline_id: str
    error_signature: str
    root_cause: str
    fix_applied: str
    confidence: float
    success: bool

class ShadowCreateRequest(BaseModel):
    pipeline_id: str
    repo_url: str
    branch: str
    github_token: str

@router.post("/agent/spawn")
async def agent_spawn(req: SpawnRequest):
    pool = await postgres.get_pool()
    redis_client = await redis.get_client()
    
    task = AgentTask(
        task_id="", # Assigned by spawner
        pipeline_id=req.pipeline_id,
        task_type=req.worker_type,
        payload=req.payload,
        iteration=req.iteration
    )
    
    agent_id = await spawn_worker(req.worker_type, task, pool, redis_client)
    return {"agent_id": agent_id}

@router.get("/agent/{agent_id}/status")
async def agent_status(agent_id: str):
    status = await redis.get_agent_status(agent_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent_id": agent_id, "status": status}

@router.post("/memory/search")
async def memory_search(req: MemorySearchRequest):
    result = await lookup_incident(req.error_signature, req.root_cause)
    return result

@router.post("/memory/store")
async def memory_store(req: MemoryStoreRequest):
    incident_id = await store_incident(
        req.error_signature,
        req.root_cause,
        req.fix_applied,
        req.confidence,
        req.success,
        req.pipeline_id
    )
    return {"incident_id": incident_id}

@router.post("/shadow/create")
async def shadow_create(req: ShadowCreateRequest, request: Request):
    env = ShadowEnvironment(req.pipeline_id)
    await env.create(req.repo_url, req.branch, req.github_token)
    
    # Store in app state
    if not hasattr(request.app.state, "shadows"):
        request.app.state.shadows = {}
    request.app.state.shadows[req.pipeline_id] = env
    
    return {"pipeline_id": req.pipeline_id, "status": "created"}

@router.post("/shadow/run/{pipeline_id}")
async def shadow_run(pipeline_id: str, request: Request):
    shadows = getattr(request.app.state, "shadows", {})
    env = shadows.get(pipeline_id)
    if not env:
        raise HTTPException(status_code=404, detail="Shadow environment not found")
    
    result = await env.run_build()
    return result.__dict__

@router.post("/shadow/destroy/{pipeline_id}")
async def shadow_destroy(pipeline_id: str, request: Request):
    shadows = getattr(request.app.state, "shadows", {})
    env = shadows.pop(pipeline_id, None)
    if env:
        await env.destroy()
        return {"status": "destroyed"}
    raise HTTPException(status_code=404, detail="Shadow environment not found")

@router.get("/health")
async def health(request: Request):
    agents = []
    if hasattr(request.app.state, "agent_tasks"):
        for task in request.app.state.agent_tasks:
            agents.append(task.get_name())
            
    return {
        "status": "ok",
        "agents": agents
    }

@router.get("/agents/active")
async def agents_active():
    # This is a bit complex as we need to scan all pipelines
    # For now, return a placeholder or implement if redis helper exists
    # Plan says: returns {agents: [{name, status, uptime}]}
    return {"agents": []}
