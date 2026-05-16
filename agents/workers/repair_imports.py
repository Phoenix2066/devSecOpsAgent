import json
import re
import logging
from base.worker import BaseWorker
from base.types import AgentResult, AgentStatus
from tools.github_tool import get_file
from tools.code_tool import analyze_dependencies
from llm.router import ModelRouter

logger = logging.getLogger(__name__)
router = ModelRouter()

class RepairImportsWorker(BaseWorker):
    """
    Dynamic worker. Fixes dependency version conflicts and missing packages.
    Modifies requirements.txt, package.json, or go.mod.
    Spawned when Coordinator identifies dependency_conflict or import_error.
    """

    async def execute(self) -> AgentResult:
        # task.payload expected keys:
        # {
        #   "repo": str,
        #   "github_token": str,
        #   "branch": str,
        #   "package_manager": str,
        #   "conflicts": list[dict],
        #   "missing": list[dict],
        #   "fix_suggestions": list[dict],
        #   "web_search_fix": str | None,
        #   "file_contents": dict[str, str],
        #   "iteration": int
        # }

        repo = self.task.payload.get("repo")
        token = self.task.payload.get("github_token")
        branch = self.task.payload.get("branch", "main")
        pm = self.task.payload.get("package_manager", "pip")
        file_contents = self.task.payload.get("file_contents", {})

        # 1. Determine target files
        pm_map = {
            "pip": "requirements.txt",
            "npm": "package.json",
            "go": "go.mod"
        }
        target_file = pm_map.get(pm, "requirements.txt")

        # 2. Get current content
        current_content = file_contents.get(target_file)
        if not current_content:
            try:
                current_content = await get_file(token, repo, target_file, ref=branch)
            except Exception as e:
                logger.error(f"Failed to fetch {target_file}: {e}")
                return self._build_failed_result(f"Could not fetch {target_file}")

        # 3. Generate patched content via LLM
        messages = self._build_repair_prompt(current_content, self.task.payload)
        try:
            response = await router.complete("repair_generation", messages, response_format="json")
            parsed = self._parse_repair_response(response)
            
            # 4. Validate patched content
            analysis = await analyze_dependencies(target_file, parsed["patched_content"])
            if any(issue["type"] == "syntax_error" for issue in analysis.get("issues", [])):
                logger.warning(f"Syntax error in LLM output for {target_file}, retrying...")
                # Retry once
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": f"The previous output had syntax errors: {json.dumps(analysis['issues'])}. Please fix and return valid JSON."})
                response = await router.complete("repair_generation", messages, response_format="json")
                parsed = self._parse_repair_response(response)

            if not parsed["patched_content"]:
                logger.warning(f"No patched content generated for {target_file}")
                parsed["confidence"] = 0.1

            return AgentResult(
                task_id=self.task.task_id,
                agent_id=self.agent_id,
                agent_type=self.task.task_type,
                pipeline_id=self.pipeline_id,
                status=AgentStatus.COMPLETE,
                findings={
                    "patches": {target_file: parsed["patched_content"]} if parsed["patched_content"] else {},
                    "changes_made": parsed["changes_made"],
                    "explanation": parsed["explanation"],
                    "patch_type": "dependency_fix"
                },
                confidence=parsed["confidence"],
                suggested_repairs=[]
            )
        except Exception as e:
            logger.error(f"RepairImports LLM failure: {e}")
            return self._build_failed_result(str(e))

    def _build_repair_prompt(self, current_content: str, payload: dict) -> list[dict]:
        system = "You are a dependency repair expert. Generate a fixed dependency file. Always respond with valid JSON only. No markdown, no explanation."
        user = f"""Fix the dependency file to resolve all conflicts and missing packages.

Package manager: {payload.get("package_manager", "pip")}
Iteration: {payload.get("iteration", 1)} (previous attempts failed if > 1)

Current file content:
{current_content}

Conflicts to resolve:
{json.dumps(payload.get("conflicts", []), indent=2)}

Missing packages to add:
{json.dumps(payload.get("missing", []), indent=2)}

Suggested fixes from static analysis:
{json.dumps(payload.get("fix_suggestions", []), indent=2)}

Web search guidance: {payload.get("web_search_fix") or "None available"}

Respond with exactly this JSON:
{{
  "patched_content": "complete corrected file content as string",
  "changes_made": ["list", "of", "specific", "changes"],
  "explanation": "Why these changes fix the conflicts",
  "confidence": 0.0
}}

Rules:
- patched_content must be the COMPLETE file, not a diff
- preserve all packages not involved in conflicts
- pin all versions explicitly — no open ranges
- confidence 0.0-1.0"""
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _parse_repair_response(self, response: str) -> dict:
        safe_default = {
            "patched_content": "",
            "changes_made": [],
            "explanation": "Parse failed",
            "confidence": 0.1
        }
        if not response:
            return safe_default
        try:
            clean = re.sub(r'```json|```', '', response).strip()
            return json.loads(clean)
        except json.JSONDecodeError:
            return safe_default
