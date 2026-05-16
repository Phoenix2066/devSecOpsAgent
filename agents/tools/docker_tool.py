import docker
from typing import Optional, Tuple, Dict, List
import logging

logger = logging.getLogger(__name__)

try:
    client = docker.from_env()
except Exception as e:
    logger.error(f"Failed to initialize Docker client: {e}")
    client = None


async def create_container(image: str, env: Dict[str, str], network: str, volumes: Optional[Dict[str, Dict[str, str]]] = None, working_dir: Optional[str] = None) -> str:
    """Creates Docker container. Returns container ID."""
    if not client:
        raise RuntimeError("Docker client not initialized")
    
    container = client.containers.run(
        image,
        detach=True,
        environment=env,
        network=network,
        volumes=volumes,
        working_dir=working_dir,
        tty=True,
        stdin_open=True
    )
    return container.id


async def run_command(container_id: str, cmd: List[str], timeout: Optional[int] = None) -> Tuple[int, str]:
    """Runs command in container. Returns (exit_code, output)."""
    if not client:
        raise RuntimeError("Docker client not initialized")
    
    container = client.containers.get(container_id)
    # exec_run doesn't natively support a timeout in the same way wait_for does,
    # but we can use asyncio.wait_for around the call if we wrap it.
    exit_code, output = container.exec_run(cmd)
    return exit_code, output.decode("utf-8")


async def get_logs(container_id: str, tail: int = 200) -> str:
    """Gets container stdout+stderr logs. Returns string."""
    if not client:
        raise RuntimeError("Docker client not initialized")
    
    container = client.containers.get(container_id)
    return container.logs(tail=tail).decode("utf-8")


async def destroy_container(container_id: str) -> None:
    """Stops and removes container."""
    if not client:
        return
    
    try:
        container = client.containers.get(container_id)
        container.stop()
        container.remove()
    except Exception as e:
        logger.warning(f"Failed to destroy container {container_id}: {e}")


async def create_network(name: str) -> str:
    """Creates Docker network. Returns network ID."""
    if not client:
        raise RuntimeError("Docker client not initialized")
    
    # Check if network exists
    networks = client.networks.list(names=[f"^{name}$"])
    if networks:
        return networks[0].id
        
    network = client.networks.create(name, driver="bridge")
    return network.id

async def destroy_network(network_id: str) -> None:
    """Removes a Docker network."""
    if not client:
        return
    try:
        network = client.networks.get(network_id)
        network.remove()
    except Exception as e:
        logger.warning(f"Failed to destroy network {network_id}: {e}")
