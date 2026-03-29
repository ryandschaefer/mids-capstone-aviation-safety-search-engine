from pydantic import BaseModel, field_validator
from typing import Optional, Any

class FilterConstraints(BaseModel):
    matchMode: str
    value: Any

class FilterInput(BaseModel):
    operator: str
    constraints: list[FilterConstraints]

class StartSearchInput(BaseModel):
    query: str
    top_k: int = 50
    mode: str = "bm25"
    use_qe: bool = False
    use_qe_judge: bool = False
    metadata_filters: dict[str, FilterInput] | None = None
    
    @field_validator("mode")
    @classmethod
    def is_valid_mode(cls, value: str) -> str:
        valid_modes = [
            "bm25", "embeddings", "hybrid"
        ]
        if value in valid_modes:
            return value
        else:
            raise ValueError(f"`{ value }` is not a valid retrieval mode. Choose one of these valid options: " + ", ".join(valid_modes))
 
class SearchResult(BaseModel):
    score: float
    doc_id: str
    chunk_id: list[int]
    
class ServiceOutput(BaseModel):
    data: list[SearchResult]
    time: float

class StartSearchOutput(BaseModel):
    cache_key: str
    # data: list[dict]
    cached: bool
    used_queries: Optional[list[str]]
    total_results: int
    times: dict[str, float]
    
class RetrieveSearchInput(BaseModel):
    cache_key: str
    page: int = 1
    page_length: int = 10
    metadata_filters: dict[str, FilterInput] | None = None
    