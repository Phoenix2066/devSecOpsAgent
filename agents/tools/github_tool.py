async def get_file(repo: str, path: str, ref: str = "main") -> str:
    if path.endswith("requirements.txt"):
        return "requests==2.28.0\nflask==2.3.0\n"
    return ""


async def get_file_tree(repo: str, ref: str = "main") -> list[str]:
    return ["requirements.txt", ".github/workflows/ci.yml", "Dockerfile"]


async def get_actions_logs(repo: str, run_id: str) -> str:
    return "pip dependency conflict: requests 2.28.0 vs 2.31.0"


async def create_branch(repo: str, base_sha: str, branch_name: str) -> str:
    return f"refs/heads/{branch_name}"


async def commit_files(repo: str, branch: str, message: str, files: dict[str, str]) -> str:
    return "mock-commit-sha"


async def open_pull_request(repo: str, head: str, base: str, title: str, body: str) -> str:
    return f"https://github.com/{repo}/pull/mock"
