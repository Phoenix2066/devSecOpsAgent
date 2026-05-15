async def create_container(image: str, env: dict, network: str) -> str:
    return "mock-container"


async def run_command(container_id: str, cmd: list[str]) -> tuple[int, str]:
    return 0, "build passed"


async def get_logs(container_id: str, tail: int = 200) -> str:
    return "mock container logs"


async def destroy_container(container_id: str) -> None:
    return None


async def create_network(name: str) -> str:
    return "mock-network"
