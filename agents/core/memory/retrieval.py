from uuid import uuid4
from typing import List, Dict, Optional, Any
from core.memory.embeddings import find_similar_incidents, generate_error_embedding, similarity_search
from db import postgres, neo4j

async def lookup_incident(error_signature: str, root_cause: Optional[str] = None) -> Dict[str, Any]:
    """
    Full memory lookup pipeline: Vector search + Neo4j enrichment.
    """
    # 1. Vector similarity search
    embeddings_result = await find_similar_incidents(error_signature, root_cause)
    
    if not embeddings_result.get("hit"):
        return {"hit": False, "source": "none"}
    
    results = embeddings_result.get("results", [])
    processed_results = []
    
    # 3. Enrich top results with Neo4j graph neighbors
    for res in results[:3]:
        incident_id = res["id"]
        # Fetch neighbors from graph
        related = await neo4j.get_similar_incidents(incident_id)
        
        # Build enriched record
        enriched = {
            "incident_id": str(res["id"]),
            "error_signature": res["error_signature"],
            "root_cause": res.get("root_cause"),
            "fix_applied": res.get("fix_applied"),
            "success_rate": res.get("success_rate", 0.0),
            "score": res["score"],
            "related": related
        }
        processed_results.append(enriched)
        
    if not processed_results:
        return {"hit": False, "source": "none"}

    best = processed_results[0]
    alternatives = processed_results[1:]
    
    return {
        "hit": True,
        "reuse": embeddings_result.get("reuse", False),
        "confidence": embeddings_result.get("confidence", 0.0),
        "best": best,
        "alternatives": alternatives,
        "source": "memory"
    }

async def store_incident(error_signature: str, root_cause: str, fix_applied: str, 
                         confidence: float, success: bool, pipeline_id: str) -> str:
    """
    Full storage pipeline — call this after every repair attempt.
    """
    # 1. Generate embedding
    embedding = await generate_error_embedding(error_signature, root_cause)
    
    # 2. Store in PostgreSQL
    incident_id = await postgres.create_incident(
        error_signature=error_signature,
        root_cause=root_cause,
        fix_applied=fix_applied,
        confidence=confidence,
        embedding=embedding
    )
    
    # 3. Create Neo4j node
    await neo4j.create_incident_node(
        incident_id=incident_id,
        error_signature=error_signature,
        root_cause=root_cause,
        confidence=confidence
    )
    
    # 4. Find similar existing incidents for graph edges
    similar_incidents = await similarity_search(embedding, top_k=5)
    
    # 5. Create similarity edges in Neo4j
    for sim in similar_incidents:
        # Cast id to str to be safe
        sim_id = str(sim["id"])
        if sim_id != incident_id and sim["score"] >= 0.5:
            await neo4j.create_similarity_edge(incident_id, sim_id, sim["score"])
            
    # 6. Link to pipeline
    await neo4j.link_pipeline_to_incident(pipeline_id, incident_id)
    
    return incident_id

async def store_fix(incident_id: str, fix_description: str, patch_type: str, 
                    success: bool, agent_id: str) -> str:
    """
    Store a fix node in Neo4j and link to incident.
    """
    fix_id = str(uuid4())
    success_rate = 1.0 if success else 0.0
    
    # 2. Create Fix node
    await neo4j.create_fix_node(
        fix_id=fix_id,
        description=fix_description,
        patch_type=patch_type,
        success_rate=success_rate
    )
    
    # 3. Link Incident -> Fix
    await neo4j.link_incident_to_fix(incident_id, fix_id)
    
    # 4. Link Agent -> Fix
    await neo4j.link_agent_to_fix(agent_id, fix_id)
    
    return fix_id

async def update_outcome(incident_id: str, success: bool) -> None:
    """
    Update success rate after a repair attempt resolves.
    """
    # 1. Update SQL stats
    await postgres.update_incident_success(incident_id, success)
    
    # 2. Fetch current node from Neo4j
    node = await neo4j.get_incident_node(incident_id)
    if not node:
        return
        
    # 3. Recalculate confidence (decay old, weight new)
    old_confidence = node.get("confidence", 0.0)
    new_confidence = (old_confidence * 0.7) + ((1.0 if success else 0.0) * 0.3)
    
    # 4. Update Neo4j node
    await neo4j.run_query(
        "MATCH (i:Incident {id: $id}) SET i.confidence = $confidence",
        {"id": incident_id, "confidence": new_confidence}
    )

async def get_repair_history(error_signature: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get past repair attempts for similar errors.
    """
    # 1. Find vector matches
    embeddings_result = await find_similar_incidents(error_signature)
    if not embeddings_result.get("hit"):
        return []
        
    best_match_id = embeddings_result["best"]["id"]
    
    # 3. Get similar incidents from Neo4j
    related_incidents = await neo4j.get_similar_incidents(best_match_id)
    
    # Include the best match itself in the pool to check
    incident_pool = [best_match_id] + [r["id"] for r in related_incidents]
    
    history = []
    
    # 4. Fetch fixes for each related incident
    for inc_id in incident_pool:
        fixes = await neo4j.run_query(
            "MATCH (i:Incident {id: $id})-[:HAS_FIX]->(f:Fix) RETURN f, i.error_signature as sig",
            {"id": str(inc_id)}
        )
        
        # Find the vector score for this incident if available
        # This is a bit complex since some are from vector search and some from graph
        score = 0.0
        for res in embeddings_result.get("results", []):
            if str(res["id"]) == str(inc_id):
                score = res["score"]
                break
        if score == 0.0:
            for rel in related_incidents:
                if str(rel["id"]) == str(inc_id):
                    score = rel.get("score", 0.0)
                    break

        for record in fixes:
            fix_data = record["f"]
            history.append({
                "incident_id": str(inc_id),
                "error_signature": record["sig"],
                "fix_description": fix_data.get("description"),
                "patch_type": fix_data.get("patch_type"),
                "success_rate": fix_data.get("success_rate", 0.0),
                "score": score
            })
            
    # 5. Rank and limit
    history.sort(key=lambda x: (x["success_rate"], x["score"]), reverse=True)
    return history[:limit]
