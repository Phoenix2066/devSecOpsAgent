import json
import re
import logging
from base.worker import BaseWorker
from base.types import AgentResult, AgentStatus
from tools.github_tool import get_file
from tools.code_tool import validate_yaml
from llm.router import ModelRouter

logger = logging.getLogger(__name__)
router = ModelRouter()

class RepairYamlWorker(BaseWorker):
    """
    Dynamic worker. Fixes YAML files: GitHub Actions workflows,
    docker-compose.yml, and any other YAML in the repo.
    Spawned when Coordinator identifies yaml_syntax errors or
    CI pipeline configuration failures.
    """

    YAML_FILE_CANDIDATES = [
        ".github/workflows/ci.yml",
        ".github/workflows/main.yml",
        ".github/workflows/build.yml",
        "docker-compose.yml",
        "docker-compose.yaml",
        ".github/workflows/deploy.yml",
    ]

    async def execute(self) -> AgentResult:
        # task.payload expected keys:
        # {
        #   "repo": str,
        #   "github_token": str,
        #   "branch": str,
        #   "error_type": str,
        #   "error_signature": str,
        #   "affected_files": list[str],
        #   "stack_trace_summary": str,
        #   "web_search_fix": str | None,
        #   "iteration": int
        # }

        repo = self.task.payload.get("repo")
        token = self.task.payload.get("github_token")
        branch = self.task.payload.get("branch", "main")
        affected = self.task.payload.get("affected_files", [])

        # 1. Determine target YAML files
        target_paths = [f for f in affected if f.endswith(".yml") or f.endswith(".yaml")]
        if not target_paths:
            # Try candidates
            target_paths = []
            for path in self.YAML_FILE_CANDIDATES:
                try:
                    await get_file(token, repo, path, ref=branch)
                    target_paths.append(path)
                except:
                    continue

        if not target_paths:
            return self._build_failed_result("No YAML files found to repair")

        target_files = {}
        for path in target_paths:
            try:
                content = await get_file(token, repo, path, ref=branch)
                target_files[path] = content
            except:
                continue

        if not target_files:
            return self._build_failed_result("Could not fetch target YAML files")

        # 2. Validation and Patching
        patches = {}
        total_confidence = 0.0
        explanations = []

        for filepath, content in target_files.items():
            validation = await validate_yaml(content)
            # Proceed even if currently valid if it's a workflow file (might have logical error)
            
            prompt = self._build_repair_prompt(filepath, content, self.task.payload, validation)
            try:
                response = await router.complete("repair_generation", prompt, response_format="json")
                parsed = self._parse_repair_response(response)
                
                # Validate patched content
                val_new = await validate_yaml(parsed["patched_content"])
                if val_new["valid"]:
                    patches[filepath] = parsed["patched_content"]
                    total_confidence += parsed["confidence"]
                    explanations.append(f"File {filepath}: {parsed['explanation']}")
                else:
                    logger.warning(f"LLM generated invalid YAML for {filepath}: {val_new['error']}")
            except Exception as e:
                logger.error(f"RepairYaml LLM failure for {filepath}: {e}")

        if not patches:
            logger.warning("No YAML patches generated")
            return AgentResult(
                task_id=self.task.task_id,
                agent_id=self.agent_id,
                agent_type=self.task.task_type,
                pipeline_id=self.pipeline_id,
                status=AgentStatus.COMPLETE,
                findings={"patches": {}, "explanation": "No valid patches generated", "patch_type": "yaml_fix"},
                confidence=0.1,
                suggested_repairs=[]
            )

        avg_confidence = total_confidence / len(patches)
        
        return AgentResult(
            task_id=self.task.task_id,
            agent_id=self.agent_id,
            agent_type=self.task.task_type,
            pipeline_id=self.pipeline_id,
            status=AgentStatus.COMPLETE,
            findings={
                "patches": patches,
                "files_patched": list(patches.keys()),
                "explanation": "\n".join(explanations),
                "patch_type": "yaml_fix"
            },
            confidence=avg_confidence,
            suggested_repairs=[]
        )

    def _build_repair_prompt(self, filepath: str, current_content: str,
                              payload: dict,
                              validation: dict) -> list[dict]:
        system = "You are a YAML and CI/CD configuration expert. Fix YAML files to resolve build failures. Always respond with valid JSON only. No markdown, no explanation."
        user = f"""Fix this YAML file to resolve the build failure.

File: {filepath}
Error signature: {payload.get("error_signature")}
Error type: {payload.get("error_type")}
Iteration: {payload.get("iteration", 1)}

YAML validation result:
{json.dumps(validation, indent=2)}

Stack trace context:
{payload.get("stack_trace_summary", "None")}

Web search guidance: {payload.get("web_search_fix") or "None available"}

Current file content:
{current_content}

Respond with exactly this JSON:
{{
  "patched_content": "complete corrected YAML as string",
  "changes_made": ["list", "of", "changes"],
  "explanation": "Why these changes fix the failure",
  "confidence": 0.0
}}

Rules:
- patched_content must be complete valid YAML
- preserve all correct configuration
- do not change indentation style
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
