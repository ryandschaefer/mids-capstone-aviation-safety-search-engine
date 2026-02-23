import src.models.bm25_service as bm25
import polars as pl
import time

# Load BM25 index
bm25.init()

async def get_bm25_data(query: str, top_k: int = 50):
    start = time.time()
    # Search with BM25
    df_bm25 = pl.DataFrame(bm25.search(query, top_k)) \
        .select(["score", "doc_id"]) \
        .sort("score", descending=True) \
        .unique("doc_id", keep = "first")
    # Return the results
    data = df_bm25.to_dicts()
    results = {
        "data": data,
        "time": time.time() - start
    }
    
    return results