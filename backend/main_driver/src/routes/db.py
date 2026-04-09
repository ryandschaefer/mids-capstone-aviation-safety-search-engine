from fastapi.routing import APIRouter
from fastapi import Query
import src.models.db as model
import src.schemas.db as schemas


router = APIRouter(prefix="/db", tags=["db"])

# @router.post("/feedback", response_model=schemas.IdResponse)
# async def create_feedback(body: schemas.FeedbackCreateInput):
#     row_id = model.insert_feedback(
#         doc_id=body.doc_id,
#         chunk_id=body.chunk_id,
#         feedback_value=body.feedback_value,
#         query_text=body.query_text,
#         mode=body.mode,
#         use_qe=body.use_qe,
#         use_qe_judge=body.use_qe_judge,
#         notes=body.notes,
#     )
#     return {"id": row_id}


# @router.get("/feedback")
# async def get_feedback(limit: int = Query(default=100, ge=1, le=1000)):
#     return model.list_feedback(limit=limit)
