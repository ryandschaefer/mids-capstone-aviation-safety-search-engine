import asyncio
import polars as pl
import src.models.search as model
import src.models.cache as cache
import src.models.data as data
import src.schemas.search as schemas
from src.controllers.bedrock import query_expansion
from collections import defaultdict
import time

async def get_test_data():
    # Return the top 15 records
    df = await data.get_sample_data()
    return df.to_dicts()

async def start_search(query: str, top_k: int, mode: str, use_qe: bool = False, use_qe_judge: bool = False) -> schemas.StartSearchOutput:
    start = time.time()
    service_names: list[str] = []
    service_list = []
    times = defaultdict(float)
    
    # Check if the search has been cached
    cache_start = time.time()
    search_params = {
        "query": query,
        "mode": mode,
        "use_qe": use_qe,
        "use_qe_judge": use_qe_judge
    }
    cache_key = cache.create_key(search_params)
    cache_value = cache.get_cache(cache_key)
    if cache_value:
        times["cache_read"] = time.time() - cache_start
        times["api_total"] = time.time() - start
        return {
            "cache_key": cache_key,
            "cached": True,
            "total_results": len(cache_value),
            "times": times,
            "used_queries": []
        }
    else:
        times["cache_read"] = time.time() - cache_start
    
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
            .rename({ "score": "bm25_score", "chunk_id": "bm25_chunk_id" }) \
            .with_row_index(name = "bm25_rank", offset = 1) \
            .join(
                outputs["embeddings"] \
                    .rename({ "score": "embedding_score", "chunk_id": "embedding_chunk_id" }) \
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
                ),
                chunk_id = pl.concat_list(["bm25_chunk_id", "embedding_chunk_id"]).list.unique()
            ) \
            .select(["doc_id", "chunk_id", "score"])
    else:
        # Use bm25 or embedding results
        df_retrieved = pl.concat(
            [ outputs["bm25"], outputs["embeddings"] ],
            how = "diagonal_relaxed"
        )
    
    # Cross reference IDs with original dataset
    # df_results = df \
    #     .join(
    #         df_retrieved,
    #         left_on = "acn_num_ACN",
    #         right_on = "doc_id"
    #     ) \
    #     .sort("score", descending=True)
    times["synthesis"] = time.time() - synthesis_start
    
    # Cache the results
    print(df_retrieved)
    data = df_retrieved.to_dicts()
    cache.set_cache(cache_key, data)
        
    # Return the results
    # data = df_results.to_dicts()
    times["api_total"] = time.time() - start
    return {
        # "data": data,
        "cache_key": cache_key,
        "cached": False,
        "total_results": len(data),
        "used_queries": [query],
        "times": times
    }
    
# Retrieve a page of results for a search from the cache
async def retrieve_results(cache_key: str, page: int, page_length: int) -> list[dict]:
    # Check that the cache key exists and is not expired
    cache_data = cache.get_cache(cache_key)
    if cache_data is None:
        raise Exception(f"The search with the key `{cache_key}` either does not exist or has expired")
    
    # Extract the page of results
    start = page * page_length
    end = (page + 1) * page_length
    curr_page = cache_data[start:end]
    df_page = pl.DataFrame(curr_page)
    print(df_page)
    
    # Get the raw records matching the results
    ids = df_page["doc_id"].to_list()
    df_records = await data.get_records_by_id(ids)
    assert len(df_page) == len(df_records)
    
    # Join result information with raw records
    df = df_records \
        .join(
            df_page,
            left_on = "acn_num_ACN",
            right_on = "doc_id"
        ) \
        .sort("score", descending=True)
    assert len(df) == len(df_page)
    
    records = df.to_dicts()
    return records