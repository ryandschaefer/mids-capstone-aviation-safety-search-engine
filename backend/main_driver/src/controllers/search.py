import asyncio
from datasets import load_dataset
import polars as pl
import src.models.search as model
import src.schemas.search as schemas
from src.controllers.bedrock import query_expansion
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

async def start_search(query: str, top_k: int, mode: str, use_qe: bool = False, use_qe_judge: bool = False):
    start = time.time()
    service_names: list[str] = []
    service_list = []
    times = defaultdict(float)
    
    # Use query expansion
    if use_qe:
        qe_start = time.time()
        query = await query_expansion(query, use_judge = use_qe_judge)
        times["query_expansion"] = time.time() - qe_start
    
    # Determine which retrieval mode is being used
    retrieval_start = time.time()
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
    times["retrieval"] = time.time() - retrieval_start
    
    synthesis_start = time.time()
    # Extract service outputs
    outputs = defaultdict(pl.DataFrame)
    for name, results in zip(service_names, service_results):
        outputs[name] = pl.DataFrame(results["data"])
        times[name] = results["time"]
        
    if mode == "hybrid":
        # Handle synthesizing hybrid results
        K = 60
        df_retrieved = outputs["bm25"] \
            .rename({ "score": "bm25_score" }) \
            .with_row_index(name = "bm25_rank", offset = 1) \
            .join(
                outputs["embeddings"] \
                    .rename({ "score": "embedding_score" }) \
                    .with_row_index(name = "embedding_rank", offset = 1),
                on = "doc_id", how = "full", validate = "1:1"
            ) \
            .with_columns(
                pl.col("bm25_rank").fill_null(len(outputs["embeddings"]) + 1),
                pl.col("embedding_rank").fill_null(len(outputs["bm25"]) + 1),
                # score = (1 + pl.col("bm25_score").fill_null(0.0)) * (1 + pl.col("embedding_score").fill_null(0.0))
            ) \
            .with_columns(
                score = (
                    (1 / (pl.col("bm25_rank") + K)) +
                    (1 / (pl.col("embedding_rank") + K))
                )
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
        "used_queries": [query],
        "times": times
    }