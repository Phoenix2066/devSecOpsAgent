from collections import Counter

ALLOWED_REPAIR_TYPES = {"repair_imports", "repair_yaml", "repair_docker"}

def aggregate_findings(results: list[dict]) -> dict:
    """Merge findings from all investigation worker AgentResults."""
    if not results:
        return {}

    # 1. Collect error types - pick most frequent
    error_types = [r.get("findings", {}).get("error_type") for r in results if r.get("findings", {}).get("error_type")]
    most_common_error = Counter(error_types).most_common(1)[0][0] if error_types else "unknown"

    # 2. Collect error signatures - pick highest confidence one
    valid_sigs = [(r.get("findings", {}).get("error_signature"), r.get("confidence", 0)) 
                  for r in results if r.get("findings", {}).get("error_signature")]
    best_sig = sorted(valid_sigs, key=lambda x: x[1], reverse=True)[0][0] if valid_sigs else "unknown"

    # 3. Merge all suggested repairs - deduplicate, preserve order by frequency
    all_suggestions = []
    for r in results:
        all_suggestions.extend(r.get("suggested_repairs", []))
    
    # Count frequency for sorting
    suggestion_counts = Counter(all_suggestions)
    # Deduplicate while preserving order of first appearance, but weighted by frequency
    repair_targets = sorted(list(set(all_suggestions)), key=lambda x: suggestion_counts[x], reverse=True)

    # 4. Merge all affected files - deduplicate
    affected_files = set()
    for r in results:
        files = r.get("findings", {}).get("affected_files", [])
        if isinstance(files, list):
            affected_files.update(files)

    # 5. Collect from dependency inspector
    conflicts = []
    missing = []
    fix_suggestions = []
    package_manager = None
    for r in results:
        findings = r.get("findings", {})
        conflicts.extend(findings.get("conflicts", []))
        missing.extend(findings.get("missing", []))
        fix_suggestions.extend(findings.get("fix_suggestions", []))
        if findings.get("package_manager"):
            package_manager = findings.get("package_manager")

    # 6. Collect file contents
    file_contents = {}
    for r in results:
        contents = r.get("findings", {}).get("file_contents", {})
        if isinstance(contents, dict):
            file_contents.update(contents)

    # 7. Pick stack trace summary from highest confidence result
    best_result = sorted(results, key=lambda x: x.get("confidence", 0), reverse=True)[0]
    stack_trace = best_result.get("findings", {}).get("stack_trace_summary", "No summary available")
    raw_logs_tail = best_result.get("findings", {}).get("raw_logs_tail")
    failure_stage = best_result.get("findings", {}).get("failure_stage", "unknown")

    return {
        "error_type": most_common_error,
        "error_signature": best_sig,
        "failure_stage": failure_stage,
        "stack_trace_summary": stack_trace,
        "affected_files": list(affected_files),
        "repair_targets": repair_targets,
        "conflicts": conflicts,
        "missing": missing,
        "fix_suggestions": fix_suggestions,
        "file_contents": file_contents,
        "package_manager": package_manager,
        "raw_logs_tail": raw_logs_tail
    }

def compute_confidence(results: list[dict], memory_result: dict, iteration: int) -> float:
    """Compute overall confidence for the repair plan."""
    if not results:
        return 0.0

    # 1. base = average of confidence values across all results
    confidences = [r.get("confidence", 0) for r in results]
    base = sum(confidences) / len(confidences) if confidences else 0.5

    # 2. memory boost
    memory_boost = 0.0
    if memory_result.get("hit"):
        if memory_result.get("reuse"):
            memory_boost = 0.20
        else:
            memory_boost = 0.10

    # 3. iteration penalty
    iteration_penalty = (iteration - 1) * 0.08

    # 4. final confidence
    confidence = base + memory_boost - iteration_penalty
    
    # 5. Clamp and round
    return round(max(0.0, min(1.0, confidence)), 4)

def decide_repair_strategy(unified_findings: dict, memory_result: dict, web_search_result: dict | None) -> list[str]:
    """Return ordered list of repair worker types to spawn."""
    strategy = []

    # 1. Memory reuse priority
    if memory_result.get("hit") and memory_result.get("reuse"):
        # Plan says: extract from memory fix_applied field. 
        # Usually it's a string like "repair_imports, repair_yaml"
        fix_applied = memory_result.get("best", {}).get("fix_applied", "")
        if fix_applied:
            for part in fix_applied.replace(" ", "").split(","):
                if part in ALLOWED_REPAIR_TYPES:
                    strategy.append(part)
        if strategy:
            return list(dict.fromkeys(strategy))

    # 2. Logic based rules
    err_type = unified_findings.get("error_type", "")
    affected_files = [f.lower() for f in unified_findings.get("affected_files", [])]

    if "dependency_conflict" in err_type or "import_error" in err_type:
        strategy.append("repair_imports")

    if "yaml_syntax" in err_type or any(f.endswith(".yml") or f.endswith(".yaml") for f in affected_files):
        strategy.append("repair_yaml")

    if "docker_error" in err_type or any("dockerfile" in f for f in affected_files):
        strategy.append("repair_docker")

    # 5. If none matched above, use suggestions from findings
    if not strategy and unified_findings.get("repair_targets"):
        strategy.extend(unified_findings.get("repair_targets"))

    # 6. Final default
    if not strategy:
        strategy = ["repair_imports", "repair_yaml"]

    # Filter to allowed and deduplicate
    final_strategy = [s for s in strategy if s in ALLOWED_REPAIR_TYPES]
    return list(dict.fromkeys(final_strategy))

def build_repair_payloads(repair_strategy: list[str],
                           unified_findings: dict,
                           memory_result: dict,
                           web_search_result: dict | None,
                           base_payload: dict) -> dict[str, dict]:
    """Build per-worker payload for each repair type."""
    payloads = {}
    
    web_search_fix = None
    if web_search_result and web_search_result.get("status") == "complete":
        web_search_fix = web_search_result.get("findings", {}).get("suggested_fix")

    for repair_type in repair_strategy:
        if repair_type == "repair_imports":
            payloads["repair_imports"] = {
                **base_payload,
                "package_manager": unified_findings.get("package_manager"),
                "conflicts": unified_findings.get("conflicts"),
                "missing": unified_findings.get("missing"),
                "fix_suggestions": unified_findings.get("fix_suggestions"),
                "web_search_fix": web_search_fix,
                "file_contents": unified_findings.get("file_contents")
            }
        elif repair_type == "repair_yaml":
            payloads["repair_yaml"] = {
                **base_payload,
                "error_type": unified_findings.get("error_type"),
                "error_signature": unified_findings.get("error_signature"),
                "affected_files": unified_findings.get("affected_files"),
                "stack_trace_summary": unified_findings.get("stack_trace_summary"),
                "web_search_fix": web_search_fix
            }
        elif repair_type == "repair_docker":
            payloads["repair_docker"] = {
                **base_payload,
                "error_signature": unified_findings.get("error_signature"),
                "error_type": unified_findings.get("error_type"),
                "stack_trace_summary": unified_findings.get("stack_trace_summary"),
                "affected_files": unified_findings.get("affected_files"),
                "web_search_fix": web_search_fix
            }

    return payloads
