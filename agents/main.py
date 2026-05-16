import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from uuid import uuid4

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from db import postgres, neo4j, redis
from core.orchestrator.agent import OrchestratorAgent
from core.coordinator.agent import CoordinatorAgent
from core.memory.agent import MemoryAgent
from core.monitor.agent import MonitoringAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP:
    logger.info("Initializing Agent Runtime infrastructure...")
    
    # 1. Init PostgreSQL pool
    db_url = os.getenv("DATABASE_URL", "postgres://devsecops:devsecops@localhost:5432/devsecops")
    await postgres.init_pool(db_url)
    
    # 2. Init Neo4j driver
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_pass = os.getenv("NEO4J_PASSWORD", "devsecops123")
    await neo4j.init_driver(neo4j_uri, neo4j_user, neo4j_pass)
    
    # 3. Init Redis client
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    await redis.init_client(redis_url)
    
    # 4. Start fixed agents as asyncio background tasks
    pool = await postgres.get_pool()
    redis_client = await redis.get_client()
    
    orchestrator = OrchestratorAgent(
        agent_id=f"fixed:orchestrator:{str(uuid4())[:8]}",
        db_pool=pool,
        redis_client=redis_client
    )
    coordinator = CoordinatorAgent(agent_id=f"fixed:coordinator:{str(uuid4())[:8]}")
    memory_agent = MemoryAgent(agent_id=f"fixed:memory:{str(uuid4())[:8]}")
    monitor_agent = MonitoringAgent(agent_id=f"fixed:monitor:{str(uuid4())[:8]}")
    
    tasks = [
        asyncio.create_task(orchestrator.start(), name="orchestrator"),
        asyncio.create_task(coordinator.start(), name="coordinator"),
        asyncio.create_task(memory_agent.start(), name="memory"),
        asyncio.create_task(monitor_agent.start(), name="monitor"),
    ]
    
    app.state.agent_tasks = tasks
    app.state.orchestrator = orchestrator
    
    logger.info("Agent Runtime startup complete. Fixed agents running.")
    
    yield
    
    # SHUTDOWN:
    logger.info("Shutting down Agent Runtime...")
    
    for task in tasks:
        task.cancel()
        
    await asyncio.gather(*tasks, return_exceptions=True)
    
    await postgres.close_pool()
    await neo4j.close_driver()
    await redis.close_client()
    
    logger.info("Agent Runtime shutdown complete.")

app = FastAPI(title="DevSecOps Agent Runtime", lifespan=lifespan)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("FASTAPI_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
