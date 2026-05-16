import asyncpg
import json
import os
from typing import List, Dict, Optional, Any

# Module-level pool — initialized once on startup
_pool: Optional[asyncpg.Pool] = None

async def init_pool(database_url: Optional[str] = None) -> None:
    """Initialize the asyncpg connection pool."""
    global _pool
    if database_url is None:
        database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        raise RuntimeError("DATABASE_URL not found in environment or arguments")

    _pool = await asyncpg.create_pool(database_url)
    
    # Run schema init
    await init_schema()

async def get_pool() -> asyncpg.Pool:
    """Return the active pool. Raise RuntimeError if init_pool() was never called."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    return _pool

async def close_pool() -> None:
    """Gracefully close the pool. Call at FastAPI shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

async def init_schema() -> None:
    """Run all CREATE TABLE IF NOT EXISTS statements."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Create extension first
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        
        # users
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT UNIQUE NOT NULL,
            github_username TEXT,
            avatar_url TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """)
        
        # projects
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id),
            github_repo TEXT NOT NULL,
            github_install_id BIGINT,
            webhook_secret TEXT NOT NULL,
            github_token TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """)
        
        # ensure column exists for older DBs
        await conn.execute("""
        ALTER TABLE projects ADD COLUMN IF NOT EXISTS github_token TEXT;
        """)
        
        # pipelines
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS pipelines (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID REFERENCES projects(id),
            commit_sha TEXT NOT NULL,
            branch TEXT NOT NULL,
            status TEXT NOT NULL,
            triggered_at TIMESTAMPTZ DEFAULT NOW(),
            completed_at TIMESTAMPTZ
        );
        """)
        
        # pipeline_runs
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pipeline_id UUID REFERENCES pipelines(id),
            iteration INT NOT NULL DEFAULT 1,
            status TEXT NOT NULL,
            logs TEXT,
            error_signature TEXT,
            started_at TIMESTAMPTZ DEFAULT NOW(),
            ended_at TIMESTAMPTZ
        );
        """)
        
        # agents
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pipeline_id UUID REFERENCES pipelines(id),
            agent_type TEXT NOT NULL,
            status TEXT NOT NULL,
            spawned_at TIMESTAMPTZ DEFAULT NOW(),
            completed_at TIMESTAMPTZ,
            result JSONB
        );
        """)
        
        # incidents
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            error_signature TEXT NOT NULL,
            root_cause TEXT,
            fix_applied TEXT,
            confidence FLOAT DEFAULT 0.0,
            success_rate FLOAT DEFAULT 0.0,
            times_seen INT DEFAULT 1,
            last_seen TIMESTAMPTZ DEFAULT NOW(),
            embedding vector(1536)
        );
        """)
        
        # index
        await conn.execute("""
        CREATE INDEX IF NOT EXISTS incidents_embedding_idx 
        ON incidents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """)

# --- Pipeline queries ---

async def create_pipeline(project_id: str, commit_sha: str, branch: str) -> str:
    """Insert pipeline row with status="pending". Return pipeline id (UUID as str)."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO pipelines (project_id, commit_sha, branch, status) VALUES ($1, $2, $3, 'pending') RETURNING id",
        project_id, commit_sha, branch
    )
    return str(row['id'])

async def update_pipeline_status(pipeline_id: str, status: str) -> None:
    """Update pipeline status. Also sets completed_at=NOW() if status in ("promoted", "rolled_back", "failed")."""
    pool = await get_pool()
    if status in ("promoted", "rolled_back", "failed", "healed"):
        await pool.execute(
            "UPDATE pipelines SET status = $1, completed_at = NOW() WHERE id = $2",
            status, pipeline_id
        )
    else:
        await pool.execute(
            "UPDATE pipelines SET status = $1 WHERE id = $2",
            status, pipeline_id
        )

async def get_pipeline(pipeline_id: str) -> Optional[Dict[str, Any]]:
    """Fetch single pipeline row as dict. Return None if not found."""
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM pipelines WHERE id = $1", pipeline_id)
    return dict(row) if row else None

