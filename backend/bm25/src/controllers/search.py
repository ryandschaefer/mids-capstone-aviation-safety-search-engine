import src.models.bm25_service as bm25
import polars as pl

# Load BM25 index
bm25.init()

async def get_bm25_data(query: str, top_k: int = 50):
    # Search with BM25
    df_bm25 = pl.DataFrame(bm25.search(query, top_k)) \
        .select(["score", "parent_doc_id"]) \
        .sort("score", descending=True) \
        .unique("parent_doc_id", keep = "first")
    # Return the results
    return df_bm25.to_dicts()