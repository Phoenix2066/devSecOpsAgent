import json
import re
import logging
from base.worker import BaseWorker
from base.types import AgentResult, AgentStatus
from tools.github_tool import get_file
from tools.code_tool import validate_dockerfile
from llm.router import ModelRouter

logger = logging.getLogger(__name__)
router = ModelRouter()

class RepairDockerWorker(BaseWorker):
    """
    Dynamic worker. Fixes Dockerfile issues: wrong base image,
    missing system dependencies, bad CMD/ENTRYPOINT, build failures.
    Spawned when Coordinator identifies docker_error.
    """

    DOCKERFILE_CANDIDATES = [
        "Dockerfile",
        "docker/Dockerfile",
        "Dockerfile.prod",
        "Dockerfile.dev",
    ]

    async def execute(self) -> AgentResult:
        # task.payload expected keys:
        # {
        #   "repo": str,
        #   "github_token": str,
        #   "branch": str,
        #   "error_signature": str,
        #   "error_type": str,
        #   "stack_trace_summary": str,
        #   "affected_files": list[str],
        #   "web_search_fix": str | None,
        #   "iteration": int
        # }

        repo = self.task.payload.get("repo")
        token = self.task.payload.get("github_token")
        branch = self.task.payload.get("branch", "main")
        affected = self.task.payload.get("affected_files", [])

        # 1. Find Dockerfile
        target_path = None
        for path in affected:
            if "Dockerfile" in path:
                target_path = path
                break
        
        if not target_path:
            for path in self.DOCKERFILE_CANDIDATES:
                try:
                    await get_file(token, repo, path, ref=branch)
                    target_path = path
                    break
                except:
                    continue
        
        if not target_path:
            return self._build_failed_result("No Dockerfile found to repair")

        try:
            content = await get_file(token, repo, target_path, ref=branch)
        except Exception as e:
            logger.error(f"Failed to fetch {target_path}: {e}")
            return self._build_failed_result(f"Could not fetch {target_path}")

        # 2. Validate current Dockerfile
        validation = await validate_dockerfile(content)

        # 3. Generate patched Dockerfile via LLM
        messages = self._build_repair_prompt(content, validation, self.task.payload)
        try:
            response = await router.complete("repair_generation", messages, response_format="json")
            parsed = self._parse_repair_response(response)
            
            # 4. Validate patched Dockerfile
            new_validation = await validate_dockerfile(parsed["patched_content"])
            if not new_validation["valid"] and any(i["rule"] == "missing_from" for i in new_validation["issues"]):
                logger.warning(f"LLM generated invalid Dockerfile for {target_path}, retrying...")
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": f"The previous output was invalid: {json.dumps(new_validation['issues'])}. Please fix."})
                response = await router.complete("repair_generation", messages, response_format="json")
                parsed = self._parse_repair_response(response)

            if not parsed["patched_content"]:
                logger.warning(f"No patched Dockerfile content generated for {target_path}")
                parsed["confidence"] = 0.1

            return AgentResult(
                task_id=self.task.task_id,
                agent_id=self.agent_id,
                agent_type=self.task.task_type,
                pipeline_id=self.pipeline_id,
                status=AgentStatus.COMPLETE,
                findings={
                    "patches": {target_path: parsed["patched_content"]} if parsed["patched_content"] else {},
                    "changes_made": parsed["changes_made"],
                    "explanation": parsed["explanation"],
                    "original_issues": validation["issues"],
                    "patch_type": "dockerfile_fix"
                },
                confidence=parsed["confidence"],
                suggested_repairs=[]
            )
        except Exception as e:
            logger.error(f"RepairDocker LLM failure: {e}")
            return self._build_failed_result(str(e))

    def _build_repair_prompt(self, current_content: str,
                              validation: dict,
                              payload: dict) -> list[dict]:
        system = "You are a Docker and containerization expert. Fix Dockerfiles to resolve build failures. Always respond with valid JSON only. No markdown, no explanation."
        user = f"""Fix this Dockerfile to resolve the build failure.

Error signature: {payload.get("error_signature")}
Error type: {payload.get("error_type")}
Iteration: {payload.get("iteration", 1)}

Current validation issues:
{json.dumps(validation.get("issues", []), indent=2)}

Stack trace context:
{payload.get("stack_trace_summary", "None")}

Web search guidance: {payload.get("web_search_fix") or "None available"}

Current Dockerfile:
{current_content}

Respond with exactly this JSON:
{{
  "patched_content": "complete corrected Dockerfile as string",
  "changes_made": ["list", "of", "changes"],
  "explanation": "Why these changes fix the failure",
  "confidence": 0.0
}}

Rules:
- patched_content must be a complete valid Dockerfile
- always include FROM, RUN, CMD or ENTRYPOINT
- use specific image tags, never :latest
- confidence 0.0-1.0"""
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _parse_repair_response(self, response: str) -> dict:
        safe_default = {"patched_content": "", "changes_made": [], "explanation": "Parse failed", "confidence": 0.1}
        if not response:
            return safe_default
        try:
            clean = re.sub(r'```json|```', '', response).strip()
            return json.loads(clean)
        except json.JSONDecodeError:
            return safe_default
