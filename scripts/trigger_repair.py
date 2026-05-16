import asyncio
import os
import json
from uuid import uuid4
from datetime import datetime
import asyncpg
from redis.asyncio import Redis

# Database and Redis URLs
DATABASE_URL = os.getenv("DATABASE_URL", "postgres://devsecops:devsecops@localhost:5432/devsecops")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

async def trigger_mock_failure(repo_name: str, branch: str = "main"):
    print(f"Connecting to database and redis...")
    conn = await asyncpg.connect(DATABASE_URL)
    redis = Redis.from_url(REDIS_URL)

    # 1. Get project ID
    row = await conn.fetchrow("SELECT id, github_token FROM projects WHERE github_repo = $1", repo_name)
    if not row:
        print(f"Error: Project {repo_name} not found in database.")
        await conn.close()
        return

    project_id = row['id']
    github_token = row['github_token']
    pipeline_id = str(uuid4())
    commit_sha = "mock-sha-" + os.urandom(4).hex()

    print(f"Project ID: {project_id}")
    print(f"Creating mock pipeline {pipeline_id}...")

    # 2. Create pipeline record
    await conn.execute(
        "INSERT INTO pipelines (id, project_id, commit_sha, branch, status, triggered_at) VALUES ($1, $2, $3, $4, 'pending', $5)",
        pipeline_id, project_id, commit_sha, branch, datetime.now()
    )

    # 3. Push to Redis queue
    event = {
        "event_type": "pipeline_triggered",
        "pipeline_id": pipeline_id,
        "repo": repo_name,
        "commit_sha": commit_sha,
        "branch": branch,
        "github_token": github_token,
        "triggered_at": datetime.now().isoformat()
    }

    await redis.rpush("queue:orchestrator", json.dumps(event))
    
    print(f"Successfully triggered repair for {repo_name}!")
    print(f"Pipeline ID: {pipeline_id}")
    print(f"Navigate to: http://localhost:3000/dashboard")
    print(f"The agents should wake up in a few seconds.")

    await conn.close()
    await redis.close()

if __name__ == "__main__":
    import sys
    repo = sys.argv[1] if len(sys.argv) > 1 else "Adithya2005-spec/TrafficAI"
    asyncio.run(trigger_mock_failure(repo))
