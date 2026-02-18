"""
Data routes for Aviation Safety Search API.

Provides endpoints for BM25, semantic, and hybrid search.
"""
from fastapi.routing import APIRouter
import controllers.data as controller

# Initialize Fastapi router
router = APIRouter(prefix = "/data")

# Return the first 15 records as a test set
@router.get("/test")
def get_test_data():
    return controller.get_test_data()

# BM25 search endpoint
@router.get("/bm25")
def search_bm25(query: str, top_k: int = 50):
    return controller.get_bm25_data(query)

# Semantic search endpoint
@router.get("/semantic")
def search_semantic(query: str, top_k: int = 50):
    return controller.get_semantic_data(query, top_k)

# Hybrid search endpoint (BM25 + Semantic)
@router.get("/hybrid")
def search_hybrid(query: str, top_k: int = 50, alpha: float = None):
    """
    Hybrid search combining BM25 and semantic retrieval.

    Args:
        query: Search query text
        top_k: Number of results to return (default: 50)
        alpha: BM25 weight, 0-1 (default: 0.5 from config)
               0 = semantic only, 1 = BM25 only

    Returns:
        List of search results with hybrid scores
    """
    return controller.get_hybrid_data(query, top_k, alpha)
