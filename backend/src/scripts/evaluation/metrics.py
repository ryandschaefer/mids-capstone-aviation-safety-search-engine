# metrics.py
# ---------------------------------------------------------
# Recall-Oriented Evaluation Metrics for Aviation Safety Search
# Implements: Recall@K, MAP, nDCG@K
# ---------------------------------------------------------

import numpy as np
from typing import List, Set, Dict, Callable
from collections import defaultdict

# =========================
# Core Metrics
# =========================

def recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Recall@K: What fraction of relevant documents are in top-K results?

    Critical for safety analysis where missing incidents is costly.

    Args:
        retrieved: List of retrieved document IDs (ordered by rank)
        relevant: Set of relevant document IDs
        k: Cutoff rank

    Returns:
        Recall@K score [0, 1]
    """
    if not relevant:
        return 0.0

    retrieved_at_k = set(retrieved[:k])
    hits = retrieved_at_k & relevant

    return len(hits) / len(relevant)


def precision_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Precision@K: What fraction of top-K results are relevant?

    Args:
        retrieved: List of retrieved document IDs (ordered by rank)
        relevant: Set of relevant document IDs
        k: Cutoff rank

    Returns:
        Precision@K score [0, 1]
    """
    if k == 0:
        return 0.0

    retrieved_at_k = set(retrieved[:k])
    hits = retrieved_at_k & relevant

    return len(hits) / k


def average_precision(retrieved: List[str], relevant: Set[str]) -> float:
    """
    Average Precision (AP): Quality of ranking.

    AP = (1/R) * sum(Precision@k * rel(k))
    Where R = total relevant docs, rel(k) = 1 if doc at rank k is relevant

    Args:
        retrieved: List of retrieved document IDs (ordered by rank)
        relevant: Set of relevant document IDs

    Returns:
        AP score [0, 1]
    """
    if not relevant:
        return 0.0

    num_relevant = len(relevant)
    score = 0.0
    num_hits = 0

    for i, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            num_hits += 1
            precision_at_i = num_hits / i
            score += precision_at_i

    return score / num_relevant


def mean_average_precision(results: List[tuple]) -> float:
    """
    Mean Average Precision (MAP): Average AP across multiple queries.

    Args:
        results: List of (retrieved, relevant) tuples for each query

    Returns:
        MAP score [0, 1]
    """
    if not results:
        return 0.0

    ap_scores = [average_precision(retr, rel) for retr, rel in results]
    return np.mean(ap_scores)


def dcg_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Discounted Cumulative Gain at K.

    DCG@K = sum(rel(i) / log2(i + 1))
    Where rel(i) = 1 if doc at rank i is relevant, 0 otherwise

    Args:
        retrieved: List of retrieved document IDs
        relevant: Set of relevant document IDs
        k: Cutoff rank

    Returns:
        DCG@K score
    """
    dcg = 0.0
    for i, doc_id in enumerate(retrieved[:k], start=1):
        if doc_id in relevant:
            dcg += 1.0 / np.log2(i + 1)

    return dcg


def ndcg_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Normalized Discounted Cumulative Gain at K.

    nDCG@K = DCG@K / IDCG@K
    Where IDCG@K is the ideal DCG (all relevant docs at top ranks)

    Args:
        retrieved: List of retrieved document IDs
        relevant: Set of relevant document IDs
        k: Cutoff rank

    Returns:
        nDCG@K score [0, 1]
    """
    dcg = dcg_at_k(retrieved, relevant, k)

    # Ideal DCG: all relevant docs at top ranks
    ideal_retrieved = list(relevant) + [None] * k  # Fill with None if needed
    idcg = dcg_at_k(ideal_retrieved, relevant, k)

    if idcg == 0:
        return 0.0

    return dcg / idcg


# =========================
# Evaluation Runner
# =========================

