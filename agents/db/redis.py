import os
import json
import asyncio
import redis.asyncio as redis
from typing import Optional, Callable, Awaitable

# Module-level client — initialized once on startup
_client: Optional[redis.Redis] = None

async def init_client(redis_url: Optional[str] = None) -> None:
    """Initialize Redis client from redis_url or REDIS_URL env var."""
    global _client
    if redis_url is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    _client = redis.from_url(redis_url, decode_responses=True)

async def get_client() -> redis.Redis:
    """Return active client. Raise RuntimeError if init_client() never called."""
    if _client is None:
        raise RuntimeError("Redis client not initialized. Call init_client() first.")
    return _client

async def close_client() -> None:
    """Close Redis connection. Call at FastAPI shutdown."""
    global _client
    if _client:
        await _client.aclose()
        _client = None

# --- Key-value state ---

async def set_state(key: str, value: dict, ttl_seconds: Optional[int] = None) -> None:
    """Serialize value to JSON and SET in Redis."""
    client = await get_client()
    serialized = json.dumps(value)
    if ttl_seconds:
        await client.setex(key, ttl_seconds, serialized)
    else:
        await client.set(key, serialized)

async def get_state(key: str) -> Optional[dict]:
    """GET and deserialize JSON value. Return None if key doesn't exist."""
    client = await get_client()
    value = await client.get(key)
    if value:
        return json.loads(value)
    return None

async def delete_state(key: str) -> None:
    """DELETE a key. No error if key doesn't exist."""
    client = await get_client()
    await client.delete(key)

async def increment(key: str) -> int:
    """INCR a key. Return new integer value."""
    client = await get_client()
    return await client.incr(key)

# --- Task queues (Redis Lists) ---

async def enqueue(queue_name: str, payload: dict) -> None:
    """RPUSH serialized JSON payload onto queue_name list."""
    client = await get_client()
    await client.rpush(queue_name, json.dumps(payload))

async def dequeue(queue_name: str, timeout: int = 5) -> Optional[dict]:
    """BLPOP from queue_name with timeout seconds."""
    client = await get_client()
    result = await client.blpop(queue_name, timeout=timeout)
    if result:
        _, payload = result
        return json.loads(payload)
    return None

async def queue_length(queue_name: str) -> int:
    """LLEN of queue_name. Return 0 if key doesn't exist."""
    client = await get_client()
    return await client.llen(queue_name)

# --- Pub/Sub ---

async def publish(channel: str, message: dict) -> None:
    """PUBLISH serialized JSON message to channel."""
    client = await get_client()
    await client.publish(channel, json.dumps(message))

async def subscribe(channel: str, handler: Callable[[dict], Awaitable[None]]) -> None:
    """
    Subscribe to channel and call handler(message: dict) for each message.
    Runs in a loop until cancelled.
    """
    client = await get_client()
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await handler(data)
    except asyncio.CancelledError:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        raise

# --- Agent state helpers ---

async def set_agent_status(agent_id: str, status: str) -> None:
    """set_state(f'agent:{agent_id}:status', {'status': status}, ttl_seconds=3600)"""
    await set_state(f"agent:{agent_id}:status", {"status": status}, ttl_seconds=3600)

async def get_agent_status(agent_id: str) -> Optional[str]:
    """get_state(f'agent:{agent_id}:status') → return status string or None"""
    state = await get_state(f"agent:{agent_id}:status")
    return state.get("status") if state else None

async def set_pipeline_state(pipeline_id: str, state: dict) -> None:
    """set_state(f'pipeline:{pipeline_id}:state', state)"""
    await set_state(f"pipeline:{pipeline_id}:state", state)

async def get_pipeline_state(pipeline_id: str) -> Optional[dict]:
    """get_state(f'pipeline:{pipeline_id}:state')"""
    return await get_state(f"pipeline:{pipeline_id}:state")

async def set_shadow_iteration(pipeline_id: str, iteration: int) -> None:
    """set_state(f'shadow:{pipeline_id}:iteration', {'iteration': iteration})"""
    await set_state(f"shadow:{pipeline_id}:iteration", {"iteration": iteration})

async def get_shadow_iteration(pipeline_id: str) -> int:
    """get_state(f'shadow:{pipeline_id}:iteration') → return iteration int, default 0"""
    state = await get_state(f"shadow:{pipeline_id}:iteration")
    return state.get("iteration", 0) if state else 0

async def add_active_agent(pipeline_id: str, agent_id: str) -> None:
    """SADD f'pipeline:{pipeline_id}:agents' agent_id"""
    client = await get_client()
    await client.sadd(f"pipeline:{pipeline_id}:agents", agent_id)

async def remove_active_agent(pipeline_id: str, agent_id: str) -> None:
    """SREM f'pipeline:{pipeline_id}:agents' agent_id"""
    client = await get_client()
    await client.srem(f"pipeline:{pipeline_id}:agents", agent_id)

async def get_active_agents(pipeline_id: str) -> set:
    """SMEMBERS f'pipeline:{pipeline_id}:agents' → return set of agent_id strings"""
    client = await get_client()
    members = await client.smembers(f"pipeline:{pipeline_id}:agents")
    return set(members)
