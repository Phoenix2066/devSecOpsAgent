import os
from typing import Optional, List, Dict, Any
from neo4j import AsyncGraphDatabase, AsyncDriver

# Module-level driver — initialized once on startup
_driver: Optional[AsyncDriver] = None

async def init_driver(uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None) -> None:
    """Initialize the Neo4j async driver."""
    global _driver
    uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = user or os.getenv("NEO4J_USER", "neo4j")
    password = password or os.getenv("NEO4J_PASSWORD", "")
    
    _driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    await init_schema()

async def get_driver() -> AsyncDriver:
    """Return active driver. Raise RuntimeError if init_driver() never called."""
    if _driver is None:
        raise RuntimeError("Neo4j driver not initialized. Call init_driver() first.")
    return _driver

async def close_driver() -> None:
    """Close the driver gracefully. Call at FastAPI shutdown."""
    global _driver
    if _driver:
        await _driver.close()
        _driver = None

async def init_schema() -> None:
    """Create constraints and indexes."""
    driver = await get_driver()
    async with driver.session() as session:
        await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (i:Incident) REQUIRE i.id IS UNIQUE")
        await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (f:Fix) REQUIRE f.id IS UNIQUE")
        await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Pipeline) REQUIRE p.id IS UNIQUE")
        await session.run("CREATE INDEX IF NOT EXISTS FOR (i:Incident) ON (i.error_signature)")

# --- Incident nodes ---

async def create_incident_node(incident_id: str, error_signature: str, root_cause: str, confidence: float) -> None:
    """Create (:Incident {id, error_signature, root_cause, confidence}) node."""
    driver = await get_driver()
    async with driver.session() as session:
        query = """
        MERGE (i:Incident {id: $id})
        SET i.error_signature = $error_signature,
            i.root_cause = $root_cause,
            i.confidence = $confidence
        """
        await session.run(query, id=incident_id, error_signature=error_signature, root_cause=root_cause, confidence=confidence)

async def get_incident_node(incident_id: str) -> Optional[Dict[str, Any]]:
    """Fetch incident node by id. Return dict or None."""
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run("MATCH (i:Incident {id: $id}) RETURN i", id=incident_id)
        record = await result.single()
        return record["i"].data() if record else None

# --- Fix nodes ---

async def create_fix_node(fix_id: str, description: str, patch_type: str, success_rate: float) -> None:
    """Create (:Fix {id, description, patch_type, success_rate}) node."""
    driver = await get_driver()
    async with driver.session() as session:
        query = """
        MERGE (f:Fix {id: $id})
        SET f.description = $description,
            f.patch_type = $patch_type,
            f.success_rate = $success_rate
        """
        await session.run(query, id=fix_id, description=description, patch_type=patch_type, success_rate=success_rate)

async def link_incident_to_fix(incident_id: str, fix_id: str) -> None:
    """Create (:Incident)-[:HAS_FIX]->(:Fix) relationship."""
    driver = await get_driver()
    async with driver.session() as session:
        query = """
        MATCH (i:Incident {id: $incident_id})
        MATCH (f:Fix {id: $fix_id})
        MERGE (i)-[:HAS_FIX]->(f)
        """
        await session.run(query, incident_id=incident_id, fix_id=fix_id)

# --- Pipeline nodes ---

async def create_pipeline_node(pipeline_id: str, repo: str, commit_sha: str) -> None:
    """Create (:Pipeline {id, repo, commit_sha}) node. Use MERGE on id."""
    driver = await get_driver()
    async with driver.session() as session:
        query = """
        MERGE (p:Pipeline {id: $id})
        SET p.repo = $repo,
            p.commit_sha = $commit_sha
        """
        await session.run(query, id=pipeline_id, repo=repo, commit_sha=commit_sha)

async def link_pipeline_to_incident(pipeline_id: str, incident_id: str) -> None:
    """Create (:Pipeline)-[:TRIGGERED]->(:Incident) relationship."""
    driver = await get_driver()
    async with driver.session() as session:
        query = """
        MATCH (p:Pipeline {id: $pipeline_id})
        MATCH (i:Incident {id: $incident_id})
        MERGE (p)-[:TRIGGERED]->(i)
        """
        await session.run(query, pipeline_id=pipeline_id, incident_id=incident_id)

# --- Similarity edges ---

async def create_similarity_edge(incident_id_a: str, incident_id_b: str, score: float) -> None:
    """Create (:Incident)-[:SIMILAR_TO {score: float}]->(:Incident). Only if score >= 0.5."""
    if score < 0.5:
        return
    driver = await get_driver()
    async with driver.session() as session:
        query = """
        MATCH (a:Incident {id: $id_a})
        MATCH (b:Incident {id: $id_b})
        MERGE (a)-[r:SIMILAR_TO]-(b)
        SET r.score = $score
        """
        await session.run(query, id_a=incident_id_a, id_b=incident_id_b, score=score)

async def get_similar_incidents(incident_id: str, min_score: float = 0.5) -> List[Dict[str, Any]]:
    """Return all incidents connected via SIMILAR_TO with score >= min_score."""
    driver = await get_driver()
    async with driver.session() as session:
        query = """
        MATCH (i:Incident {id: $id})-[r:SIMILAR_TO]-(other:Incident)
        WHERE r.score >= $min_score
        RETURN other.id AS id, other.error_signature AS error_signature, 
               other.root_cause AS root_cause, other.confidence AS confidence, r.score AS score
        ORDER BY r.score DESC
        """
        result = await session.run(query, id=incident_id, min_score=min_score)
        records = await result.all()
        return [record.data() for record in records]

# --- Agent nodes ---

async def create_agent_node(agent_id: str, agent_type: str, pipeline_id: str) -> None:
    """Create (:Agent {id, agent_type, pipeline_id}) node. Use MERGE on id."""
    driver = await get_driver()
    async with driver.session() as session:
        query = """
        MERGE (a:Agent {id: $id})
        SET a.agent_type = $agent_type,
            a.pipeline_id = $pipeline_id
        """
        await session.run(query, id=agent_id, agent_type=agent_type, pipeline_id=pipeline_id)

async def link_agent_to_fix(agent_id: str, fix_id: str) -> None:
    """Create (:Agent)-[:PRODUCED]->(:Fix) relationship. Use MERGE."""
    driver = await get_driver()
    async with driver.session() as session:
        query = """
        MATCH (a:Agent {id: $agent_id})
        MATCH (f:Fix {id: $fix_id})
        MERGE (a)-[:PRODUCED]->(f)
        """
        await session.run(query, agent_id=agent_id, fix_id=fix_id)

# --- Utility ---

async def run_query(cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Generic query runner for any Cypher."""
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(cypher, **(params or {}))
        records = await result.all()
        return [record.data() for record in records]
