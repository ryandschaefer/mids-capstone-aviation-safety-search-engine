from pydantic import BaseModel

class ServiceInput(BaseModel):
    query: str
    top_k: int = 50
    
class SearchResult(BaseModel):
    score: float
    doc_id: str
    chunk_id: list[int]
    
class ServiceOutput(BaseModel):
    data: list[SearchResult]
    time: float
    