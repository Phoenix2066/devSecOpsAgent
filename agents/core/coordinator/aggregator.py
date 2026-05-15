def aggregate_results(results: list[dict], memory: dict) -> dict:
    repair_targets: set[str] = set()
    errors: set[str] = set()
    confidence_values: list[float] = []
    for result in results:
        findings = result.get("findings", {})
        if findings.get("error_type"):
            errors.add(findings["error_type"])
        repair_targets.update(result.get("suggested_repairs", []))
        confidence_values.append(float(result.get("confidence", 0)))
    memory_confidence = float(memory.get("confidence", 0))
    if memory.get("reuse") and memory.get("fix_applied"):
        repair_targets.add("repair_imports")
    return {
        "errors": sorted(errors),
        "repair_targets": sorted(repair_targets),
        "memory_hit": bool(memory.get("hit")),
        "memory_confidence": memory_confidence,
        "reuse_fix": bool(memory.get("reuse")),
        "suggested_patches": {"requirements.txt": "requests==2.31.0\nflask==2.3.0\n"},
        "overall_confidence": round((sum(confidence_values) + memory_confidence) / max(len(confidence_values) + 1, 1), 2),
    }