class RetrievalEvaluator:
    """
    Evaluates retrieval systems using recall-oriented metrics.

    Based on project requirements:
    - Focus on recall (finding ALL relevant incidents)
    - Use deep metrics (k up to 1000)
    - Compare BM25, Semantic, and Hybrid approaches
    """

    def __init__(self, k_values: List[int] = [10, 20, 50, 100, 1000]):
        """
        Initialize evaluator.

        Args:
            k_values: List of k values for Recall@K and nDCG@K
        """
        self.k_values = k_values

    def evaluate_query(
        self,
        retrieved: List[str],
        relevant: Set[str]
    ) -> Dict[str, float]:
        """
        Evaluate a single query.

        Args:
            retrieved: List of retrieved document IDs (ordered by rank)
            relevant: Set of relevant document IDs

        Returns:
            Dictionary of metric scores
        """
        metrics = {}

        # Recall@K for each k
        for k in self.k_values:
            metrics[f"recall@{k}"] = recall_at_k(retrieved, relevant, k)

        # Precision@K for each k
        for k in self.k_values:
            metrics[f"precision@{k}"] = precision_at_k(retrieved, relevant, k)

        # nDCG@K for each k
        for k in self.k_values:
            metrics[f"ndcg@{k}"] = ndcg_at_k(retrieved, relevant, k)

        # Average Precision (for MAP calculation)
        metrics["ap"] = average_precision(retrieved, relevant)

        return metrics

    def evaluate_system(
        self,
        queries: List[str],
        relevant_sets: List[Set[str]],
        retrieval_fn: Callable[[str, int], List[str]],
        max_k: int = 1000
    ) -> Dict[str, float]:
        """
        Evaluate a retrieval system across multiple queries.

        Args:
            queries: List of query strings
            relevant_sets: List of relevant document sets (one per query)
            retrieval_fn: Function that takes (query, k) and returns list of doc IDs
            max_k: Maximum k to retrieve

        Returns:
            Dictionary of averaged metric scores
        """
        all_metrics = defaultdict(list)

        for query, relevant in zip(queries, relevant_sets):
            # Retrieve top max_k results
            retrieved = retrieval_fn(query, max_k)

            # Evaluate this query
            query_metrics = self.evaluate_query(retrieved, relevant)

            # Accumulate metrics
            for metric_name, score in query_metrics.items():
                all_metrics[metric_name].append(score)

        # Aggregate metrics (mean across queries)
        aggregated = {}
        for metric_name, scores in all_metrics.items():
            if metric_name == "ap":
                # MAP is the mean of AP scores
                aggregated["map"] = np.mean(scores)
            else:
                # Average other metrics
                aggregated[metric_name] = np.mean(scores)

        # Add number of queries evaluated
        aggregated["num_queries"] = len(queries)

        return aggregated

    def compare_systems(
        self,
        queries: List[str],
        relevant_sets: List[Set[str]],
        systems: Dict[str, Callable[[str, int], List[str]]],
        max_k: int = 1000
    ) -> Dict[str, Dict[str, float]]:
        """
        Compare multiple retrieval systems.

        Args:
            queries: List of query strings
            relevant_sets: List of relevant document sets
            systems: Dict of {system_name: retrieval_fn}
            max_k: Maximum k to retrieve

        Returns:
            Dict of {system_name: metrics}
        """
        results = {}

        for system_name, retrieval_fn in systems.items():
            print(f"Evaluating {system_name}...")
            results[system_name] = self.evaluate_system(
                queries,
                relevant_sets,
                retrieval_fn,
                max_k
            )

        return results

    def print_comparison(
        self,
        results: Dict[str, Dict[str, float]],
        metrics_to_show: List[str] = None
    ):
        """
        Print comparison table.

        Args:
            results: Output from compare_systems()
            metrics_to_show: List of metrics to display (None = all)
        """
        if not results:
            print("No results to display")
            return

        # Get all metric names
        system_names = list(results.keys())
        all_metrics = set()
        for metrics in results.values():
            all_metrics.update(metrics.keys())

        # Filter metrics if specified
        if metrics_to_show:
            all_metrics = [m for m in all_metrics if m in metrics_to_show]
        else:
            # Default: show key metrics
            priority_metrics = ["map", "recall@10", "recall@100", "recall@1000",
                              "ndcg@10", "ndcg@100", "ndcg@1000"]
            all_metrics = [m for m in priority_metrics if m in all_metrics]

        # Print header
        print(f"\n{'Metric':<20}", end="")
        for name in system_names:
            print(f"{name:<15}", end="")
        print()
        print("-" * (20 + 15 * len(system_names)))

        # Print each metric
        for metric in all_metrics:
            print(f"{metric:<20}", end="")
            for name in system_names:
                score = results[name].get(metric, 0.0)
                if isinstance(score, float):
                    print(f"{score:.4f}         ", end="")
                else:
                    print(f"{score:<15}", end="")
            print()


# =========================
# Utility Functions
# =========================

def results_to_doc_ids(results: List[Dict], id_key: str = "parent_doc_id") -> List[str]:
    """
    Extract document IDs from search results.

    Args:
        results: List of search result dicts
        id_key: Key to extract ID from

    Returns:
        List of document IDs
    """
    return [r[id_key] for r in results]
