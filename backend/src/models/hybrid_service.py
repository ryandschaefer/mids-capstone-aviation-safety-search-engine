# hybrid_service.py
# ---------------------------------------------------------
# Hybrid Retrieval Service (BM25 + Semantic)
# Implements score fusion for recall-oriented safety search
# ---------------------------------------------------------

import numpy as np
from typing import List, Dict, Optional
from collections import defaultdict

# =========================
# Score Normalization
# =========================

def min_max_normalize(scores: List[float]) -> List[float]:
    """
    Min-max normalization to [0, 1] range.

    Handles edge cases:
    - All scores equal: returns all 1.0
    - Empty list: returns empty list
    """
    if not scores:
        return []

    min_score = min(scores)
    max_score = max(scores)

    if max_score == min_score:
        return [1.0] * len(scores)

    return [(s - min_score) / (max_score - min_score) for s in scores]


def rank_normalize(scores: List[float]) -> List[float]:
    """
    Rank-based normalization.

    Converts scores to ranks (1 = best), then normalizes.
    More robust to score scale differences than min-max.
    """
    if not scores:
        return []

    # Create (score, index) pairs and sort
    indexed_scores = [(s, i) for i, s in enumerate(scores)]
    indexed_scores.sort(reverse=True, key=lambda x: x[0])

    # Assign ranks (1-based)
    ranks = [0] * len(scores)
    for rank, (score, idx) in enumerate(indexed_scores, start=1):
        ranks[idx] = rank

    # Normalize to [0, 1] with rank 1 → score 1.0
    max_rank = len(scores)
    return [(max_rank - r + 1) / max_rank for r in ranks]


# =========================
# Fusion Strategies
# =========================

class HybridFusion:
    """
    Hybrid retrieval combining BM25 (lexical) and semantic (dense) search.

    Based on project requirements:
    - "Dense retrievers can miss weakly relevant documents unless interpolated with BM25"
    - Goal: Maximize recall for safety-critical retrieval
    - Strategy: Normalized linear interpolation of scores
    """

    def __init__(
        self,
        bm25_service,
        semantic_service,
        alpha: float = 0.5,
        normalization: str = "min_max",
        retrieve_k: int = 100
    ):
        """
        Initialize hybrid fusion.

        Args:
            bm25_service: BM25 service instance
            semantic_service: Semantic service instance
            alpha: Weight for BM25 (0 = semantic only, 1 = BM25 only)
            normalization: Score normalization method ("min_max" or "rank")
            retrieve_k: Number of candidates to retrieve from each system before fusion
        """
        self.bm25 = bm25_service
        self.semantic = semantic_service
        self.alpha = alpha
        self.normalization = normalization
        self.retrieve_k = retrieve_k

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict] = None,
        alpha: Optional[float] = None
    ) -> List[Dict]:
        """
        Hybrid search with score fusion.

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional metadata filters
            alpha: Override default alpha for this query

        Returns:
            List of fused results with combined scores
        """
        # Use provided alpha or default
        alpha_value = alpha if alpha is not None else self.alpha

        # Retrieve candidates from both systems
        # Use retrieve_k to get enough candidates for fusion
        bm25_results = self.bm25.search(query, top_k=self.retrieve_k, filters=filters)
        semantic_results = self.semantic.search(query, top_k=self.retrieve_k, filters=filters)

        # Fusion
        fused_results = self._fuse_results(
            bm25_results,
            semantic_results,
            alpha=alpha_value,
            top_k=top_k
        )

        return fused_results

    def _fuse_results(
        self,
        bm25_results: List[Dict],
        semantic_results: List[Dict],
        alpha: float,
        top_k: int
    ) -> List[Dict]:
        """
        Fuse BM25 and semantic results using normalized linear interpolation.

        Formula:
            fused_score = α * norm(BM25_score) + (1-α) * norm(semantic_score)

        Where norm() is the configured normalization function.
        """
        # Build score maps: chunk_id -> score
        bm25_scores = {r["chunk_id"]: r["score"] for r in bm25_results}
        semantic_scores = {r["chunk_id"]: r["score"] for r in semantic_results}

        # Get all unique chunk IDs
        all_chunk_ids = set(bm25_scores.keys()) | set(semantic_scores.keys())

        # Collect scores for normalization
        bm25_score_list = [bm25_scores.get(cid, 0.0) for cid in all_chunk_ids]
        semantic_score_list = [semantic_scores.get(cid, 0.0) for cid in all_chunk_ids]

        # Normalize scores
        if self.normalization == "rank":
            bm25_norm = dict(zip(all_chunk_ids, rank_normalize(bm25_score_list)))
            semantic_norm = dict(zip(all_chunk_ids, rank_normalize(semantic_score_list)))
        else:  # min_max
            bm25_norm = dict(zip(all_chunk_ids, min_max_normalize(bm25_score_list)))
            semantic_norm = dict(zip(all_chunk_ids, min_max_normalize(semantic_score_list)))

        # Compute fused scores
        fused_scores = {}
        for chunk_id in all_chunk_ids:
            bm25_n = bm25_norm.get(chunk_id, 0.0)
            semantic_n = semantic_norm.get(chunk_id, 0.0)
            fused_scores[chunk_id] = alpha * bm25_n + (1 - alpha) * semantic_n

        # Build result list with metadata
        # Need to merge metadata from both result sets
        metadata_map = {}
        for r in bm25_results:
            metadata_map[r["chunk_id"]] = r
        for r in semantic_results:
            if r["chunk_id"] not in metadata_map:
                metadata_map[r["chunk_id"]] = r

        # Create fused results
        fused_results = []
        for chunk_id, fused_score in fused_scores.items():
            meta = metadata_map.get(chunk_id, {})
            fused_results.append({
                "chunk_id": chunk_id,
                "score": float(fused_score),
                "bm25_score": bm25_scores.get(chunk_id, 0.0),
                "semantic_score": semantic_scores.get(chunk_id, 0.0),
                "parent_doc_id": meta.get("parent_doc_id", ""),
                "chunk_j": meta.get("chunk_j", 0),
                "when": meta.get("when"),
                "where": meta.get("where"),
                "anomaly": meta.get("anomaly"),
            })

        # Sort by fused score and return top-k
        fused_results.sort(key=lambda x: x["score"], reverse=True)
        return fused_results[:top_k]


