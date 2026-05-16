import asyncio
import logging
import re
from dataclasses import dataclass
from typing import List, Optional
from .environment import ShadowEnvironment, BuildResult
from .validator import ValidationRunner, ValidationResult
from db.redis import subscribe
from api.events import (
    emit_repair_iteration,
    emit_validation_passed,
    emit_validation_failed,
    emit_rollback_triggered
)

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 5
MIN_ITERATIONS = 1    # always run at least one full iteration

@dataclass
class IterationSummary:
    iteration: int
    build_result: BuildResult
    validation_result: Optional[ValidationResult]
    action_taken: str    # "repair" | "promote" | "rollback" | "continue"
    context_sent: dict   # context passed to next repair cycle

class FeedbackLoop:
    """
    Drives iterative shadow build + repair cycles for one pipeline.
    Coordinates: ShadowEnvironment → ValidationRunner → Orchestrator signals.
    Terminates on: promotion, rollback, or MAX_ITERATIONS reached.
    """

    def __init__(self, pipeline_id: str, shadow_env: ShadowEnvironment,
                 validator: ValidationRunner, redis_client,
                 memory_confidence: float = 0.0):
        self.pipeline_id = pipeline_id
        self.shadow_env = shadow_env
        self.validator = validator
        self.redis = redis_client
        self.memory_confidence = memory_confidence
        self.iteration_summaries: List[IterationSummary] = []

    async def run(self) -> dict:
        """Main loop. Returns final outcome dict."""
        iteration = 0
        
        while iteration < MAX_ITERATIONS:
            iteration += 1
            logger.info(f"FeedbackLoop: Starting iteration {iteration} for pipeline {self.pipeline_id}")
            
            try:
                # 1. Run build in shadow env
                build_result = await self.shadow_env.run_build()
                
                status = "success" if build_result.passed else "failed"
                logs_summary = self._summarize_logs(build_result.logs)
                next_action = "validating" if build_result.passed else "repairing"
                
                # 2. Emit WS event
                await emit_repair_iteration(self.pipeline_id, iteration, status, logs_summary, next_action)
                
                validation_result = None
                
                # 3. If build passed (exit_code == 0):
                if build_result.passed:
                    validation_result = await self.validator.run(build_result, iteration, self.memory_confidence)
                    
                    if validation_result.passed:
                        await emit_validation_passed(self.pipeline_id, iteration, validation_result.confidence)
                        
                        summary = IterationSummary(
                            iteration=iteration,
                            build_result=build_result,
                            validation_result=validation_result,
                            action_taken="promote",
                            context_sent={}
                        )
                        self.iteration_summaries.append(summary)
                        return await self._build_outcome("promoted", build_result, validation_result)
                    else:
                        await emit_validation_failed(self.pipeline_id, iteration, validation_result.reason or "Validation failed")
                
                # 4. If build failed or validation failed:
                if iteration >= MAX_ITERATIONS:
                    reason = validation_result.reason if validation_result else "Max iterations reached"
                    await emit_rollback_triggered(self.pipeline_id, reason, iteration)
                    
                    summary = IterationSummary(
                        iteration=iteration,
                        build_result=build_result,
                        validation_result=validation_result,
                        action_taken="rollback",
                        context_sent={}
                    )
                    self.iteration_summaries.append(summary)
                    return await self._build_outcome("rollback", build_result, validation_result)
                else:
                    context = await self.shadow_env.get_context_for_next_iteration()
                    
                    summary = IterationSummary(
                        iteration=iteration,
                        build_result=build_result,
                        validation_result=validation_result,
                        action_taken="repair",
                        context_sent=context
                    )
                    self.iteration_summaries.append(summary)
                    
                    # publish to "queue:orchestrator" requesting next repair cycle:
                    from db.redis import enqueue
                    await enqueue("queue:orchestrator", {
                        "event_type": "repair_iteration_failed",
                        "pipeline_id": self.pipeline_id,
                        "iteration": iteration,
                        "context": context
                    })
                    
                    # Wait for next repair patches
                    patches = await self._wait_for_patches(iteration)
                    
                    if patches:
                        await self.shadow_env.apply_patches(patches)
                        await self.shadow_env.reset_for_iteration()
                    else:
                        # If no patches received, we can't continue repairing
                        logger.warning(f"No patches received for iteration {iteration+1}. Terminating loop.")
                        await emit_rollback_triggered(self.pipeline_id, "Repair timed out (no patches received)", iteration)
                        return await self._build_outcome("rollback", build_result, validation_result)

            except Exception as e:
                logger.error(f"Error in FeedbackLoop iteration {iteration}: {e}", exc_info=True)
                # Treat as a failed iteration
                if iteration >= MAX_ITERATIONS:
                    return await self._build_outcome("rollback", BuildResult(
                        container_id="unknown", exit_code=1, logs=str(e), error_signature="loop_error",
                        duration_seconds=0, passed=False, test_failures=[], iteration=iteration
                    ), None)
                # Continue loop if possible
                continue

        # Should not reach here if loop logic is correct
        return await self._build_outcome("rollback", build_result, None)

    async def _wait_for_patches(self, iteration: int,
                                 timeout: int = 120) -> Optional[dict]:
        """Wait for repair agents to produce patches for next iteration."""
        channel = f"pipeline:{self.pipeline_id}:patches:{iteration+1}"
        logger.info(f"FeedbackLoop: Waiting for patches on {channel} (timeout={timeout}s)")
        
        patch_future = asyncio.get_event_loop().create_future()
        
        async def handler(message: dict) -> None:
            if not patch_future.done():
                patch_future.set_result(message)
                
        # Subscribe
        sub_task = asyncio.create_task(subscribe(channel, handler))
        
        try:
            patches = await asyncio.wait_for(patch_future, timeout=float(timeout))
            return patches
        except asyncio.TimeoutError:
            logger.warning(f"FeedbackLoop: Timed out waiting for patches for iteration {iteration+1}")
            return None
        finally:
            sub_task.cancel()
            try:
                await sub_task
            except asyncio.CancelledError:
                pass

    async def _build_outcome(self, result: str,
                              build_result: BuildResult,
                              validation_result: Optional[ValidationResult]) -> dict:
        """Build final outcome dict returned by run()."""
        return {
            "result": result,            # "promoted" | "rollback"
            "pipeline_id": self.pipeline_id,
            "total_iterations": self.shadow_env.iteration,
            "final_exit_code": build_result.exit_code,
            "final_error_signature": build_result.error_signature,
            "final_confidence": validation_result.confidence if (result == "promoted" and validation_result) else 0.0,
            "iteration_summaries": [
                {
                    "iteration": s.iteration, 
                    "action": s.action_taken,
                    "passed": s.build_result.passed
                }
                for s in self.iteration_summaries
            ],
            "pr_url": None    # populated by OrchestratorAgent after promotion
        }

    def _summarize_logs(self, logs: str) -> str:
        """Extract last 500 chars of logs and strip ANSI codes."""
        tail = logs[-500:] if len(logs) > 500 else logs
        return self._strip_ansi(tail)

    def _strip_ansi(self, text: str) -> str:
        """Remove ANSI escape sequences using regex."""
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    async def get_full_summary(self) -> dict:
        """Return complete summary of all iterations."""
        return {
            "pipeline_id": self.pipeline_id,
            "total_iterations": self.shadow_env.iteration,
            "iterations": [
                {
                    "iteration": s.iteration,
                    "build_passed": s.build_result.passed,
                    "error_signature": s.build_result.error_signature,
                    "action": s.action_taken,
                    "duration": s.build_result.duration_seconds
                }
                for s in self.iteration_summaries
            ],
            "repair_history": [r.__dict__ for r in self.shadow_env.build_history]
        }
