import src.models.bm25_service as bm25
import polars as pl
import time

# Load BM25 index
bm25.init()

# Check if the bm25 index has been loaded
def is_index_loaded() -> bool:
    return bm25.bm25 is not None

async def get_bm25_data(query: str, top_k: int = 50):
    start = time.time()
    # Search with BM25
    df_bm25 = pl.DataFrame(bm25.search(query, top_k)) \
        .select(["score", "doc_id", "chunk_id"]) \
        .group_by("doc_id") \
        .agg(
            chunk_id = pl.col("chunk_id"),
            score = pl.col("score").max()
        ) \
        .sort("score", descending=True)
    # Return the results
    data = df_bm25.to_dicts()
    results = {
        "data": data,
        "time": time.time() - start
    }
    
    return results