class ReciprocalRankFusion:
    """
    Reciprocal Rank Fusion (RRF) - rank-based fusion.

    RRF is more robust to score scale differences and is commonly
    used in production retrieval systems.

    Formula:
        RRF_score = sum(1 / (k + rank_i))

    Where k is a constant (typically 60) and rank_i is the rank in system i.
    """

    def __init__(
        self,
        bm25_service,
        semantic_service,
        k: int = 60,
        retrieve_k: int = 100
    ):
        """
        Initialize RRF fusion.

        Args:
            bm25_service: BM25 service instance
            semantic_service: Semantic service instance
            k: RRF constant (typically 60)
            retrieve_k: Number of candidates to retrieve from each system
        """
        self.bm25 = bm25_service
        self.semantic = semantic_service
        self.k = k
        self.retrieve_k = retrieve_k

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search using Reciprocal Rank Fusion.
        """
        # Retrieve candidates from both systems
        bm25_results = self.bm25.search(query, top_k=self.retrieve_k, filters=filters)
        semantic_results = self.semantic.search(query, top_k=self.retrieve_k, filters=filters)

        # Build rank maps: chunk_id -> rank (1-based)
        bm25_ranks = {r["chunk_id"]: idx + 1 for idx, r in enumerate(bm25_results)}
        semantic_ranks = {r["chunk_id"]: idx + 1 for idx, r in enumerate(semantic_results)}

        # Get all unique chunk IDs
        all_chunk_ids = set(bm25_ranks.keys()) | set(semantic_ranks.keys())

        # Compute RRF scores
        rrf_scores = {}
        for chunk_id in all_chunk_ids:
            rrf_score = 0.0
            if chunk_id in bm25_ranks:
                rrf_score += 1.0 / (self.k + bm25_ranks[chunk_id])
            if chunk_id in semantic_ranks:
                rrf_score += 1.0 / (self.k + semantic_ranks[chunk_id])
            rrf_scores[chunk_id] = rrf_score

        # Build metadata map
        metadata_map = {}
        for r in bm25_results:
            metadata_map[r["chunk_id"]] = r
        for r in semantic_results:
            if r["chunk_id"] not in metadata_map:
                metadata_map[r["chunk_id"]] = r

        # Create fused results
        fused_results = []
        for chunk_id, rrf_score in rrf_scores.items():
            meta = metadata_map.get(chunk_id, {})
            fused_results.append({
                "chunk_id": chunk_id,
                "score": float(rrf_score),
                "bm25_rank": bm25_ranks.get(chunk_id, None),
                "semantic_rank": semantic_ranks.get(chunk_id, None),
                "parent_doc_id": meta.get("parent_doc_id", ""),
                "chunk_j": meta.get("chunk_j", 0),
                "when": meta.get("when"),
                "where": meta.get("where"),
                "anomaly": meta.get("anomaly"),
            })

        # Sort by RRF score and return top-k
        fused_results.sort(key=lambda x: x["score"], reverse=True)
        return fused_results[:top_k]


# =========================
# Service API
# =========================

hybrid_fusion = None

def init(
    bm25_service,
    semantic_service,
    fusion_type: str = "linear",
    alpha: float = 0.5,
    normalization: str = "min_max",
    rrf_k: int = 60,
    retrieve_k: int = 100
):
    """
    Initialize hybrid search service.

    Args:
        bm25_service: Initialized BM25 service
        semantic_service: Initialized semantic service
        fusion_type: "linear" or "rrf"
        alpha: Weight for BM25 in linear fusion
        normalization: "min_max" or "rank" for linear fusion
        rrf_k: Constant for RRF
        retrieve_k: Candidates to retrieve from each system
    """
    global hybrid_fusion

    if fusion_type == "rrf":
        hybrid_fusion = ReciprocalRankFusion(
            bm25_service=bm25_service,
            semantic_service=semantic_service,
            k=rrf_k,
            retrieve_k=retrieve_k
        )
        print(f"Hybrid search initialized with RRF (k={rrf_k})")
    else:  # linear
        hybrid_fusion = HybridFusion(
            bm25_service=bm25_service,
            semantic_service=semantic_service,
            alpha=alpha,
            normalization=normalization,
            retrieve_k=retrieve_k
        )
        print(f"Hybrid search initialized with linear fusion (α={alpha}, norm={normalization})")

def search(query: str, top_k: int = 10, filters: Optional[Dict] = None, alpha: Optional[float] = None) -> List[Dict]:
    """
    Hybrid search API.
    """
    if hybrid_fusion is None:
        raise RuntimeError("Hybrid search not initialized. Call init().")

    if isinstance(hybrid_fusion, HybridFusion):
        return hybrid_fusion.search(query, top_k, filters, alpha)
    return hybrid_fusion.search(query, top_k, filters)