async def create_pipeline_run(pipeline_id: str, iteration: int) -> str:
    """Insert pipeline_run row with status="running". Return run id."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO pipeline_runs (pipeline_id, iteration, status) VALUES ($1, $2, 'running') RETURNING id",
        pipeline_id, iteration
    )
    return str(row['id'])

async def update_pipeline_run(run_id: str, status: str, logs: Optional[str], error_signature: Optional[str]) -> None:
    """Update pipeline_run row."""
    pool = await get_pool()
    await pool.execute(
        "UPDATE pipeline_runs SET status = $1, logs = $2, error_signature = $3, ended_at = NOW() WHERE id = $4",
        status, logs, error_signature, run_id
    )

# --- Agent queries ---

async def create_agent_record(pipeline_id: str, agent_type: str) -> str:
    """Insert agent row with status="spawned". Return agent id."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO agents (pipeline_id, agent_type, status) VALUES ($1, $2, 'spawned') RETURNING id",
        pipeline_id, agent_type
    )
    return str(row['id'])

async def update_agent_status(agent_id: str, status: str, result: Optional[Dict[str, Any]] = None) -> None:
    """Update agent status. Set completed_at=NOW() if status in ("complete", "failed"). Store result as JSONB if provided."""
    pool = await get_pool()
    result_json = json.dumps(result) if result is not None else None
    
    if status in ("complete", "failed"):
        await pool.execute(
            "UPDATE agents SET status = $1, result = $2, completed_at = NOW() WHERE id = $3",
            status, result_json, agent_id
        )
    else:
        await pool.execute(
            "UPDATE agents SET status = $1, result = $2 WHERE id = $3",
            status, result_json, agent_id
        )

async def get_active_agents(pipeline_id: str) -> List[Dict[str, Any]]:
    """Return all agents for a pipeline where status not in ("complete", "failed")."""
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM agents WHERE pipeline_id = $1 AND status NOT IN ('complete', 'failed')",
        pipeline_id
    )
    return [dict(r) for r in rows]

# --- Incident / memory queries ---

async def create_incident(error_signature: str, root_cause: str, fix_applied: str, confidence: float, embedding: List[float]) -> str:
    """Insert incident row with embedding as pgvector column. Return incident id."""
    pool = await get_pool()
    # asyncpg handles list[float] to vector automatically if type is registered
    # but here we just pass the list and cast it if needed, 
    # though asyncpg-pgvector might be needed for better integration.
    # For now, let's try passing the list directly.
    row = await pool.fetchrow(
        "INSERT INTO incidents (error_signature, root_cause, fix_applied, confidence, embedding) VALUES ($1, $2, $3, $4, $5) RETURNING id",
        error_signature, root_cause, fix_applied, confidence, embedding
    )
    return str(row['id'])

async def similarity_search(embedding: List[float], top_k: int = 3) -> List[Dict[str, Any]]:
    """Query pgvector for top_k most similar incidents using cosine distance."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT id, error_signature, root_cause, fix_applied, confidence, success_rate,
               1 - (embedding <=> $1) AS score
        FROM incidents ORDER BY score DESC LIMIT $2
        """,
        embedding, top_k
    )
    return [dict(r) for r in rows]

async def update_incident_success(incident_id: str, success: bool) -> None:
    """Update success_rate and times_seen. Increment times_seen by 1."""
    pool = await get_pool()
    val = 1.0 if success else 0.0
    await pool.execute(
        """
        UPDATE incidents 
        SET success_rate = (success_rate * times_seen + $1) / (times_seen + 1),
            times_seen = times_seen + 1,
            last_seen = NOW()
        WHERE id = $2
        """,
        val, incident_id
    )

# --- Project queries ---

async def get_project_by_repo(repo: str) -> Optional[Dict[str, Any]]:
    """Fetch project row by github_repo field. Return None if not found."""
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM projects WHERE github_repo = $1", repo)
    return dict(row) if row else None

async def create_project(user_id: str, github_repo: str, webhook_secret: str) -> str:
    """Insert project row. Return project id."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO projects (user_id, github_repo, webhook_secret) VALUES ($1, $2, $3) RETURNING id",
        user_id, github_repo, webhook_secret
    )
    return str(row['id'])
