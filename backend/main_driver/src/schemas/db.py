from pydantic import BaseModel, Field, field_validator


class ChunkUpsertInput(BaseModel):
    doc_id: str = Field(min_length=1)
    chunk_id: int = Field(ge=0)
    chunk_text: str = Field(min_length=1)
    source: str | None = None


class ChunkBulkUpsertInput(BaseModel):
    items: list[ChunkUpsertInput] = Field(default_factory=list)


class FeedbackCreateInput(BaseModel):
    doc_id: str = Field(min_length=1)
    feedback_value: str
    chunk_id: int | None = Field(default=None, ge=0)
    query_text: str | None = None
    mode: str | None = None
    use_qe: bool = False
    use_qe_judge: bool = False
    notes: str | None = None

    @field_validator("feedback_value")
    @classmethod
    def validate_feedback_value(cls, value: str) -> str:
        if value not in {"up", "down"}:
            raise ValueError("feedback_value must be either 'up' or 'down'")
        return value


class IdResponse(BaseModel):
    id: int
