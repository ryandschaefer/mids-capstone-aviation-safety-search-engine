import asyncio
import polars as pl
import src.models.search as model
import src.models.cache as cache
import src.models.data as data
import src.models.db as db
import src.schemas.search as schemas
from src.controllers.bedrock import query_expansion, judge_relevance
from collections import defaultdict
import time
from fastapi.responses import StreamingResponse
import io

async def get_test_data():
    # Return the top 15 records
    df = await data.get_sample_data()
    return df.to_dicts()

async def retrieve_docs(query: str, top_k: int, mode: str, times: defaultdict[str, float]) -> pl.DataFrame:
    service_names: list[str] = []
    service_list = []
    
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
    times["retrieval"] += time.time() - retrieval_start
    
    synthesis_start = time.time()
    # Extract service outputs
    outputs = defaultdict(pl.DataFrame)
    for name, results in zip(service_names, service_results):
        outputs[name] = pl.DataFrame(results["data"])
        times[name] += results["time"]
        
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
    times["synthesis"] += time.time() - synthesis_start
    
    return df_retrieved

async def feedback_approach_1(
    query: str, search_q: str, mode: str, times: defaultdict[str, float],
    init_pool: int = 100, k_increment: int = 50, max_pool: int = 5_000,
    precision_threshold: float = 0.5
) -> tuple[pl.DataFrame, int]:
    """
    Precision-based expansion loop — collect judge-confirmed relevant docs only.
    Keeps fetching in increments of A1_K_INCREMENT until A1_TARGET_K relevant docs
    are collected or precision in the latest batch drops below A1_THRESHOLD.
    Irrelevant documents are discarded; the return list contains only relevant docs.
    """
    current_pool  = min(init_pool, max_pool)
    relevant_cache = {}
    relevant_docs = []
    all_docs = []
    num_iters = 0

    while current_pool == init_pool or current_pool <= max_pool:
        print(f"\nStarting iteration { num_iters+1 }. Retrieving { current_pool } chunks...")
        # Retrieve a new set of documents
        df_ranked = await retrieve_docs(search_q, current_pool, mode, times)
        if all_docs:
            df_batch = df_ranked.filter(~pl.col("doc_id").is_in(all_docs))
        else:
            df_batch = df_ranked
        new_batch = df_batch["doc_id"].unique().to_list()
        # Stop if no new records returned
        if not new_batch:
            break

        judge_start = time.time()
        # Get narratives for the new batch of documents
        df_narratives = await db.get_narratives(new_batch)
        # Judge relevant documents and compute precision
        judge_results = await asyncio.gather(*[
            judge_relevance(query, row["doc_id"], row["narrative"], relevant_cache) 
            for row in df_narratives.iter_rows(named = True)
        ])
        df_narratives = df_narratives.with_columns(
            pl.Series("is_relevant", judge_results)
        )
        times["llm_judge"] += time.time() - judge_start
        
        batch_relevant = df_narratives.filter(pl.col("is_relevant") == True)["doc_id"].to_list()
        precision = len(batch_relevant) / len(new_batch)
        print(f"{ len(batch_relevant) }/{ len(new_batch) } documents are relevant. Precision = {precision:.3f}")
        # Only keep relevant docs
        relevant_docs.extend(batch_relevant)
        num_iters += 1

        # Break early if precision drops below threshold
        if precision < precision_threshold:
            print(f"Precision is below the treshold of { precision_threshold }. Stopping prematurely")
            break
        
        # Prep for next iteration
        all_docs.extend(new_batch)
        current_pool += k_increment

    # Return all relevant documents
    return df_ranked.filter(pl.col("doc_id").is_in(relevant_docs)), num_iters

