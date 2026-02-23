from pydantic import BaseModel, field_validator

class StartSearchInput(BaseModel):
    query: str
    top_k: int = 50
    mode: str = "bm25"
    
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
    
class ServiceOutput(BaseModel):
    data: list[dict]
    time: float

class StartSearchOutput(BaseModel):
    # search_hash: str
    data: list[dict]
    times: dict[str, float]
    
class RetrieveSearchInput(BaseModel):
    search_hash: str
    page: int = 1
    page_length: int = 10
    