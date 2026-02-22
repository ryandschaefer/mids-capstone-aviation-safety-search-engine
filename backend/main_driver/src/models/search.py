import httpx
import os
from src.schemas.search import ServiceOutput
from fastapi import HTTPException

# Initialize request client
http_client = httpx.AsyncClient(timeout=10.0)

# Get service endpoints from env
BM25_ENDPOINT = os.environ.get("BM25_URL")
EMBEDDING_ENDPOINT = os.environ.get("EMBEDDINGS_URL")

# Get BM25 results from service
async def get_bm25_results(query: str, top_k: int = 50) -> ServiceOutput:
    query_params = {
        "query": query,
        "top_k": top_k
    }
    
    response = await http_client.get(f"{ BM25_ENDPOINT }/search", params = query_params)
    
    # Throw error if request fails
    if response.is_error:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )
    
    return response.json()

# Get embedding retrieval results from service
async def get_embedding_results(query: str, top_k: int = 50) -> ServiceOutput:
    query_params = {
        "query": query,
        "top_k": top_k
    }
    
    response = await http_client.get(f"{ EMBEDDING_ENDPOINT }/search", params = query_params)
    
    # Throw error if request fails
    if response.is_error:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )
        
    return response.json()