import asyncio
from typing import List, Dict, Optional
from llm.openai import get_openai_client
from db.postgres import similarity_search as db_similarity_search

async def generate_embedding(text: str) -> List[float]:
    """
    Generate a 1536-dim embedding using OpenAI text-embedding-3-small.
    """
    # Preprocess text
    text = text.strip().replace("\n", " ")
    if not text:
        raise ValueError("Text is empty after preprocessing")
    
    # Truncate to 8000 chars max
    text = text[:8000]
    
    client = await get_openai_client()
    response = await client.embeddings.create(
        input=[text],
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

async def generate_error_embedding(error_signature: str, root_cause: Optional[str] = None) -> List[float]:
    """
    Build a combined text for embedding and generate it.
    This is the standard way all incidents are embedded.
    """
    text = f"error: {error_signature}"
    if root_cause:
        text += f" cause: {root_cause}"
    return await generate_embedding(text)

async def similarity_search(embedding: List[float], top_k: int = 3) -> List[Dict]:
    """
    Query pgvector for top_k most similar incidents and post-process.
    """
    results = await db_similarity_search(embedding, top_k)
    
    processed = []
    for res in results:
        score = res.get("score", 0)
        # Filter out results with score < 0.4
        if score < 0.4:
            continue
            
        # Round score to 4 decimal places
        res["score"] = round(score, 4)
        
        # Add "reuse" field
        res["reuse"] = score >= 0.75
        
        processed.append(res)
        
    return processed

async def find_similar_incidents(error_signature: str, root_cause: Optional[str] = None) -> Dict:
    """
    Full pipeline: text → embedding → similarity search → structured result.
    """
    embedding = await generate_error_embedding(error_signature, root_cause)
    results = await similarity_search(embedding, top_k=3)
    
    if not results:
        return {"hit": False, "results": []}
    
    best_result = results[0]
    score = best_result["score"]
    
    return {
        "hit": True,
        "reuse": score >= 0.75,
        "best": best_result,
        "results": results,
        "confidence": score
    }

async def batch_generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts efficiently in batches of 10.
    """
    if not texts:
        raise ValueError("Texts list is empty")
        
    client = await get_openai_client()
    embeddings = []
    
    # Process in batches of 10 using asyncio.gather for concurrent calls 
    # OR use OpenAI's native batch input. The instruction says asyncio.gather().
    for i in range(0, len(texts), 10):
        batch = texts[i : i + 10]
        
        # Internal helper for concurrent execution
        async def _get_single_embedding(t: str):
            t = t.strip().replace("\n", " ")[:8000]
            if not t: return [0.0] * 1536
            resp = await client.embeddings.create(input=[t], model="text-embedding-3-small")
            return resp.data[0].embedding
            
        tasks = [_get_single_embedding(t) for t in batch]
        batch_results = await asyncio.gather(*tasks)
        embeddings.extend(batch_results)
        
    return embeddings
