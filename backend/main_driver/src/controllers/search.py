import asyncio
from datasets import load_dataset
import polars as pl
import src.models.search as model
import src.schemas.search as schemas
from collections import defaultdict
import time

# Load HuggingFace dataset
ds = load_dataset("elihoole/asrs-aviation-reports")
df: pl.DataFrame = pl.concat(
    [ ds[split].to_polars() for split in ["train", "validation", "test"] ], 
    how = "diagonal_relaxed"
)

async def get_test_data():
    # Return the top 15 records
    return df[:15].to_dicts()

async def start_search(query: str, top_k: int, mode: str):
    start = time.time()
    service_names: list[str] = []
    service_list = []
    times = defaultdict(float)
    # Determine which retrieval mode is being used
    if mode == "bm25":
        service_names.extend([
            "bm25"
        ])
        service_list.extend([
            model.get_bm25_results(query, top_k)
        ])
    elif mode == "embeddings":
        service_names.extend([
            "embeddings"
        ])
        service_list.extend([
            model.get_embedding_results(query, top_k)
        ])
    else:
        service_names.extend([
            "bm25",
            "embeddings"
        ])
        service_list.extend([
            model.get_bm25_results(query, top_k),
            model.get_embedding_results(query, top_k)
        ])
        
    # Wait for all services to execute
    service_results: list[schemas.ServiceOutput] = await asyncio.gather(*service_list)
    times["retrieval"] = time.time() - start
    
    synthesis_start = time.time()
    # Extract service outputs
    outputs = defaultdict(pl.DataFrame)
    for name, results in zip(service_names, service_results):
        outputs[name] = pl.DataFrame(results["data"])
        times[name] = results["time"]
        
    if mode == "hybrid":
        # Handle synthesizing hybrid results
        df_retrieved = outputs["bm25"] \
            .rename({ "score": "bm25_score" }) \
            .join(
                outputs["embeddings"] \
                    .rename({ "score": "embedding_score" }),
                on = "doc_id", how = "full", validate = "1:1"
            ) \
            .with_columns(
                score = (1 + pl.col("bm25_score").fill_null(0.0)) * (1 + pl.col("embedding_score").fill_null(0.0))
            )
    else:
        # Use bm25 or embedding results
        df_retrieved = pl.concat(
            [ outputs["bm25"], outputs["embeddings"] ],
            how = "diagonal_relaxed"
        )
    
    # Cross reference IDs with original dataset
    df_results = df \
        .join(
            df_retrieved,
            left_on = "acn_num_ACN",
            right_on = "doc_id"
        ) \
        .sort("score", descending=True)
    times["synthesis"] = time.time() - synthesis_start
        
    # Return the results
    data = df_results.to_dicts()
    times["api_total"] = time.time() - start
    return {
        "data": data,
        "times": times
    }