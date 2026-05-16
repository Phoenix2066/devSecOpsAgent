from dataclasses import dataclass
from typing import List, Optional
from .environment import BuildResult

@dataclass
class HealthCheck:
    name: str
    passed: bool
    detail: str
    critical: bool

@dataclass
class ValidationResult:
    passed: bool
    confidence: float
    checks: List[HealthCheck]
    iteration: int
    reason: Optional[str]

class ValidationRunner:
    """
    Runs health checks on a shadow build result.
    Called after run_build() returns exit_code == 0.
    Produces a ValidationResult that drives promotion or next iteration.
    """

    PROMOTION_THRESHOLD = 0.70    # minimum confidence to promote

    def __init__(self, pipeline_id: str, docker_client=None):
        self.pipeline_id = pipeline_id

    async def run(self, build_result: BuildResult,
                  iteration: int,
                  memory_confidence: float) -> ValidationResult:
        # Run all health checks in order
        checks = [
            await self.check_exit_code(build_result),
            await self.check_no_test_failures(build_result),
            await self.check_no_error_signature(build_result),
            await self.check_log_warnings(build_result),
            await self.check_iteration_count(iteration)
        ]
        
        confidence = self.compute_confidence(checks, iteration, memory_confidence)
        
        # A validation passes if:
        # 1. All critical checks passed AND
        # 2. confidence >= PROMOTION_THRESHOLD
        all_critical_passed = all(c.passed for c in checks if c.critical)
        passed = all_critical_passed and confidence >= self.PROMOTION_THRESHOLD
        
        reason = None
        if not passed:
            reason = self.summarize_failure(checks)
            if all_critical_passed and confidence < self.PROMOTION_THRESHOLD:
                reason = "Confidence below promotion threshold"
        
        return ValidationResult(
            passed=passed,
            confidence=confidence,
            checks=checks,
            iteration=iteration,
            reason=reason
        )

    async def check_exit_code(self, build_result: BuildResult) -> HealthCheck:
        passed = build_result.exit_code == 0
        detail = "Build succeeded" if passed else f"Build exited with code {build_result.exit_code}"
        return HealthCheck(
            name="Exit Code",
            passed=passed,
            detail=detail,
            critical=True
        )

    async def check_no_test_failures(self, build_result: BuildResult) -> HealthCheck:
        n = len(build_result.test_failures)
        passed = n == 0
        if passed:
            detail = "All tests passed"
        else:
            first_three = ", ".join(build_result.test_failures[:3])
            detail = f"{n} test failures detected: {first_three}"
        return HealthCheck(
            name="Test Failures",
            passed=passed,
            detail=detail,
            critical=True
        )

    async def check_no_error_signature(self, build_result: BuildResult) -> HealthCheck:
        passed = build_result.error_signature is None
        detail = "No error signature detected" if passed else f"Error signature detected: {build_result.error_signature}"
        return HealthCheck(
            name="Error Signature",
            passed=passed,
            detail=detail,
            critical=True
        )

    async def check_log_warnings(self, build_result: BuildResult) -> HealthCheck:
        warning_count = 0
        for line in build_result.logs.splitlines():
            upper_line = line.upper()
            if "WARNING" in upper_line or "WARN" in upper_line:
                warning_count += 1
        
        passed = warning_count <= 10
        detail = "Log warnings within acceptable range" if passed else f"{warning_count} warnings found in build logs"
        return HealthCheck(
            name="Log Warnings",
            passed=passed,
            detail=detail,
            critical=False
        )

    async def check_iteration_count(self, iteration: int) -> HealthCheck:
        passed = iteration <= 3
        if passed:
            detail = f"Passed on iteration {iteration} — high confidence"
        else:
            detail = f"Passed on iteration {iteration} — confidence reduced"
        return HealthCheck(
            name="Iteration Count",
            passed=passed,
            detail=detail,
            critical=False
        )

    def compute_confidence(self, checks: List[HealthCheck],
                            iteration: int,
                            memory_confidence: float) -> float:
        all_critical_passed = all(c.passed for c in checks if c.critical)
        base = 1.0 if all_critical_passed else 0.0
        
        iteration_penalty = min(iteration - 1, 4) * 0.05
        
        # Find Log Warnings check result
        log_warn_check = next((c for c in checks if c.name == "Log Warnings"), None)
        warning_penalty = 0.05 if (log_warn_check and not log_warn_check.passed) else 0.0
        
        memory_boost = 0.10 if memory_confidence >= 0.80 else 0.0
        
        confidence = base - iteration_penalty - warning_penalty + memory_boost
        
        # Clamp to [0.0, 1.0]
        confidence = max(0.0, min(1.0, confidence))
        return round(confidence, 4)

    def summarize_failure(self, checks: List[HealthCheck]) -> str:
        failed_critical = [c.name for c in checks if c.critical and not c.passed]
        if not failed_critical:
            return "Confidence below promotion threshold"
        return f"Failed checks: {', '.join(failed_critical)}"
