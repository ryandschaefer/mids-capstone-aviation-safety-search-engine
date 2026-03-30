from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, Any
import json

class FilterConstraint(BaseModel):
    matchMode: str
    value: Any

class FilterInput(BaseModel):
    operator: str
    constraints: list[FilterConstraint]
    
    @field_validator("operator")
    @classmethod
    def is_valid_operator(cls, value: str) -> str:
        valid_operators = ["and", "or"]
        if value.lower() in ["and", "or"]:
            return value
        else:
            raise ValueError(f"`{ value }` is not a valid retrieval mode. Choose one of these valid options: " + ", ".join(valid_operators))

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
    
    @model_validator(mode="before")
    @classmethod
    def parse_metadata_filters(cls, values):
        mf = values.get("metadata_filters")
        if isinstance(mf, str):
            try:
                values["metadata_filters"] = json.loads(mf)
            except json.JSONDecodeError as e:
                raise ValueError(f"metadata_filters is not valid JSON: {e}")
        return values
    
class RetrieveSearchOutput(BaseModel):
    total_results: int
    data: list[dict]