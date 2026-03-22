# query_generation.py
# ---------------------------------------------------------
# Synthetic Query Generation for Evaluation
# Uses anomaly labels to create test queries
# ---------------------------------------------------------

import random
from typing import List, Dict, Set, Tuple
from collections import defaultdict, Counter

# =========================
# Anomaly-Based Query Generation
# =========================

def extract_anomaly_queries(dataset, min_docs: int = 5, max_docs: int = 500) -> List[Dict]:
    """
    Generate synthetic queries from anomaly labels.

    Strategy (from project plan):
    - Use anomaly field as query
    - Define relevance using anomaly labels
    - Filter categories with enough but not too many documents

    Args:
        dataset: HuggingFace dataset or list of records
        min_docs: Minimum documents per anomaly to be usable
        max_docs: Maximum documents per anomaly (avoid very common ones)

    Returns:
        List of query dicts with format:
        {
            "query": str,
            "relevant_ids": set of parent_doc_ids,
            "anomaly_label": str
        }
    """
    from models.bm25_service import get_doc_id

    # Build anomaly -> doc_ids mapping
    anomaly_to_docs = defaultdict(set)

    for r in dataset:
        doc_id = get_doc_id(r)
        anomaly = r.get("Events_Anomaly")

        if anomaly:
            # Handle multi-label anomalies (semicolon separated)
            anomaly_labels = [a.strip() for a in str(anomaly).split(";")]
            for label in anomaly_labels:
                if label:
                    anomaly_to_docs[label].add(str(doc_id))

    # Filter anomalies by document count
    valid_anomalies = {
        label: docs
        for label, docs in anomaly_to_docs.items()
        if min_docs <= len(docs) <= max_docs
    }

    print(f"Found {len(valid_anomalies)} valid anomalies")
    print(f"  (between {min_docs} and {max_docs} documents)")

    # Create queries
    queries = []
    for label, relevant_ids in valid_anomalies.items():
        queries.append({
            "query": label,
            "relevant_ids": relevant_ids,
            "anomaly_label": label,
            "num_relevant": len(relevant_ids)
        })

    # Sort by number of relevant docs for easy analysis
    queries.sort(key=lambda x: x["num_relevant"])

    return queries


def sample_balanced_queries(
    queries: List[Dict],
    n_queries: int = 50,
    strategy: str = "stratified"
) -> List[Dict]:
    """
    Sample a balanced set of queries.

    Args:
        queries: Full list of queries
        n_queries: Number of queries to sample
        strategy: Sampling strategy
            - "stratified": Sample across different sizes
            - "random": Random sample
            - "diverse": Sample maximally diverse queries

    Returns:
        Sampled queries
    """
    if len(queries) <= n_queries:
        return queries

    if strategy == "stratified":
        # Split into buckets by num_relevant
        buckets = defaultdict(list)
        for q in queries:
            bucket_idx = int(np.log10(q["num_relevant"]) * 10)
            buckets[bucket_idx].append(q)

        # Sample proportionally from each bucket
        sampled = []
        queries_per_bucket = max(1, n_queries // len(buckets))

        for bucket in buckets.values():
            n_sample = min(queries_per_bucket, len(bucket))
            sampled.extend(random.sample(bucket, n_sample))

        # Fill remaining slots with random samples
        if len(sampled) < n_queries:
            remaining = [q for q in queries if q not in sampled]
            sampled.extend(random.sample(remaining, min(n_queries - len(sampled), len(remaining))))

        return sampled[:n_queries]

    else:  # random
        return random.sample(queries, n_queries)


# =========================
# Handwritten Query Templates
# =========================

SAFETY_SCENARIO_TEMPLATES = [
    # Altitude deviations
    "altitude crossing restriction not met",
    "descended below minimum altitude",
    "climbed through assigned altitude",

    # Communication issues
    "misunderstood clearance from ATC",
    "radio frequency congestion",
    "lost communication with tower",

    # Traffic conflicts
    "TCAS resolution advisory",
    "close proximity to other aircraft",
    "loss of separation",

    # Weather
    "encountered severe turbulence",
    "wake turbulence from preceding aircraft",
    "flight into IMC conditions",

    # Approach and landing
    "unstabilized approach",
    "go-around due to traffic on runway",
    "landing without clearance",

    # Runway incursions
    "crossed hold short line",
    "wrong runway departure",
    "taxiway confusion",

    # System failures
    "autopilot disconnect",
    "navigation system failure",
    "engine failure on takeoff",

    # Human factors
    "crew fatigue factor",
    "distraction in cockpit",
    "task saturation",
]


def create_handwritten_queries(dataset) -> List[Dict]:
    """
    Create queries from handwritten safety scenarios.

    These can be used alongside anomaly-based queries for evaluation.

    Args:
        dataset: HuggingFace dataset

    Returns:
        List of query dicts (without pre-defined relevant sets)
    """
    queries = []
    for template in SAFETY_SCENARIO_TEMPLATES:
        queries.append({
            "query": template,
            "relevant_ids": None,  # To be labeled manually or via search
            "source": "handwritten",
        })

    return queries


# =========================
# Query Augmentation
# =========================

def augment_anomaly_query(anomaly_label: str) -> List[str]:
    """
    Create variations of an anomaly query.

    Useful for testing robustness to query phrasing.

    Args:
        anomaly_label: Original anomaly label

    Returns:
        List of query variations
    """
    # Start with original
    queries = [anomaly_label]

    # Add shortened version (remove redundant words)
    stop_phrases = ["All Types", "Not Specified"]
    shortened = anomaly_label
    for phrase in stop_phrases:
        shortened = shortened.replace(phrase, "").strip()
    shortened = shortened.replace("  ", " ")
    if shortened != anomaly_label and shortened:
        queries.append(shortened)

    # Add first component only (if semicolon separated)
    if ";" in anomaly_label:
        first_component = anomaly_label.split(";")[0].strip()
        if first_component not in queries:
            queries.append(first_component)

    return queries


# =========================
# Relevance Assessment Helpers
# =========================

def build_relevance_sets_from_anomaly(
    dataset,
    anomaly_label: str
) -> Set[str]:
    """
    Build relevance set for an anomaly-based query.

    Args:
        dataset: HuggingFace dataset
        anomaly_label: Anomaly label to match

    Returns:
        Set of relevant document IDs
    """
    from models.bm25_service import get_doc_id

    relevant = set()

    for r in dataset:
        anomaly = r.get("Events_Anomaly")
        if anomaly and anomaly_label in str(anomaly):
            doc_id = get_doc_id(r)
            relevant.add(str(doc_id))

    return relevant


def compute_query_statistics(queries: List[Dict]) -> Dict:
    """
    Compute statistics about query set.

    Args:
        queries: List of query dicts

    Returns:
        Statistics dict
    """
    import numpy as np

    num_relevant = [q["num_relevant"] for q in queries if "num_relevant" in q]

    stats = {
        "num_queries": len(queries),
        "num_with_relevance": len(num_relevant),
        "avg_relevant": float(np.mean(num_relevant)) if num_relevant else 0,
        "median_relevant": float(np.median(num_relevant)) if num_relevant else 0,
        "min_relevant": int(np.min(num_relevant)) if num_relevant else 0,
        "max_relevant": int(np.max(num_relevant)) if num_relevant else 0,
    }

    return stats


# =========================
# Numpy import for stratified sampling
# =========================
import numpy as np
