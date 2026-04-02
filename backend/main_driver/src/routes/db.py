from fastapi.routing import APIRouter
from fastapi import Query
import src.models.db as model
import src.schemas.db as schemas


router = APIRouter(prefix="/db", tags=["db"])


@router.get("/health")
async def health():
    return model.get_db_summary()


@router.post("/chunks")
async def upsert_chunk(body: schemas.ChunkUpsertInput):
    model.upsert_chunk(
        doc_id=body.doc_id,
        chunk_id=body.chunk_id,
        chunk_text=body.chunk_text,
        source=body.source,
    )
    return {"ok": True}


@router.post("/chunks/bulk")
async def upsert_chunks_bulk(body: schemas.ChunkBulkUpsertInput):
    for item in body.items:
        model.upsert_chunk(
            doc_id=item.doc_id,
            chunk_id=item.chunk_id,
            chunk_text=item.chunk_text,
            source=item.source,
        )
    return {"ok": True, "upserted": len(body.items)}


@router.get("/chunks")
async def get_chunks(limit: int = Query(default=100, ge=1, le=1000)):
    return model.list_chunks(limit=limit)


@router.post("/feedback", response_model=schemas.IdResponse)
async def create_feedback(body: schemas.FeedbackCreateInput):
    row_id = model.insert_feedback(
        doc_id=body.doc_id,
        chunk_id=body.chunk_id,
        feedback_value=body.feedback_value,
        query_text=body.query_text,
        mode=body.mode,
        use_qe=body.use_qe,
        use_qe_judge=body.use_qe_judge,
        notes=body.notes,
    )
    return {"id": row_id}


@router.get("/feedback")
async def get_feedback(limit: int = Query(default=100, ge=1, le=1000)):
    return model.list_feedback(limit=limit)
