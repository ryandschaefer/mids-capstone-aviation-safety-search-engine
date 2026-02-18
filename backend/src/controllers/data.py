from datasets import load_dataset
import models.bm25_service as bm25
import models.semantic_service as semantic
import models.hybrid_service as hybrid
import polars as pl
from pathlib import Path

# Load HuggingFace dataset
ds = load_dataset("elihoole/asrs-aviation-reports")
df: pl.DataFrame = ds["train"].to_polars()
work = df.to_dicts()

# Load BM25 index
bm25.init(work)

# Load Semantic index (will be built if doesn't exist)
# Note: Set force_rebuild=True to rebuild index with different model
semantic_index_path = Path(__file__).parent.parent / "models" / "semantic_index.pkl"
try:
    semantic.init(work, index_path=str(semantic_index_path), force_rebuild=False)
    semantic_enabled = True
    print("Semantic search enabled")
except Exception as e:
    print(f"Semantic search disabled: {e}")
    semantic_enabled = False

# Initialize hybrid search if semantic is available
if semantic_enabled:
    try:
        hybrid.init(
            bm25_service=bm25,
            semantic_service=semantic,
            fusion_type="linear",  # or "rrf"
            alpha=0.5,  # Tune this based on evaluation
            normalization="min_max",
            retrieve_k=100
        )
        hybrid_enabled = True
        print("Hybrid search enabled")
    except Exception as e:
        print(f"Hybrid search disabled: {e}")
        hybrid_enabled = False
else:
    hybrid_enabled = False

def get_test_data():
    # Return the top 15 records
    return df[:15].to_dicts()

def get_bm25_data(query: str):
    # Search with BM25
    df_bm25 = pl.DataFrame(bm25.search(query, 50)) \
        .select(["score", "parent_doc_id"]) \
        .unique("parent_doc_id", keep = "first")
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

def get_semantic_data(query: str, top_k: int = 50):
    """Search using semantic (dense) retrieval only."""
    if not semantic_enabled:
        return {"error": "Semantic search not available. Run model building first."}

    # Search with semantic model
    df_semantic = pl.DataFrame(semantic.search(query, top_k)) \
        .select(["score", "parent_doc_id"]) \
        .unique("parent_doc_id", keep = "first")

    # Cross reference IDs with original dataset
    df_results = df \
        .join(
            df_semantic,
            left_on = "acn_num_ACN",
            right_on = "parent_doc_id"
        ) \
        .sort("score", descending=True)

    return df_results.to_dicts()

def get_hybrid_data(query: str, top_k: int = 50, alpha: float = None):
    """
    Search using hybrid retrieval (BM25 + Semantic).

    Args:
        query: Search query
        top_k: Number of results to return
        alpha: BM25 weight (0=semantic only, 1=BM25 only). If None, uses default.

    Returns:
        List of search results with hybrid scores
    """
    if not hybrid_enabled:
        return {"error": "Hybrid search not available. Ensure semantic index is built."}

    # Search with hybrid model
    hybrid_results = hybrid.search(query, top_k, alpha=alpha)

    if not hybrid_results:
        return []

    # Extract parent_doc_ids and scores
    df_hybrid = pl.DataFrame(hybrid_results) \
        .select(["score", "parent_doc_id", "bm25_score", "semantic_score"]) \
        .unique("parent_doc_id", keep = "first")

    # Cross reference with original dataset
    df_results = df \
        .join(
            df_hybrid,
            left_on = "acn_num_ACN",
            right_on = "parent_doc_id"
        ) \
        .sort("score", descending=True)

    return df_results.to_dicts()