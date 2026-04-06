from fastapi import APIRouter, Query
import src.controllers.search as controller
import src.schemas.search as schemas
from typing import Annotated
from fastapi.responses import StreamingResponse

# Initialize Fastapi router
router = APIRouter(prefix = "/search")

# Return the first 15 records as a test set
@router.get("/test")
async def get_test_data():
    return await controller.get_test_data()

# Run a search
@router.post("")
async def start_search(body: schemas.StartSearchInput) -> schemas.StartSearchOutput:
    return await controller.start_search(body.query, body.top_k, body.mode, body.use_qe, body.use_qe_judge, body.use_feedback_1)

# Retrieve paginated results from a search
@router.get("/retrieve")
async def retrieve_results(body: Annotated[schemas.RetrieveSearchInput, Query()]) -> schemas.RetrieveSearchOutput:
    return await controller.retrieve_results(body.cache_key, body.page, body.page_length, body.metadata_filters)

# Download the results of a search
@router.get("/download")
async def download_results(body: Annotated[schemas.RetrieveSearchInput, Query()]) -> StreamingResponse:
    return await controller.download_results(body.cache_key, body.metadata_filters)