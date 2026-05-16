import asyncio
import logging
import time
from typing import Dict, Any

from base.agent import BaseAgent
from base.types import AgentTask
from core.orchestrator.spawner import spawn_worker, spawn_workers_parallel
from core.orchestrator.graph import ExecutionGraph
from shadow.environment import ShadowEnvironment
from shadow.validator import ValidationRunner
from shadow.feedback import FeedbackLoop
from tools import github_tool
from db.postgres import update_pipeline_status
from db.redis import dequeue, enqueue, subscribe
from core.memory.agent import request_memory_store
from api.events import (
    emit_repair_started, 
    emit_deployment_promoted,
    emit_rollback_triggered
)

logger = logging.getLogger(__name__)

class OrchestratorAgent(BaseAgent):
    """
    Fixed agent. The central coordinator of the entire platform.
    Consumes from queue:orchestrator.
    Manages full pipeline lifecycle: trigger → investigate → repair → validate → promote/rollback.
    """

    QUEUE_NAME = "queue:orchestrator"
    MAX_CONCURRENT_PIPELINES = 10

    def __init__(self, agent_id: str, db_pool, redis_client):
        super().__init__(agent_id)
        self.db_pool = db_pool
        self.redis = redis_client
        self._active_pipelines: Dict[str, Dict[str, Any]] = {}

    async def execute(self) -> None:
        """Main event loop. Runs continuously until cancelled."""
        logger.info("OrchestratorAgent starting event loop...")
        while True:
            try:
                payload = await dequeue(self.QUEUE_NAME, timeout=5)
                if payload is None:
                    continue

                event_type = payload.get("event_type")
                if event_type == "pipeline_triggered":
                    await self.handle_pipeline_triggered(payload)
                elif event_type == "investigation_complete":
                    await self.handle_investigation_complete(payload)
                elif event_type == "repair_iteration_failed":
                    await self.handle_repair_iteration_failed(payload)
                else:
                    logger.warning(f"Unknown event_type in Orchestrator: {event_type}")
                    
            except asyncio.CancelledError:
                logger.info("OrchestratorAgent shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in Orchestrator loop: {e}", exc_info=True)

    async def handle_pipeline_triggered(self, payload: dict) -> None:
        """Entry point for a new pipeline failure repair cycle."""
        pid = payload["pipeline_id"]
        repo = payload["repo"]
        commit_sha = payload["commit_sha"]
        branch = payload["branch"]
        github_token = payload.get("github_token")

        logger.info(f"Orchestrator: Handling triggered pipeline {pid} for {repo}")
        
        # 1. Update status
        await update_pipeline_status(pid, "running")
        
        # 2. Create ExecutionGraph
        graph = ExecutionGraph(pid)
        graph.add_node(self.agent_id, "orchestrator")
        
        # 3. Store in active pipelines
        self._active_pipelines[pid] = {
            "graph": graph,
            "base_payload": {
                "repo": repo,
                "github_token": github_token,
                "branch": branch,
                "commit_sha": commit_sha,
                "iteration": 1
            }
        }
        
        # 4. Notify Coordinator
        await enqueue("queue:coordinator", {
            "action": "expect_workers",
            "pipeline_id": pid,
            "iteration": 1,
            "expected_count": 2,
            "base_payload": self._active_pipelines[pid]["base_payload"]
        })
        
        # 5. Spawn investigation workers
        base_task = AgentTask(
            task_id="", # Assigned by spawner
            pipeline_id=pid,
            task_type="", # Assigned by spawner
            payload=payload,
            iteration=1,
            parent_agent_id=self.agent_id
        )
        
        agent_ids = await spawn_workers_parallel(
            ["log_analyzer", "dependency_inspector"],
            base_task, self.db_pool, self.redis
        )
        
        # 6. Add nodes to graph
        for aid, wtype in zip(agent_ids, ["log_analyzer", "dependency_inspector"]):
            graph.add_node(aid, wtype, parent_id=self.agent_id)
            
        await graph.save(self.redis)
        
        # 7. Update status to healing
        await update_pipeline_status(pid, "healing")

    async def handle_investigation_complete(self, payload: dict) -> None:
        """Called by Coordinator when all investigation workers finish."""
        pid = payload["pipeline_id"]
        iteration = payload["iteration"]
        strategy = payload["repair_strategy"]
        repair_payloads = payload["repair_payloads"]
        
        if pid not in self._active_pipelines:
            logger.error(f"Received investigation for untracked pipeline: {pid}")
            return
            
        logger.info(f"Orchestrator: Investigation complete for {pid}. Strategy: {strategy}")
        
        # 1. Emit WS event
        await emit_repair_started(pid, strategy, iteration)
        
        # 2. Store results
        self._active_pipelines[pid]["memory_result"] = payload["memory_result"]
        self._active_pipelines[pid]["unified_findings"] = payload["unified_findings"]
        
        # 3. Spawn repair workers
        graph = self._active_pipelines[pid]["graph"]
        agent_ids = []
        for worker_type in strategy:
            task = AgentTask(
                task_id="",
                pipeline_id=pid,
                task_type=worker_type,
                payload=repair_payloads[worker_type],
                iteration=iteration,
                parent_agent_id=self.agent_id
            )
            aid = await spawn_worker(worker_type, task, self.db_pool, self.redis)
            agent_ids.append(aid)
            graph.add_node(aid, worker_type, parent_id=self.agent_id)
            
        await graph.save(self.redis)
        
        # 4. Wait for all repair workers to publish patches
        patches = await self._collect_repair_patches(pid, strategy, iteration)
        
        if not patches:
            logger.error(f"No patches generated for pipeline {pid}")
            # Simplified rollback for MVD
            await self.handle_rollback(pid, {"reason": "No patches generated"})
            return

        # 5. Commit and start feedback loop
        base = self._active_pipelines[pid]["base_payload"]
        try:
            # Note: In real flow we'd create a branch first. 
            # github_tool functions used as requested.
            commit_sha = await github_tool.commit_files(
                base["github_token"], base["repo"], base["branch"], 
                f"Anvil: Autonomous Repair (Iteration {iteration})", 
                patches
            )
            
            # Start FeedbackLoop in background
            asyncio.create_task(self._start_feedback_loop(pid, patches, payload))
            
        except Exception as e:
            logger.error(f"Failed to commit patches for {pid}: {e}")
            await self.handle_rollback(pid, {"reason": f"GitHub commit failed: {str(e)}"})

    async def _collect_repair_patches(self, pipeline_id: str,
                                       repair_strategy: list[str],
                                       iteration: int,
                                       timeout: int = 90) -> dict:
        """Subscribe to patches channel and aggregate results from repair workers."""
        channel = f"pipeline:{pipeline_id}:patches:raw"
        expected = len(repair_strategy)
        received = 0
        merged_patches = {}
        
        patch_queue = asyncio.Queue()

        async def handler(msg: dict) -> None:
            await patch_queue.put(msg)

        sub_task = asyncio.create_task(subscribe(channel, handler))
        
        start_time = time.monotonic()
        while received < expected:
            remaining = timeout - (time.monotonic() - start_time)
            if remaining <= 0:
                break
                
            try:
                msg = await asyncio.wait_for(patch_queue.get(), timeout=remaining)
                patches = msg.get("patches", {})
                merged_patches.update(patches)
                received += 1
            except asyncio.TimeoutError:
                break
                
        sub_task.cancel()
        return merged_patches

    async def _start_feedback_loop(self, pipeline_id: str,
                                    patches: dict,
                                    investigation_payload: dict) -> None:
        """Orchestrate the shadow validation loop."""
        base = self._active_pipelines[pipeline_id]["base_payload"]
        
        # 1. Get or create ShadowEnvironment
        if "shadow_env" not in self._active_pipelines[pipeline_id]:
            env = ShadowEnvironment(pipeline_id)
            await env.create(base["repo"], base["branch"], base["github_token"])
            self._active_pipelines[pipeline_id]["shadow_env"] = env
        
        shadow_env = self._active_pipelines[pipeline_id]["shadow_env"]
        
        # 2. Apply patches
        await shadow_env.apply_patches(patches)
        
        # 3. Setup validator and loop
        validator = ValidationRunner(pipeline_id)
        memory_confidence = investigation_payload["memory_result"].get("confidence", 0.0)
        
        loop = FeedbackLoop(
            pipeline_id, shadow_env, validator, self.redis, memory_confidence
        )
        self._active_pipelines[pipeline_id]["feedback_loop"] = loop
        
        # 4. Run loop
        outcome = await loop.run()
        
        # 5. Handle result
        if outcome["result"] == "promoted":
            await self.handle_promotion(pipeline_id, outcome)
        else:
            await self.handle_rollback(pipeline_id, outcome)

    async def handle_repair_iteration_failed(self, payload: dict) -> None:
        """FeedbackLoop signals that a build failed and needs a new investigation/repair cycle."""
        pid = payload["pipeline_id"]
        iteration = payload["iteration"]
        context = payload["context"]
        
        if pid not in self._active_pipelines:
            return
            
        logger.info(f"Orchestrator: Repair iteration {iteration} failed for {pid}. Re-investigating...")
        
        # 1. Update local payload with context
        base = self._active_pipelines[pid]["base_payload"]
        base["iteration"] = iteration + 1
        
        # 2. Re-notify Coordinator
        expected = 1 # Always log_analyzer
        if context.get("error_delta") != "resolved":
            expected += 1
            
        await enqueue("queue:coordinator", {
            "action": "expect_workers",
            "pipeline_id": pid,
            "iteration": iteration + 1,
            "expected_count": expected,
            "base_payload": base
        })
        
        # 3. Spawn workers
        graph = self._active_pipelines[pid]["graph"]
        
        log_payload = {**base, "container_id": self._active_pipelines[pid]["shadow_env"].container_id}
        log_task = AgentTask(
            task_id="", pipeline_id=pid, task_type="log_analyzer",
            payload=log_payload, iteration=iteration + 1, parent_agent_id=self.agent_id
        )
        log_aid = await spawn_worker("log_analyzer", log_task, self.db_pool, self.redis)
        graph.add_node(log_aid, "log_analyzer", parent_id=self.agent_id)
        
        if expected > 1:
            dep_task = AgentTask(
                task_id="", pipeline_id=pid, task_type="dependency_inspector",
                payload=base, iteration=iteration + 1, parent_agent_id=self.agent_id
            )
            dep_aid = await spawn_worker("dependency_inspector", dep_task, self.db_pool, self.redis)
            graph.add_node(dep_aid, "dependency_inspector", parent_id=self.agent_id)
            
        await graph.save(self.redis)

    async def handle_promotion(self, pipeline_id: str, outcome: dict) -> None:
        """Finalize the repair by opening a PR and updating memory."""
        pipe_state = self._active_pipelines.get(pipeline_id)
        if not pipe_state: return
        
        base = pipe_state["base_payload"]
        findings = pipe_state["unified_findings"]
        
        try:
            # 2. Open PR
            # In a real flow we'd use a unique branch name
            repair_branch = f"anvil-repair-{pipeline_id[:8]}"
            pr_url = await github_tool.open_pull_request(
                base["github_token"], base["repo"], 
                head=base["branch"], # Simplified: committed back to same branch for demo
                base=base["branch"], 
                title=f"[Auto-Heal] Fix for pipeline {pipeline_id}",
                body=self._build_pr_body(outcome)
            )
            
            # 3. Update status
            await update_pipeline_status(pipeline_id, "promoted")
            
            # 4. Emit event
            await emit_deployment_promoted(pipeline_id, pr_url, base["commit_sha"], base["branch"])
            
            # 5. Store in memory
            await request_memory_store(
                pipeline_id, 
                findings["error_signature"], 
                findings["stack_trace_summary"], 
                str(outcome["iteration_summaries"]), # fix_applied summary
                outcome["final_confidence"], 
                True, 
                self.redis
            )
            
        except Exception as e:
            logger.error(f"Promotion failed for {pipeline_id}: {e}")
            await update_pipeline_status(pipeline_id, "failed")
        finally:
            # 6. Destroy shadow
            if "shadow_env" in pipe_state:
                await pipe_state["shadow_env"].destroy()
            # 7. Cleanup
            self._active_pipelines.pop(pipeline_id, None)

    async def handle_rollback(self, pipeline_id: str, outcome: dict) -> None:
        """Cleanup after a failed repair attempt."""
        pipe_state = self._active_pipelines.get(pipeline_id)
        if not pipe_state: return
        
        findings = pipe_state.get("unified_findings", {"error_signature": "unknown", "stack_trace_summary": "unknown"})
        
        await update_pipeline_status(pipeline_id, "rolled_back")
        await emit_rollback_triggered(pipeline_id, "Max iterations reached or no fix found", outcome.get("total_iterations", 0))
        
        # 3. Store failure in memory
        await request_memory_store(
            pipeline_id, 
            findings["error_signature"], 
            findings["stack_trace_summary"], 
            "failed_repair", 
            0.0, 
            False, 
            self.redis
        )
        
        if "shadow_env" in pipe_state:
            await pipe_state["shadow_env"].destroy()
            
        self._active_pipelines.pop(pipeline_id, None)

    def _build_pr_body(self, outcome: dict) -> str:
        """Build PR description markdown."""
        summaries = ""
        for s in outcome.get("iteration_summaries", []):
            status = "✅ Passed" if s["passed"] else "❌ Failed"
            summaries += f"- **Iteration {s['iteration']}:** {s['action']} ({status})\n"
            
        return f"""## Auto-Heal Report
**Pipeline:** {outcome['pipeline_id']}
**Iterations:** {outcome['total_iterations']}
**Confidence:** {outcome['final_confidence']:.2%}

### Changes Made
{summaries}

This fix was automatically generated and verified by the Anvil Self-Healing Platform."""
