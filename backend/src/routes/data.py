from fastapi.routing import APIRouter
from pydantic import BaseModel
from ..controllers import data as controller

# Initialize Fastapi router
router = APIRouter(prefix = "/data")

# Return the first 15 records as a test set
@router.get("/test")
def get_test_data():
    return controller.get_test_data()

# BM25 search with optional metadata filters
@router.get("/bm25")
def get_bm25(
    query: str,
    when_prefix: str | None = None,
    where_contains: str | None = None,
    anomaly_contains: str | None = None,
):
    return controller.get_bm25_data(
        query,
        when_prefix=when_prefix,
        where_contains=where_contains,
        anomaly_contains=anomaly_contains,
    )


class FeedbackBody(BaseModel):
    query_text: str
    doc_id: str
    relevant: bool
    annotator_id: str | None = None
    session_id: str | None = None


@router.post("/feedback")
def post_feedback(body: FeedbackBody):
    """Human-in-the-loop: store relevance label for (query, document)."""
    return controller.submit_feedback(
        body.query_text,
        body.doc_id,
        body.relevant,
        annotator_id=body.annotator_id,
        session_id=body.session_id,
    )