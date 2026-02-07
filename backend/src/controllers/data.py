from datasets import load_dataset
import models.bm25_service as bm25
import polars as pl

# Load HuggingFace dataset
ds = load_dataset("elihoole/asrs-aviation-reports")
df: pl.DataFrame = ds["train"].to_polars()

# Load BM25 index
bm25.init(df.to_dicts())

def get_test_data():
    # Return the top 15 records
    return df[:15].to_dicts()

def get_bm25_data(query: str):
    # Search with BM25
    df_bm25 = pl.DataFrame(bm25.search(query, 50)) \
        .select(["score", "parent_doc_id"])
    # Cross reference IDs with original dataset
    df_results = df \
        .join(
            df_bm25,
            left_on = "acn_num_ACN",
            right_on = "parent_doc_id"
        ) \
        .sort("score", descending=True)
    # Return the top 15 records
    return df_results.to_dicts()