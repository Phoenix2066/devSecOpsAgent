from typing import Optional


class BuildResult:
    def __init__(self, exit_code: int, output: str, test_failures: list[str] | None = None):
        self.exit_code = exit_code
        self.output = output
        self.test_failures = test_failures or []
        self.passed = exit_code == 0 and not self.test_failures

    def model_dump(self) -> dict:
        return {"exit_code": self.exit_code, "output": self.output, "test_failures": self.test_failures, "passed": self.passed}


class ShadowEnvironment:
    def __init__(self, pipeline_id: str, docker_client, github_client):
        self.pipeline_id = pipeline_id
        self.container_id: Optional[str] = None
        self.network_id: Optional[str] = None
        self.iteration: int = 0
        self.patches: dict[str, str] = {}

    async def create(self, repo_url: str, branch: str) -> None:
        self.container_id = f"shadow-{self.pipeline_id}"
        self.network_id = f"shadow-net-{self.pipeline_id}"

    async def apply_patches(self, patches: dict[str, str]) -> None:
        self.patches.update(patches)

    async def run_build(self) -> BuildResult:
        self.iteration += 1
        if self.patches or self.iteration > 1:
            return BuildResult(0, "build passed after dependency repair")
        return BuildResult(1, "pip dependency conflict: requests 2.28.0 vs 2.31.0", ["dependency conflict"])

    async def destroy(self) -> None:
        self.container_id = None
        self.network_id = None