async def start_search(
    query: str, top_k: int, mode: str, 
    use_qe: bool = False, use_qe_judge: bool = False, 
    use_feedback_1: bool = False
) -> schemas.StartSearchOutput:
    start = time.time()
    times = defaultdict(float)
    
    # Check if the search has been cached
    cache_start = time.time()
    search_params = {
        "query": query,
        "top_k": top_k,
        "mode": mode,
        "use_qe": use_qe,
        "use_qe_judge": use_qe_judge,
        "use_feedback_1": use_feedback_1
    }
    cache_key = cache.create_key(search_params)
    cache_value = await cache.get_cache(cache_key)
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
        search_query = await query_expansion(query, use_judge = use_qe_judge)
        times["query_expansion"] = time.time() - qe_start
    else:
        search_query = query
    
    num_iters = None
    if use_feedback_1:
        loop_start = time.time()
        df_retrieved, num_iters = await feedback_approach_1(query, search_query, mode, times, max_pool=top_k)
        times["feedback_loop"] = time.time() - loop_start
    else:
        df_retrieved = await retrieve_docs(query, top_k, mode, times)
    
    # Cache the results
    cache_write_start = time.time()
    data = df_retrieved.to_dicts()
    await cache.set_cache(cache_key, data)
    times["cache_write"] = time.time() - cache_write_start
        
    # Return the results
    times["api_total"] = time.time() - start
    return {
        "cache_key": cache_key,
        "cached": False,
        "total_results": len(data),
        "used_queries": [query],
        "times": times,
        "feedback_iterations": num_iters
    }
    
# Retrieve cached results from s3
async def retrieve_page(
    cache_key: str, paginate: bool, page: int = 0, page_length: int = 10, 
    metadata_filters: dict[str, schemas.FilterInput] | None = None
) -> tuple[pl.DataFrame, int, dict[str, float]]:
    start_time = time.time()
    times = defaultdict(float)
    
    # Get data from the cache
    # and apply metadata filters in parallel
    cache_data, df_metadata = await asyncio.gather(cache.get_cache(cache_key), data.get_metadata_filters(metadata_filters))
    times["cache_plus_metadata"] = time.time() - start_time
    
    # Check that the cache key exists and is not expired
    if cache_data is None:
        raise Exception(f"The search with the key `{cache_key}` either does not exist or has expired")
    
    paginate_start = time.time()
    # Join with metadata filters
    df_data = pl.DataFrame(cache_data)
    if df_metadata is not None:
        df_data = df_data.join(df_metadata, left_on = "doc_id", right_on = "acn_num_ACN")
        
    # Extract the page of results
    df_page = df_data.sort("score", descending = True)
    if paginate:
        df_page = df_page.slice(page*page_length, page_length)
    times["filter_plus_paginate"] = time.time() - paginate_start
    
    retrieve_start = time.time()
    # Get the raw records matching the results and 
    doc_ids = df_page["doc_id"].to_list()
    chunk_ids = df_page["chunk_id"].to_list()
    df_records, df_chunks = await asyncio.gather(data.get_records_by_id(doc_ids), db.get_relevant_chunks(doc_ids, chunk_ids))
    assert len(df_page) == len(df_records)
    assert len(df_page) == len(df_chunks)
    times["retrieval"] = time.time() - retrieve_start
    
    join_start = time.time()
    # Join result information with raw records and chunk text
    df = df_records \
        .join(
            df_page,
            left_on = "acn_num_ACN",
            right_on = "doc_id",
            validate = "1:1"
        ) \
        .join(
            df_chunks,
            left_on = "acn_num_ACN",
            right_on = "doc_id",
            validate = "1:1"
        ) \
        .sort("score", descending=True) \
        .drop(["chunk_id"], strict = False)
    assert len(df) == len(df_page)
    times["joins"] = time.time() - join_start
    times["api_total"] = time.time() - start_time
    
    return df, len(df_data), times
    
# Retrieve a page of results for a search from the cache
async def retrieve_results(
    cache_key: str, page: int, page_length: int, 
    metadata_filters: dict[str, schemas.FilterInput] | None = None
) -> list[dict]:
    # Retrieve a page of results from s3
    df, total_results, times = await retrieve_page(cache_key, True, page, page_length, metadata_filters)
    
    records = df.to_dicts()
    return {
        "total_results": total_results,
        "times": times,
        "data": records
    }
    
# Download cached results as a csv
async def download_results(cache_key: str, metadata_filters: dict[str, schemas.FilterInput] | None = None) -> StreamingResponse:
    # Retreive all results from s3
    df, _, _ = await retrieve_page(cache_key, False, metadata_filters=metadata_filters)
    
    # Drop irrelevant columns
    df = df.drop(["score", "chunk_id", "chunks"], strict = False)
    
    # Write csv of results to buffer
    buffer = io.BytesIO()
    df.write_csv(buffer)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=results.csv"}
    )