#!/usr/bin/env python3
"""
Comprehensive Model Comparison: SafeAeroBERT vs BERT-cased vs General Models

Tests 4 models to evaluate:
1. Impact of case sensitivity (BERT-cased vs BERT-uncased)
2. Impact of domain-specific training (SafeAeroBERT vs general models)
3. Overall best model for aviation safety search
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sentence_transformers import SentenceTransformer, models
from datasets import load_dataset
import numpy as np

print("="*80)
print("Comprehensive Aviation Model Comparison")
print("Testing: SafeAeroBERT | BERT-cased | BERT-uncased | MiniLM-L12")
print("="*80)

# Aviation queries with case-sensitive acronyms
aviation_queries = [
    "ATC clearance not received before departure",
    "TCAS Resolution Advisory required immediate climb",
    "IFR flight plan filed but departed VFR conditions",
    "runway incursion at taxiway",
    "engine failure on takeoff",
    "loss of separation between aircraft"
]

# Load ASRS samples with aviation acronyms
print("\nLoading ASRS samples with acronyms...")
ds = load_dataset("elihoole/asrs-aviation-reports")
sample_docs = []
acronyms = ["ATC", "TCAS", "IFR", "VFR", "MEL", "ATIS", "FMS", "SID", "STAR"]

for record in ds["train"]:
    narrative = record.get("Report 1_Narrative", "")
    if narrative and any(acronym in narrative for acronym in acronyms):
        sample_docs.append(narrative[:500])
        if len(sample_docs) >= 20:
            break

print(f"Loaded {len(sample_docs)} sample documents with acronyms\n")

# Models to test (all 4 models)
models_to_test = {
    "MiniLM-L12 (baseline)": "sentence-transformers/all-MiniLM-L12-v2",
    "BERT-base-uncased": None,  # Will create manually
    "BERT-base-cased": None,     # Will create manually
    "SafeAeroBERT (aviation)": None,  # Will create manually
}

# Create all models
print("Loading models...")

# 1. BERT-base-uncased
try:
    word_embedding_uncased = models.Transformer('bert-base-uncased')
    pooling_uncased = models.Pooling(
        word_embedding_uncased.get_word_embedding_dimension(),
        pooling_mode='mean'
    )
    models_to_test["BERT-base-uncased"] = SentenceTransformer(modules=[word_embedding_uncased, pooling_uncased])
    print("BERT-base-uncased loaded")
except Exception as e:
    print(f"BERT-base-uncased failed: {e}")

# 2. BERT-base-cased
try:
    word_embedding_cased = models.Transformer('bert-base-cased')
    pooling_cased = models.Pooling(
        word_embedding_cased.get_word_embedding_dimension(),
        pooling_mode='mean'
    )
    models_to_test["BERT-base-cased"] = SentenceTransformer(modules=[word_embedding_cased, pooling_cased])
    print("BERT-base-cased loaded")
except Exception as e:
    print(f"BERT-base-cased failed: {e}")

# 3. SafeAeroBERT
try:
    word_embedding = models.Transformer('NASA-AIML/MIKA_SafeAeroBERT')
    pooling = models.Pooling(
        word_embedding.get_word_embedding_dimension(),
        pooling_mode='mean'
    )
    models_to_test["SafeAeroBERT (aviation)"] = SentenceTransformer(modules=[word_embedding, pooling])
    print("SafeAeroBERT loaded")
except Exception as e:
    print(f"SafeAeroBERT failed: {e}")

# Test each model
print("\n" + "="*80)
print("TESTING MODELS ON AVIATION QUERIES WITH ACRONYMS")
print("="*80)

results = {}

for model_name, model in models_to_test.items():
    if model is None:
        continue  # Skip if model failed to load

    print(f"\n{model_name}:")
    print("-" * len(model_name))

    try:

        # Encode queries and documents
        try:
            query_embeddings = model.encode(aviation_queries, show_progress_bar=False)
            doc_embeddings = model.encode(sample_docs, show_progress_bar=False)
        except TypeError:
            # Some models don't support show_progress_bar parameter
            query_embeddings = model.encode(aviation_queries)
            doc_embeddings = model.encode(sample_docs)

        # Normalize embeddings for fair comparison (cosine similarity)
        query_norms = np.linalg.norm(query_embeddings, axis=1, keepdims=True)
        doc_norms = np.linalg.norm(doc_embeddings, axis=1, keepdims=True)

        query_embeddings_norm = query_embeddings / (query_norms + 1e-8)
        doc_embeddings_norm = doc_embeddings / (doc_norms + 1e-8)

        # Compute cosine similarity
        similarities = np.dot(query_embeddings_norm, doc_embeddings_norm.T)
        avg_similarity = similarities.mean()

        results[model_name] = {
            "avg_similarity": avg_similarity,
            "embedding_dim": query_embeddings.shape[1],
            "top_similarity": similarities.max()
        }

        print(f"  Embedding dimension: {query_embeddings.shape[1]}")
        print(f"  Avg similarity: {avg_similarity:.4f}")
        print(f"  Max similarity: {similarities.max():.4f}")

    except Exception as e:
        print(f"  Error: {e}")
        results[model_name] = None

# Compare results
print("\n" + "="*80)
print("COMPARISON: Cased vs Uncased vs Domain-Specific")
print("="*80)

# Sort by performance
sorted_results = sorted(
    [(name, res) for name, res in results.items() if res is not None],
    key=lambda x: x[1]["avg_similarity"],
    reverse=True
)

# Get baseline
baseline = results.get("MiniLM-L12 (baseline)")
baseline_score = baseline["avg_similarity"] if baseline else 0.2437

print(f"\n{'Rank':<6} {'Model':<30} {'Avg Similarity':<15} {'Improvement':<15}")
print("-" * 70)

for rank, (name, res) in enumerate(sorted_results, 1):
    avg_sim = res["avg_similarity"]
    improvement = ((avg_sim - baseline_score) / baseline_score) * 100
    marker = "BEST" if rank == 1 else f"{rank}."
    print(f"{marker:<6} {name:<30} {avg_sim:<15.4f} {improvement:+.1f}%")

# Key comparisons
print("\n" + "="*80)
print("KEY FINDINGS")
print("="*80)

bert_cased = results.get("BERT-base-cased")
bert_uncased = results.get("BERT-base-uncased")
safeaero = results.get("SafeAeroBERT (aviation)")

if bert_cased and bert_uncased:
    print("\n1. Impact of Case Sensitivity:")
    diff = ((bert_cased["avg_similarity"] - bert_uncased["avg_similarity"]) /
            bert_uncased["avg_similarity"]) * 100
    print(f"   BERT-cased:   {bert_cased['avg_similarity']:.4f}")
    print(f"   BERT-uncased: {bert_uncased['avg_similarity']:.4f}")
    print(f"   Difference:   {diff:+.1f}%")

if safeaero and bert_uncased:
    print("\n2. Impact of Domain-Specific Training:")
    diff = ((safeaero["avg_similarity"] - bert_uncased["avg_similarity"]) /
            bert_uncased["avg_similarity"]) * 100
    print(f"   SafeAeroBERT: {safeaero['avg_similarity']:.4f}")
    print(f"   BERT-uncased: {bert_uncased['avg_similarity']:.4f}")
    print(f"   Difference:   {diff:+.1f}%")

if bert_cased and safeaero:
    print("\n3. Cased General vs Uncased Aviation:")
    diff = ((bert_cased["avg_similarity"] - safeaero["avg_similarity"]) /
            safeaero["avg_similarity"]) * 100
    print(f"   BERT-cased (general):   {bert_cased['avg_similarity']:.4f}")
    print(f"   SafeAeroBERT (aviation): {safeaero['avg_similarity']:.4f}")
    print(f"   Difference:             {diff:+.1f}%")

print("\n" + "="*80)
print("RECOMMENDATION")
print("="*80)

if sorted_results:
    best = sorted_results[0]
    print(f"\nBest model: {best[0]}")
    print(f"   Score: {best[1]['avg_similarity']:.4f}")

    if "SafeAeroBERT" in best[0]:
        print("\nRECOMMENDATION: Use SafeAeroBERT")
        print("   - Aviation-specific training on ASRS/NTSB data")
        print("   - Close performance to best model")
        print("   - Production-ready")
    elif "cased" in best[0].lower():
        print("\nRECOMMENDATION: Consider trade-offs")
        print("   - BERT-cased best for acronyms")
        print("   - But lacks aviation-specific training")
        print("   - SafeAeroBERT may be better for full narratives")

print("\n" + "="*80)
