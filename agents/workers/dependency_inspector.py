import json
import re
import logging
from base.worker import BaseWorker
from base.types import AgentResult, AgentStatus
from tools.github_tool import get_file, get_file_tree
from tools.code_tool import analyze_dependencies
from llm.router import ModelRouter

logger = logging.getLogger(__name__)
router = ModelRouter()

class DependencyInspectorWorker(BaseWorker):
    """
    Dynamic worker. Fetches and analyzes dependency files from the repo.
    Identifies conflicts, version mismatches, unpinned packages.
    Always spawned in parallel with LogAnalyzerWorker.
    """

    # Dependency files to look for, in priority order per package manager
    DEPENDENCY_FILES = {
        "pip": ["requirements.txt", "requirements-dev.txt", "setup.py", "pyproject.toml"],
        "npm": ["package.json", "package-lock.json"],
        "go":  ["go.mod", "go.sum"],
    }

    async def execute(self) -> AgentResult:
        # task.payload expected keys:
        # {
        #   "repo": str,
        #   "github_token": str,
        #   "branch": str,
        #   "error_signature": str | None,
        #   "affected_files": list[str]
        # }

        repo = self.task.payload.get("repo")
        token = self.task.payload.get("github_token")
        branch = self.task.payload.get("branch", "main")
        error_signature = self.task.payload.get("error_signature")

        # 1. Detect package manager and fetch dependency files
        fetched = await self._fetch_dependency_files(token, repo, branch)
        if not fetched:
            return self._build_failed_result("No dependency files found in repository")

        # 2. Run static analysis on each file
        analyses = []
        for filepath, content in fetched.items():
            analysis = await analyze_dependencies(filepath, content)
            analyses.append({"file": filepath, "analysis": analysis})

        # 3. Call LLM for conflict detection
        messages = self._build_analysis_prompt(fetched, analyses, error_signature)
        try:
            response = await router.complete("log_extraction", messages, response_format="json")
            parsed = self._parse_llm_response(response)
        except Exception as e:
            logger.error(f"LLM dependency analysis failed: {e}")
            parsed = self._parse_llm_response("")

        # 4. Return AgentResult
        findings = {
            "package_manager": analyses[0]["analysis"]["package_manager"] if analyses else "unknown",
            "dependency_files": list(fetched.keys()),
            "static_issues": self._collect_static_issues(analyses),
            "conflicts": parsed["conflicts"],
            "outdated": parsed["outdated"],
            "missing": parsed["missing"],
            "fix_suggestions": parsed["fix_suggestions"],
            "file_contents": fetched
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

    async def _fetch_dependency_files(self, token: str, repo: str, branch: str) -> dict[str, str]:
        fetched = {}
        
        # Try to fetch every file in DEPENDENCY_FILES
        all_candidate_files = []
        for files in self.DEPENDENCY_FILES.values():
            all_candidate_files.extend(files)
            
        for path in all_candidate_files:
            try:
                content = await get_file(token, repo, path, ref=branch)
                fetched[path] = content
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.debug(f"Failed to fetch {path}: {e}")

        # If nothing found, try scanning the tree
        if not fetched:
            try:
                tree = await get_file_tree(token, repo, ref=branch)
                for path in tree:
                    filename = path.split("/")[-1]
                    if filename in all_candidate_files:
                        try:
                            content = await get_file(token, repo, path, ref=branch)
                            fetched[path] = content
                        except:
                            continue
            except Exception as e:
                logger.error(f"Failed to fetch file tree: {e}")
                
        return fetched

    def _collect_static_issues(self, analyses: list[dict]) -> list[dict]:
        combined = []
        for item in analyses:
            filepath = item["file"]
            issues = item["analysis"].get("issues", [])
            for issue in issues:
                issue_copy = issue.copy()
                issue_copy["file"] = filepath
                combined.append(issue_copy)
        return combined

    def _build_analysis_prompt(self, fetched: dict[str, str],
                                analyses: list[dict],
                                error_signature: str | None) -> list[dict]:
        system = "You are a dependency resolution expert. Analyze dependency files for conflicts, version mismatches, and missing packages. Always respond with valid JSON only. No explanation, no markdown."
        
        user = f"""Analyze these dependency files for issues.

Error context: {error_signature or "No error signature provided"}

Static analysis findings:
{json.dumps(analyses, indent=2)}

Raw dependency file contents:
{self._format_file_contents(fetched)}

Respond with exactly this JSON structure:
{{
  "conflicts": [
    {{"package": "pkgname", "current_version": "1.0.0", "required_version": "2.0.0", "reason": "why"}}
  ],
  "outdated": [
    {{"package": "pkgname", "current_version": "1.0.0", "detail": "why"}}
  ],
  "missing": [
    {{"package": "pkgname", "reason": "why"}}
  ],
  "fix_suggestions": [
    {{"file": "filename", "package": "pkgname", "action": "update|add|remove", "new_version": "2.0.0"}}
  ],
  "suggested_repairs": ["repair_imports", "repair_yaml"],
  "confidence": 0.0
}}

Rules:
- suggested_repairs must only contain: repair_imports, repair_yaml, repair_docker
- confidence is 0.0-1.0
- All lists may be empty if no issues found of that type"""

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]

    def _format_file_contents(self, fetched: dict[str, str]) -> str:
        output = ""
        for filepath, content in fetched.items():
            # Truncate each file to 2000 chars max
            safe_content = content[:2000]
            output += f"=== {filepath} ===\n{safe_content}\n"
        return output

    def _parse_llm_response(self, response: str) -> dict:
        safe_default = {
            "conflicts": [],
            "outdated": [],
            "missing": [],
            "fix_suggestions": [],
            "suggested_repairs": [],
            "confidence": 0.1
        }
        
        if not response:
            return safe_default

        try:
            clean_response = re.sub(r'```json|```', '', response).strip()
            return json.loads(clean_response)
        except json.JSONDecodeError:
            return safe_default
