import asyncio
from datasets import load_dataset
import polars as pl
import src.models.search as model

# Load HuggingFace dataset
ds = load_dataset("elihoole/asrs-aviation-reports")
df: pl.DataFrame = ds["train"].to_polars()

async def get_test_data():
    # Return the top 15 records
    return df[:15].to_dicts()

async def start_search(query: str):
    # Define list of services to run
    service_list = [
        model.get_bm25_results(query)
    ]
    # Wait for all services to execute
    service_results = await asyncio.gather(*service_list)
    
    # Extract BM25 from results
    df_bm25 = pl.DataFrame(service_results[0])
    
    # Cross reference IDs with original dataset
    df_results = df \
        .join(
            df_bm25,
            left_on = "acn_num_ACN",
            right_on = "parent_doc_id"
        ) \
        .sort("score", descending=True)
        
    # Return the results
    return df_results.to_dicts()