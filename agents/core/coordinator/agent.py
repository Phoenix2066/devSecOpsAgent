import asyncio
import logging
import time
from uuid import uuid4
from typing import Dict, Any, Optional
from base.agent import BaseAgent
from base.types import AgentTask, AgentStatus
from core.coordinator import aggregator
from core.memory.agent import request_memory_lookup
from workers.web_search import WebSearchWorker
from db import redis

logger = logging.getLogger(__name__)

class CoordinatorAgent(BaseAgent):
    """
    Fixed agent. Consumes from queue:coordinator.
    Aggregates investigation results, triggers memory lookup,
    decides repair strategy, signals Orchestrator.
    """

    QUEUE_NAME = "queue:coordinator"
    WORKER_WAIT_TIMEOUT = 60
    MEMORY_MISS_THRESHOLD = 0.50

    def __init__(self, agent_id: str, pipeline_id: Optional[str] = None):
        super().__init__(agent_id, pipeline_id)
        # {pipeline_id: {iteration: {"results": [], "expected": int, "received": int}}}
        self._pending: Dict[str, Dict[int, Dict[str, Any]]] = {}

    async def execute(self) -> None:
        """Main event loop."""
        logger.info("CoordinatorAgent starting event loop...")
        loop_count = 0
        
        while True:
            try:
                payload = await redis.dequeue(self.QUEUE_NAME, timeout=5)
                if payload:
                    action = payload.get("action")
                    if action == "worker_result":
                        await self.handle_worker_result(payload)
                    elif action == "expect_workers":
                        await self.handle_expect_workers(payload)
                    else:
                        logger.warning(f"Unknown action in Coordinator: {action}")
                
                # Periodic cleanup
                loop_count += 1
                if loop_count >= 20: # Check every ~100s if timeout is 5s
                    await self._cleanup_timed_out_pipelines()
                    loop_count = 0
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Coordinator loop: {e}", exc_info=True)

    async def handle_expect_workers(self, payload: Dict[str, Any]) -> None:
        """Initialize tracking for a set of workers."""
        pid = payload["pipeline_id"]
        iteration = payload["iteration"]
        
        if pid not in self._pending:
            self._pending[pid] = {}
            
        self._pending[pid][iteration] = {
            "results": [],
            "expected": payload["expected_count"],
            "received": 0,
            "base_payload": payload["base_payload"],
            "deadline": time.monotonic() + self.WORKER_WAIT_TIMEOUT
        }
        logger.info(f"Coordinator: Expecting {payload['expected_count']} workers for pipeline {pid} iter {iteration}")

    async def handle_worker_result(self, payload: Dict[str, Any]) -> None:
        """Process an incoming result from a worker."""
        pid = payload["pipeline_id"]
        iteration = payload["iteration"]
        result = payload["result"]

        if pid not in self._pending or iteration not in self._pending[pid]:
            logger.warning(f"Received result for unknown pipeline/iteration: {pid}/{iteration}")
            return

        entry = self._pending[pid][iteration]
        entry["results"].append(result)
        entry["received"] += 1
        
        received = entry["received"]
        expected = entry["expected"]
        over_deadline = time.monotonic() > entry["deadline"]
        
        if received >= expected or (over_deadline and received > 0):
            await self._process_complete_investigation(pid, iteration)

    async def _process_complete_investigation(self, pipeline_id: str, iteration: int) -> None:
        """Full aggregation + repair decision pipeline."""
        entry = self._pending[pipeline_id].pop(iteration)
        if not self._pending[pipeline_id]:
            self._pending.pop(pipeline_id)
            
        results = entry["results"]
        base_payload = entry["base_payload"]
        
        # 1. Aggregate
        unified = aggregator.aggregate_findings(results)
        
        # 2. Memory lookup
        memory_result = await request_memory_lookup(
            pipeline_id, 
            unified["error_signature"], 
            unified["stack_trace_summary"], 
            redis
        )
        
        # 3. Web search decision
        web_search_result = None
        if not memory_result.get("hit") or memory_result.get("confidence", 0) < self.MEMORY_MISS_THRESHOLD:
            web_search_result = await self._run_web_search(pipeline_id, unified, base_payload)
            
        # 4. Compute confidence
        confidence = aggregator.compute_confidence(results, memory_result, iteration)
        
        # 5. Decide strategy
        strategy = aggregator.decide_repair_strategy(unified, memory_result, web_search_result)
        
        # 6. Build repair payloads
        payloads = aggregator.build_repair_payloads(strategy, unified, memory_result, web_search_result, base_payload)
        
        # 7. Signal Orchestrator
        await redis.enqueue("queue:orchestrator", {
            "event_type": "investigation_complete",
            "pipeline_id": pipeline_id,
            "iteration": iteration,
            "unified_findings": unified,
            "repair_strategy": strategy,
            "repair_payloads": payloads,
            "memory_result": memory_result,
            "confidence": confidence
        })
        logger.info(f"Coordinator: Investigation complete for {pipeline_id}. Strategy: {strategy}")

    async def _run_web_search(self, pipeline_id: str, unified: dict, base_payload: dict) -> Optional[dict]:
        """Spawn WebSearchWorker inline."""
        task = AgentTask(
            task_id=str(uuid4()),
            pipeline_id=pipeline_id,
            task_type="web_search",
            payload={
                "error_signature": unified["error_signature"],
                "error_type": unified["error_type"],
                "package_manager": unified["package_manager"],
                "stack_trace_summary": unified["stack_trace_summary"],
                "pipeline_id": pipeline_id,
                **base_payload
            }
        )
        worker = WebSearchWorker(task)
        result = await worker.run()
        
        # Convert dataclass result to dict for aggregator
        if result.status == AgentStatus.COMPLETE:
            return {
                "status": "complete",
                "findings": result.findings,
                "confidence": result.confidence,
                "suggested_repairs": result.suggested_repairs
            }
        return None

    async def _cleanup_timed_out_pipelines(self) -> None:
        """Periodically check for exceeded deadlines."""
        now = time.monotonic()
        to_process = []
        to_delete = []
        
        for pid, iterations in self._pending.items():
            for iteration, entry in iterations.items():
                if now > entry["deadline"]:
                    if entry["received"] > 0:
                        to_process.append((pid, iteration))
                    else:
                        to_delete.append((pid, iteration))
                        
        for pid, iteration in to_process:
            logger.warning(f"Coordinator: Pipeline {pid} iter {iteration} timed out with partial results. Processing...")
            await self._process_complete_investigation(pid, iteration)
            
        for pid, iteration in to_delete:
            logger.warning(f"Coordinator: Pipeline {pid} iter {iteration} timed out with NO results. Cleaning up.")
            self._pending[pid].pop(iteration)
            if not self._pending[pid]:
                self._pending.pop(pid)
