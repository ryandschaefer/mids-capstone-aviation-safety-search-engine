"""
Evaluation metrics for information retrieval systems.

Author: Ryan Powers
Project: Aviation Safety Hybrid Retrieval System
Date: February 9, 2026

Metrics implemented:
  - Recall@K: Coverage of relevant documents
  - Precision@K: Quality of top K results
  - Average Precision (AP): Ranking quality per query
  - Mean Average Precision (MAP): Aggregate performance
  - nDCG@K: Normalized ranking quality with position discount
"""

import numpy as np
from typing import List, Set, Dict


def recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """Fraction of relevant docs found in top K."""
    if len(relevant) == 0:
        return 0.0
    retrieved_at_k = set(retrieved[:k])
    hits = retrieved_at_k.intersection(relevant)
    return len(hits) / len(relevant)


def precision_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """Fraction of top K that are relevant."""
    if k == 0:
        return 0.0
    retrieved_at_k = set(retrieved[:k])
    hits = retrieved_at_k.intersection(relevant)
    return len(hits) / k


def average_precision(retrieved: List[str], relevant: Set[str]) -> float:
    """Ranking-aware quality metric for single query."""
    if len(relevant) == 0:
        return 0.0
    
    score = 0.0
    num_hits = 0
    
    for i, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            num_hits += 1
            precision_at_i = num_hits / i
            score += precision_at_i
    
    return score / len(relevant)


def mean_average_precision(
    results: Dict[str, List[str]], 
    relevance: Dict[str, Set[str]]
) -> float:
    """Average of AP across all queries (industry standard)."""
    if len(results) == 0:
        return 0.0
    
    ap_scores = []
    for query_id in results:
        if query_id in relevance:
            ap = average_precision(results[query_id], relevance[query_id])
            ap_scores.append(ap)
    
    return np.mean(ap_scores) if ap_scores else 0.0


def dcg_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """Discounted Cumulative Gain with log discount."""
    dcg = 0.0
    for i, doc_id in enumerate(retrieved[:k], start=1):
        if doc_id in relevant:
            dcg += 1.0 / np.log2(i + 1)
    return dcg


def ndcg_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """Normalized DCG: standard for deep retrieval evaluation."""
    actual_dcg = dcg_at_k(retrieved, relevant, k)
    ideal_retrieved = list(relevant) + [d for d in retrieved if d not in relevant]
    ideal_dcg = dcg_at_k(ideal_retrieved, relevant, k)
    
    if ideal_dcg == 0:
        return 0.0
    return actual_dcg / ideal_dcg


def evaluate_retrieval(
    results: Dict[str, List[str]],
    relevance: Dict[str, Set[str]],
    k_values: List[int] = [10, 50, 100, 1000]
) -> Dict:
    """
    Comprehensive evaluation across all metrics.
    
    Returns dictionary with map, recall, precision, ndcg scores.
    """
    metrics = {
        'map': mean_average_precision(results, relevance),
        'recall': {},
        'precision': {},
        'ndcg': {}
    }
    
    for k in k_values:
        recall_scores = []
        precision_scores = []
        ndcg_scores = []
        
        for qid in results:
            if qid in relevance:
                retrieved = results[qid]
                relevant = relevance[qid]
                
                recall_scores.append(recall_at_k(retrieved, relevant, k))
                precision_scores.append(precision_at_k(retrieved, relevant, k))
                ndcg_scores.append(ndcg_at_k(retrieved, relevant, k))
        
        metrics['recall'][k] = np.mean(recall_scores) if recall_scores else 0.0
        metrics['precision'][k] = np.mean(precision_scores) if precision_scores else 0.0
        metrics['ndcg'][k] = np.mean(ndcg_scores) if ndcg_scores else 0.0
    
    return metrics


if __name__ == "__main__":
    print("✓ retrieval_metrics.py module loaded successfully")
