import httpx
import os

# Initialize request client
http_client = httpx.AsyncClient(timeout=10.0)

# Get service endpoints from env
BM25_ENDPOINT = os.environ.get("BM25_URL")

# Get BM25 results from service
async def get_bm25_results(query: str, top_k: int = 50):
    query_params = {
        "query": query,
        "top_k": top_k
    }
    
    response = await http_client.get(f"{ BM25_ENDPOINT }/search", params = query_params)
    response.raise_for_status()
    return response.json()