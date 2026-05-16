# scripts/seed_memory.py
# Pre-seeds the incident memory database with known incidents for demo.
# Run once after docker-compose up and before the demo.
# Usage: python scripts/seed_memory.py

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add agents directory to path so we can import modules
sys.path.append(str(Path(__file__).parent.parent / "agents"))

from db import postgres, neo4j, redis
from core.memory.retrieval import store_incident

load_dotenv()

async def seed():
    print("Initializing database connections...")
    
    # 1. Init all DB connections
    db_url = os.getenv("DATABASE_URL", "postgres://devsecops:devsecops@localhost:5432/devsecops")
    await postgres.init_pool(db_url)
    
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_pass = os.getenv("NEO4J_PASSWORD", "devsecops123")
    await neo4j.init_driver(neo4j_uri, neo4j_user, neo4j_pass)
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    await redis.init_client(redis_url)

    print("Seeding known incidents...")

    # 2. Store known incident — the one that matches the demo broken commit:
    try:
        incident_id = await store_incident(
            error_signature="pip_conflict:requests:2.28.0_vs_httpx:0.23.0",
            root_cause="requests==2.28.0 conflicts with httpx==0.23.0 urllib3 constraints",
            fix_applied="pin requests==2.31.0 and httpx==0.24.1",
            confidence=0.92,
            success=True,
            pipeline_id="seed-pipeline-000"
        )
        print(f"Seeded incident: {incident_id}")
        
        # 3. Store a second known incident for variety:
        incident_id2 = await store_incident(
            error_signature="importerror:missing_module:flask",
            root_cause="flask not listed in requirements.txt",
            fix_applied="add flask==2.3.3 to requirements.txt",
            confidence=0.88,
            success=True,
            pipeline_id="seed-pipeline-001"
        )
        print(f"Seeded incident: {incident_id2}")
        
    except Exception as e:
        print(f"Error seeding memory: {e}")
        if "OPENAI_API_KEY" not in os.environ:
            print("Note: Seeding requires a valid OPENAI_API_KEY for embedding generation.")

    # 4. Close all connections
    await postgres.close_pool()
    await neo4j.close_driver()
    await redis.close_client()
    
    print("Memory seeded successfully. Ready for demo.")

if __name__ == "__main__":
    asyncio.run(seed())
