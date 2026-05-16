import json
import re
import logging
from base.worker import BaseWorker
from base.types import AgentResult, AgentStatus
from tools.github_tool import get_actions_logs
from tools.docker_tool import get_logs
from tools.code_tool import extract_error_signature
from llm.router import ModelRouter

logger = logging.getLogger(__name__)
router = ModelRouter()

class LogAnalyzerWorker(BaseWorker):
    """
    Dynamic worker. Spawned once per pipeline failure and once per
    failed repair iteration. Analyzes GitHub Actions logs and shadow
    container logs to extract structured error information.
    """

    async def execute(self) -> AgentResult:
        # task.payload expected keys:
        # {
        #   "repo": str,
        #   "github_token": str,
        #   "run_id": str | None,        # GitHub Actions run ID — None if shadow run
        #   "container_id": str | None,  # Docker container ID — None if Actions run
        #   "iteration": int
        # }

        repo = self.task.payload.get("repo")
        token = self.task.payload.get("github_token")
        run_id = self.task.payload.get("run_id")
        container_id = self.task.payload.get("container_id")

        raw_logs_github = ""
        raw_logs_docker = ""

        # 1. Fetch logs
        if run_id and token and repo:
            try:
                raw_logs_github = await get_actions_logs(token, repo, run_id)
            except Exception as e:
                logger.error(f"Failed to fetch GitHub logs: {e}")

        if container_id:
            try:
                raw_logs_docker = await get_logs(container_id, tail=500)
            except Exception as e:
                logger.error(f"Failed to fetch Docker logs: {e}")

        if not raw_logs_github and not raw_logs_docker:
            return self._build_failed_result("No log source provided or logs could not be fetched")

        if raw_logs_github and raw_logs_docker:
            raw_logs = f"{raw_logs_github}\n---\n{raw_logs_docker}"
        else:
            raw_logs = raw_logs_github or raw_logs_docker

        # 2. Extract error signature
        error_signature = await extract_error_signature(raw_logs)

        # 3. Call LLM for structured extraction
        messages = self._build_extraction_prompt(raw_logs, error_signature)
        try:
            response = await router.complete("log_extraction", messages, response_format="json")
            parsed = self._parse_llm_response(response)
            parsed = self._validate_parsed(parsed)
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            parsed = self._parse_llm_response("") # Get safe defaults

        # 5. Return AgentResult
        findings = {
            "error_type": parsed["error_type"],
            "error_signature": error_signature,
            "failure_stage": parsed["failure_stage"],
            "stack_trace_summary": parsed["stack_trace_summary"],
            "affected_files": parsed["affected_files"],
            "raw_logs_tail": raw_logs[-2000:]
        }
        
        return AgentResult(
            task_id=self.task.task_id,
            agent_id=self.agent_id,
            agent_type=self.task.task_type,
            pipeline_id=self.pipeline_id,
            status=AgentStatus.COMPLETE,
            findings=findings,
            confidence=parsed["confidence"],
            suggested_repairs=parsed["suggested_repairs"]
        )

    def _build_extraction_prompt(self, raw_logs: str, error_signature: str) -> list[dict]:
        system = "You are a DevOps log analysis expert. Extract structured error information from build logs. Always respond with valid JSON only. No explanation, no markdown, no code blocks."
        
        user = f"""Analyze these build logs and extract error information.

Pre-extracted error signature: {error_signature}

Build logs:
{raw_logs[-4000:]}

Respond with exactly this JSON structure:
{{
  "error_type": "import_error|dependency_conflict|yaml_syntax|docker_error|test_failure|unknown",
  "failure_stage": "install|build|test|deploy|unknown",
  "stack_trace_summary": "2-3 sentence summary of what failed and where",
  "affected_files": ["list", "of", "files", "mentioned", "in", "logs"],
  "suggested_repairs": ["repair_imports", "repair_yaml", "repair_docker"],
  "confidence": 0.0
}}

Rules:
- error_type must be exactly one of the enum values
- suggested_repairs must only contain: repair_imports, repair_yaml, repair_docker
- confidence is float 0.0-1.0 representing how certain you are of the diagnosis
- affected_files should be empty list if no specific files identified"""

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]

    def _parse_llm_response(self, response: str) -> dict:
        safe_default = {
            "error_type": "unknown",
            "failure_stage": "unknown",
            "stack_trace_summary": "Failed to parse LLM response",
            "affected_files": [],
            "suggested_repairs": [],
            "confidence": 0.1
        }
        
        if not response:
            return safe_default

        try:
            # Strip any accidental markdown fences
            clean_response = re.sub(r'```json|```', '', response).strip()
            return json.loads(clean_response)
        except json.JSONDecodeError:
            return safe_default

    def _validate_parsed(self, parsed: dict) -> dict:
        allowed_repairs = {"repair_imports", "repair_yaml", "repair_docker"}
        allowed_types = {"import_error", "dependency_conflict", "yaml_syntax", "docker_error", "test_failure", "unknown"}
        allowed_stages = {"install", "build", "test", "deploy", "unknown"}

        # Ensure required keys exist with safe defaults
        if "error_type" not in parsed or parsed["error_type"] not in allowed_types:
            parsed["error_type"] = "unknown"
            
        if "failure_stage" not in parsed or parsed["failure_stage"] not in allowed_stages:
            parsed["failure_stage"] = "unknown"
            
        if "stack_trace_summary" not in parsed:
            parsed["stack_trace_summary"] = "No summary provided"
            
        if "affected_files" not in parsed or not isinstance(parsed["affected_files"], list):
            parsed["affected_files"] = []
            
        if "suggested_repairs" not in parsed or not isinstance(parsed["suggested_repairs"], list):
            parsed["suggested_repairs"] = []
        else:
            parsed["suggested_repairs"] = [r for r in parsed["suggested_repairs"] if r in allowed_repairs]
            
        if "confidence" not in parsed or not isinstance(parsed["confidence"], (int, float)):
            parsed["confidence"] = 0.5
        else:
            parsed["confidence"] = max(0.0, min(1.0, float(parsed["confidence"])))
            
        return parsed
