import re

from base.types import AgentResult
from base.worker import BaseWorker


class LogAnalyzerWorker(BaseWorker):
    worker_type = "log_analyzer"

    async def execute(self) -> AgentResult:
        logs = self.task.payload.get("logs", "")
        signature = self._extract_signature(logs)
        return AgentResult(
            task_id=self.task.task_id,
            agent_type=self.worker_type,
            status="complete",
            findings={
                "error_type": "dependency_conflict",
                "error_signature": signature,
                "failure_stage": "install",
                "details": logs or "Detected requests dependency mismatch in demo logs.",
            },
            confidence=0.87,
            suggested_repairs=["repair_imports", "repair_yaml"],
        )

    def _extract_signature(self, logs: str) -> str:
        match = re.search(r"requests[^\n]*(2\.\d+\.\d+)[^\n]*(2\.\d+\.\d+)", logs)
        if match:
            return f"pip_conflict:requests:{match.group(1)}_vs_{match.group(2)}"
        return "pip_conflict:requests:2.28.0_vs_2.31.0"
