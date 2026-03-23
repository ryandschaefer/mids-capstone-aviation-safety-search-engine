from fastapi.routing import APIRouter
import src.controllers.search as controller
import src.schemas.search as schemas

# Initialize Fastapi router
router = APIRouter(prefix = "/search")

# Return the first 15 records as a test set
@router.get("/test")
async def get_test_data():
    return await controller.get_test_data()

# Run a search
@router.post("")
async def start_search(body: schemas.StartSearchInput) -> schemas.StartSearchOutput:
    return await controller.start_search(body.query, body.top_k, body.mode, body.use_qe, body.use_qe_judge)

# Run a search
@router.get("/retrieve")
async def retrieve_results(body: schemas.RetrieveSearchInput) -> list[dict]:
    return await controller.retrieve_results(body.cache_key, body.page, body.page_length)