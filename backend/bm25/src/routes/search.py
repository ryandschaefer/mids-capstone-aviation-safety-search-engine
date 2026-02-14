from fastapi.routing import APIRouter
import src.controllers.search as controller

# Initialize Fastapi router
router = APIRouter(prefix = "/search")

# Return the top k most relevant results by BM25 score
@router.get("")
async def get_test_data(query: str, top_k: int = 50):
    return await controller.get_bm25_data(query, top_k)