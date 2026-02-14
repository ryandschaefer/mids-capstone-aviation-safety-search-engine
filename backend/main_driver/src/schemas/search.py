from pydantic import BaseModel

class StartSearchInput(BaseModel):
    query: str
    top_k: int = 10