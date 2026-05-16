import asyncio
import logging
from uuid import uuid4
from typing import Optional, Any, Dict
from base.agent import BaseAgent
from core.memory.retrieval import lookup_incident, store_incident, store_fix, update_outcome
from db.neo4j import create_pipeline_node, link_pipeline_to_incident
from db.redis import dequeue, publish, subscribe
from api.events import emit_memory_hit, emit_memory_miss

logger = logging.getLogger(__name__)

class MemoryAgent(BaseAgent):
    """
    Fixed agent. Consumes from queue:memory.
    Handles: incident lookup, storage, fix recording, outcome updates.
    All memory operations platform-wide go through this agent.
    """

    QUEUE_NAME = "queue:memory"

    async def execute(self) -> None:
        """Main event loop. Runs continuously until cancelled."""
        logger.info("MemoryAgent starting execution loop...")
        while True:
            try:
                payload = await dequeue(self.QUEUE_NAME, timeout=5)
                if payload is None:
                    continue

                action = payload.get("action")
                if action == "lookup":
                    await self.handle_lookup(payload)
                elif action == "store":
                    await self.handle_store(payload)
                elif action == "store_fix":
                    await self.handle_store_fix(payload)
                elif action == "update_outcome":
                    await self.handle_update_outcome(payload)
                else:
                    logger.warning(f"Unknown action in MemoryAgent: {action}")
            except asyncio.CancelledError:
                logger.info("MemoryAgent shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in MemoryAgent loop: {e}", exc_info=True)
                continue

    async def handle_lookup(self, payload: Dict[str, Any]) -> None:
        """
        payload: {
          "request_id": str,
          "pipeline_id": str,
          "error_signature": str,
          "root_cause": str | None
        }
        """
        request_id = payload["request_id"]
        pipeline_id = payload["pipeline_id"]
        error_signature = payload["error_signature"]
        root_cause = payload.get("root_cause")

        # 1. Call lookup_incident
        result = await lookup_incident(error_signature, root_cause)

        # 2. Emit WS event
        if result["hit"]:
            await emit_memory_hit(pipeline_id, result["best"]["incident_id"], result["confidence"], result["reuse"])
        else:
            await emit_memory_miss(pipeline_id, error_signature)

        # 3. Publish result to response channel
        await publish(f"memory:response:{request_id}", result)

    async def handle_store(self, payload: Dict[str, Any]) -> None:
        """
        payload: {
          "pipeline_id": str,
          "error_signature": str,
          "root_cause": str,
          "fix_applied": str,
          "confidence": float,
          "success": bool
        }
        """
        pipeline_id = payload["pipeline_id"]
        error_signature = payload["error_signature"]
        root_cause = payload["root_cause"]
        fix_applied = payload["fix_applied"]
        confidence = payload["confidence"]
        success = payload["success"]

        # 1. Store incident (Postgres + Neo4j nodes/edges)
        incident_id = await store_incident(
            error_signature=error_signature,
            root_cause=root_cause,
            fix_applied=fix_applied,
            confidence=confidence,
            success=success,
            pipeline_id=pipeline_id
        )

        # 2. Fetch repo and commit_sha (should be in payload or retrieved)
        # Assuming they are passed in or we use defaults if missing
        repo = payload.get("repo", "unknown/repo")
        commit_sha = payload.get("commit_sha", "unknown-sha")
        
        await create_pipeline_node(pipeline_id, repo, commit_sha)
        await link_pipeline_to_incident(pipeline_id, incident_id)

        logger.info(f"Incident {incident_id} stored for pipeline {pipeline_id}")

    async def handle_store_fix(self, payload: Dict[str, Any]) -> None:
        """
        payload: {
          "incident_id": str,
          "fix_description": str,
          "patch_type": str,
          "success": bool,
          "agent_id": str
        }
        """
        await store_fix(
            incident_id=payload["incident_id"],
            fix_description=payload["fix_description"],
            patch_type=payload["patch_type"],
            success=payload["success"],
            agent_id=payload["agent_id"]
        )

    async def handle_update_outcome(self, payload: Dict[str, Any]) -> None:
        """
        payload: {"incident_id": str, "success": bool}
        """
        await update_outcome(payload["incident_id"], payload["success"])

# --- Module-level helper for other agents to request a memory lookup ---

async def request_memory_lookup(pipeline_id: str, error_signature: str,
                                 root_cause: Optional[str],
                                 redis_client) -> Dict[str, Any]:
    """
    Other agents call this instead of touching the queue directly.
    """
    request_id = str(uuid4())
    response_channel = f"memory:response:{request_id}"
    
    response_future = asyncio.get_event_loop().create_future()

    async def handler(message: Dict[str, Any]) -> None:
        if not response_future.done():
            response_future.set_result(message)

    # 2. Subscribe before enqueuing to avoid race condition
    # Start subscription task
    sub_task = asyncio.create_task(subscribe(response_channel, handler))

    try:
        # 3. Enqueue lookup request
        from db.redis import enqueue
        await enqueue("queue:memory", {
            "action": "lookup",
            "request_id": request_id,
            "pipeline_id": pipeline_id,
            "error_signature": error_signature,
            "root_cause": root_cause
        })

        # 4. Wait for response
        try:
            result = await asyncio.wait_for(response_future, timeout=30.0)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Memory lookup timed out for request {request_id}")
            return {"hit": False, "source": "timeout"}
    finally:
        # 6. Cleanup: cancel subscription task
        sub_task.cancel()
        try:
            await sub_task
        except asyncio.CancelledError:
            pass

async def request_memory_store(pipeline_id: str, error_signature: str,
                                root_cause: str, fix_applied: str,
                                confidence: float, success: bool,
                                redis_client) -> None:
    """
    Fire-and-forget. Enqueue store action, do not wait for response.
    """
    from db.redis import enqueue
    await enqueue("queue:memory", {
        "action": "store",
        "pipeline_id": pipeline_id,
        "error_signature": error_signature,
        "root_cause": root_cause,
        "fix_applied": fix_applied,
        "confidence": confidence,
        "success": success
    })
