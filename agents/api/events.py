import logging
from datetime import datetime, timezone
from db.redis import publish

logger = logging.getLogger(__name__)

EVENTS: list[dict] = []  # Keep historical events for the /events endpoint

async def emit(pipeline_id: str, event: str, data: dict) -> None:
    """Build envelope and publish to Redis channel f'ws:pipeline:{pipeline_id}'."""
    envelope = {
        "event": event,
        "pipeline_id": pipeline_id,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "data": data
    }
    EVENTS.append(envelope)
    try:
        await publish(f"ws:pipeline:{pipeline_id}", envelope)
    except Exception as e:
        logger.error(f"Failed to emit WS event {event} for pipeline {pipeline_id}: {e}")

async def emit_agent_spawned(pipeline_id: str, agent_id: str, agent_type: str, spawned_by: str) -> None:
    data = {"agent_id": agent_id, "agent_type": agent_type, "spawned_by": spawned_by}
    await emit(pipeline_id, "agent_spawned", data)

async def emit_agent_complete(pipeline_id: str, agent_id: str, agent_type: str, confidence: float) -> None:
    data = {"agent_id": agent_id, "agent_type": agent_type, "confidence": confidence}
    await emit(pipeline_id, "agent_complete", data)

async def emit_agent_failed(pipeline_id: str, agent_id: str, agent_type: str, error: str) -> None:
    data = {"agent_id": agent_id, "agent_type": agent_type, "error": error}
    await emit(pipeline_id, "agent_failed", data)

async def emit_pipeline_failed(pipeline_id: str, commit_sha: str, error_signature: str, stage: str) -> None:
    data = {"commit_sha": commit_sha, "error_signature": error_signature, "stage": stage}
    await emit(pipeline_id, "pipeline_failed", data)

async def emit_memory_hit(pipeline_id: str, incident_id: str, similarity_score: float, reuse: bool) -> None:
    data = {"incident_id": incident_id, "similarity_score": similarity_score, "reuse": reuse}
    await emit(pipeline_id, "memory_hit", data)

async def emit_memory_miss(pipeline_id: str, error_signature: str) -> None:
    data = {"error_signature": error_signature}
    await emit(pipeline_id, "memory_miss", data)

async def emit_repair_started(pipeline_id: str, repair_targets: list[str], iteration: int) -> None:
    data = {"repair_targets": repair_targets, "iteration": iteration}
    await emit(pipeline_id, "repair_started", data)

async def emit_repair_iteration(pipeline_id: str, iteration: int, status: str, logs_summary: str, next_action: str) -> None:
    data = {"iteration": iteration, "status": status, "logs_summary": logs_summary, "next_action": next_action}
    await emit(pipeline_id, "repair_iteration", data)

async def emit_web_search_started(pipeline_id: str, error_signature: str) -> None:
    data = {"error_signature": error_signature}
    await emit(pipeline_id, "web_search_started", data)

async def emit_web_search_complete(pipeline_id: str, sources: list[str], confidence: float) -> None:
    data = {"sources": sources, "confidence": confidence}
    await emit(pipeline_id, "web_search_complete", data)

async def emit_validation_passed(pipeline_id: str, iteration: int, confidence: float) -> None:
    data = {"iteration": iteration, "confidence": confidence}
    await emit(pipeline_id, "validation_passed", data)

async def emit_validation_failed(pipeline_id: str, iteration: int, reason: str) -> None:
    data = {"iteration": iteration, "reason": reason}
    await emit(pipeline_id, "validation_failed", data)

async def emit_deployment_promoted(pipeline_id: str, pr_url: str, commit_sha: str, branch: str) -> None:
    data = {"pr_url": pr_url, "commit_sha": commit_sha, "branch": branch}
    await emit(pipeline_id, "deployment_promoted", data)

async def emit_rollback_triggered(pipeline_id: str, reason: str, iterations_attempted: int) -> None:
    data = {"reason": reason, "iterations_attempted": iterations_attempted}
    await emit(pipeline_id, "rollback_triggered", data)
