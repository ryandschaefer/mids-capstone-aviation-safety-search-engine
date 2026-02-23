import src.models.search as model
import polars as pl
import time

# Verify connection to qdrant
def get_qdrant_status():
    # Test qdrant connection
    model.client.info()

async def get_embedding_data(query: str, top_k: int = 50):
    start = time.time()
    # Search with embeddings
    df_embeddings = pl.DataFrame(model.search(query, top_k)) \
        .select(["score", "doc_id"]) \
        .sort("score", descending=True) \
        .unique("doc_id", keep = "first")
    # Return the results
    data = df_embeddings.to_dicts()
    results = {
        "data": data,
        "time": time.time() - start
    }
    
    return results