from fastapi import Query
from fastapi.routing import APIRouter
import src.controllers.search as controller
import src.schemas.search as schemas
from typing import Annotated

# Initialize Fastapi router
router = APIRouter(prefix = "/search")

# Return the top k most relevant results by BM25 score
@router.get("")
async def get_test_data(inputs: Annotated[schemas.ServiceInput, Query()]) -> schemas.ServiceOutput:
    return await controller.get_embedding_data(inputs.query, inputs.top_k)