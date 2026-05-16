import json
import re
import logging
from base.worker import BaseWorker
from base.types import AgentResult, AgentStatus
from tools.search_tool import search, fetch_page
from api.events import emit_web_search_started, emit_web_search_complete
from llm.router import ModelRouter

logger = logging.getLogger(__name__)
router = ModelRouter()

class WebSearchWorker(BaseWorker):
    """
    Dynamic worker. Fires on memory miss (confidence < 0.5).
    Searches external sources for known fixes to the error signature.
    Results are fed back to Coordinator alongside investigation findings.
    """

    MAX_RESULTS_PER_SOURCE = 3
    MAX_PAGE_CONTENT_CHARS = 3000

    SEARCH_QUERIES = [
        "{error_signature} fix github issues",
        "{error_signature} stackoverflow solution",
        "{error_signature} {package_manager} documentation",
    ]

    async def execute(self) -> AgentResult:
        # task.payload expected keys:
        # {
        #   "error_signature": str,
        #   "error_type": str,
        #   "package_manager": str | None,
        #   "stack_trace_summary": str | None,
        #   "pipeline_id": str
        # }

        error_signature = self.task.payload.get("error_signature", "unknown error")
        error_type = self.task.payload.get("error_type", "unknown")
        package_manager = self.task.payload.get("package_manager")
        stack_trace_summary = self.task.payload.get("stack_trace_summary")
        pipeline_id = self.pipeline_id

        # 1. Emit web search started
        await emit_web_search_started(pipeline_id, error_signature)

        # 2. Build search queries
        queries = self._build_queries(error_signature, error_type, package_manager)

        # 3. Execute searches
        all_results = []
        for query in queries:
            try:
                results = await search(query, num_results=self.MAX_RESULTS_PER_SOURCE)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Search failed for query '{query}': {e}")

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for r in all_results:
            if r["url"] not in seen_urls:
                unique_results.append(r)
                seen_urls.add(r["url"])

        # 4. Fetch page content for top 3 results
        enriched = []
        for result in unique_results[:3]:
            try:
                content = await fetch_page(result["url"])
                enriched.append({**result, "content": content[:self.MAX_PAGE_CONTENT_CHARS]})
            except Exception as e:
                logger.error(f"Failed to fetch page content for {result['url']}: {e}")
                enriched.append({**result, "content": "Failed to fetch content"})

        # 5. Synthesize with LLM
        synthesis = await self._synthesize(enriched, error_signature, stack_trace_summary, package_manager)

        # 6. Emit web search complete
        sources = [r["url"] for r in enriched]
        await emit_web_search_complete(pipeline_id, sources, synthesis["confidence"])

        # 7. Return AgentResult
        findings = {
            "error_signature": error_signature,
            "search_queries": queries,
            "sources": [{"url": r["url"], "title": r.get("title"), "snippet": r.get("snippet")} for r in unique_results],
            "synthesis": synthesis["summary"],
            "suggested_fix": synthesis["suggested_fix"],
            "fix_type": synthesis["fix_type"],
            "code_snippets": synthesis["code_snippets"],
            "references": synthesis["references"]
        }
        
        return AgentResult(
            task_id=self.task.task_id,
            agent_id=self.agent_id,
            agent_type=self.task.task_type,
            pipeline_id=self.pipeline_id,
            status=AgentStatus.COMPLETE,
            findings=findings,
            confidence=synthesis["confidence"],
            suggested_repairs=synthesis["suggested_repairs"]
        )

    def _build_queries(self, error_signature: str, error_type: str,
                        package_manager: str | None) -> list[str]:
        pm = package_manager or error_type
        queries = []
        for template in self.SEARCH_QUERIES:
            queries.append(template.format(error_signature=error_signature, package_manager=pm))
        
        # Add targeted query
        if error_type == "import_error":
            queries.append(f"python {error_signature} ModuleNotFoundError fix")
        elif error_type == "dependency_conflict":
            queries.append(f"{pm} dependency conflict {error_signature} resolve")
        elif error_type == "yaml_syntax":
            queries.append(f"yaml syntax error {error_signature} fix")
        elif error_type == "docker_error":
            queries.append(f"dockerfile {error_signature} fix")
        elif error_type == "test_failure":
            queries.append(f"pytest {error_signature} fix")
        else:
            queries.append(f"{error_signature} fix solution")
            
        return list(dict.fromkeys(queries))[:4]

    async def _synthesize(self, enriched_results: list[dict],
                           error_signature: str,
                           stack_trace_summary: str | None,
                           package_manager: str | None) -> dict:
        system = "You are a DevOps repair expert. Given search results about a build error, synthesize the most actionable fix. Respond with valid JSON only. No explanation, no markdown, no code blocks."
        
        user = f"""Synthesize these search results into a repair plan.

Error signature: {error_signature}
Stack trace summary: {stack_trace_summary or "Not available"}
Package manager: {package_manager or "Unknown"}

Search results:
{self._format_search_results(enriched_results)}

Respond with exactly this JSON structure:
{{
  "summary": "2-3 sentence explanation of the error and fix",
  "suggested_fix": "Specific actionable fix description",
  "fix_type": "version_pin|package_replace|config_change|code_change|unknown",
  "code_snippets": [
    {{"language": "lang", "description": "desc", "code": "code"}}
  ],
  "references": [
    {{"title": "title", "url": "url", "relevance": "high|medium|low"}}
  ],
  "suggested_repairs": ["repair_imports", "repair_yaml"],
  "confidence": 0.0
}}

Rules:
- suggested_repairs must only contain: repair_imports, repair_yaml, repair_docker
- confidence 0.0-1.0 — be conservative, max 0.75 for web search results
- code_snippets may be empty list if no specific code fix found
- fix_type must be exactly one of the enum values"""

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
        
        try:
            response = await router.complete("web_synthesis", messages, response_format="json")
            parsed = self._parse_synthesis_response(response)
            # Cap confidence at 0.75
            parsed["confidence"] = min(0.75, float(parsed.get("confidence", 0.1)))
            return parsed
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return self._parse_synthesis_response("")

    def _format_search_results(self, results: list[dict]) -> str:
        formatted = ""
        for r in results:
            formatted += f"Source: {r.get('title')}\nURL: {r.get('url')}\nSnippet: {r.get('snippet')}\nContent: {r.get('content', '')[:1000]}\n---\n"
        return formatted

    def _parse_synthesis_response(self, response: str) -> dict:
        safe_default = {
            "summary": "Web search synthesis failed",
            "suggested_fix": "Manual investigation required",
            "fix_type": "unknown",
            "code_snippets": [],
            "references": [],
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
