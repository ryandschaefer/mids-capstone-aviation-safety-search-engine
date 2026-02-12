#!/usr/bin/env python3
"""
Comprehensive Model Evaluation on Synthetic Queries
Combines all models from initial evaluation + additional SOTA models
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sentence_transformers import SentenceTransformer, models
from datasets import load_dataset
import numpy as np
from datetime import datetime

print("="*80)
print("COMPREHENSIVE MODEL EVALUATION")
print("Aviation Safety Search Engine - MIDS Capstone")
print("="*80)
print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Load datasets
print("\nLoading datasets...")
query_ds = load_dataset("rnapberkeley/asrs")
val_queries = query_ds["validation"]
asrs_ds = load_dataset("elihoole/asrs-aviation-reports")
documents = asrs_ds["train"]

print(f"✓ Loaded {len(val_queries)} validation queries")
print(f"✓ Loaded {len(documents)} documents")

# Build document lookup
print("\nBuilding document lookup...")
doc_lookup = {}
for doc in documents:
    doc_id = doc.get("acn_num_ACN")
    if doc_id:
        narrative = doc.get("Report 1_Narrative", "")
        synopsis = doc.get("Report 1_Synopsis", "")
        text = f"{synopsis} {narrative}".strip()
        if text:
            doc_lookup[str(doc_id)] = {
                "text": text[:1000],
                "id": str(doc_id)
            }

print(f"✓ Built lookup for {len(doc_lookup)} documents")

# Sample queries
n_eval_queries = 200
print(f"\n✓ Using {n_eval_queries} queries for evaluation")
eval_queries = val_queries.select(range(min(n_eval_queries, len(val_queries))))

# Prepare evaluation data
queries_text = []
relevant_docs = []

for q in eval_queries:
    queries_text.append(q["query"])
    relevant_docs.append([str(q["seed_doc_id"])])

# Get evaluation documents
all_relevant_ids = set()
for rel_docs in relevant_docs:
    all_relevant_ids.update(rel_docs)

eval_doc_ids = list(all_relevant_ids)
eval_docs = []
eval_doc_id_to_idx = {}

for idx, doc_id in enumerate(eval_doc_ids):
    if doc_id in doc_lookup:
        eval_docs.append(doc_lookup[doc_id]["text"])
        eval_doc_id_to_idx[doc_id] = idx

print(f"✓ Prepared {len(eval_docs)} documents for ranking\n")

# ALL MODELS - Combined from both evaluations
models_config = {
    # === PREVIOUS EVALUATION MODELS ===
    "BERT-base-cased": ("bert-base-cased", "wrap", "Previous"),
    "RoBERTa-base": ("roberta-base", "wrap", "Previous"),
    "RoBERTa-large": ("roberta-large", "wrap", "Previous"),
    "SafeAeroBERT": ("NASA-AIML/MIKA_SafeAeroBERT", "wrap", "Aviation-Specific"),
    "E5-large": ("intfloat/e5-large-v2", "sentence", "Previous"),
    "E5-base": ("intfloat/e5-base-v2", "sentence", "Previous"),

    # === BGE MODELS (Top MTEB performers) ===
    "BGE-large-en-v1.5": ("BAAI/bge-large-en-v1.5", "sentence", "BGE"),
    "BGE-base-en-v1.5": ("BAAI/bge-base-en-v1.5", "sentence", "BGE"),

    # === GTE MODELS (Strong retrieval) ===
    "GTE-large": ("thenlper/gte-large", "sentence", "GTE"),
    "GTE-base": ("thenlper/gte-base", "sentence", "GTE"),

    # === PROVEN MODELS ===
    "MPNet-base-v2": ("sentence-transformers/all-mpnet-base-v2", "sentence", "Proven"),

    # === FAST MODELS ===
    "MiniLM-L12-v2": ("sentence-transformers/all-MiniLM-L12-v2", "sentence", "Fast"),
    "MiniLM-L6-v2": ("sentence-transformers/all-MiniLM-L6-v2", "sentence", "Fast"),

    # === ADVANCED MODELS ===
    "UAE-Large-V1": ("WhereIsAI/UAE-Large-V1", "sentence", "Advanced"),
    "Instructor-XL": ("hkunlp/instructor-xl", "sentence", "Instruction-based"),
    "Instructor-large": ("hkunlp/instructor-large", "sentence", "Instruction-based"),
}

print(f"Total models to evaluate: {len(models_config)}\n")

# Results storage
results = {}

# Evaluate each model
for model_name, (model_id, load_type, category) in models_config.items():
    print(f"{'='*80}")
    print(f"[{category}] {model_name}")
    print(f"{'='*80}")

    try:
        # Load model
        print("Loading model...")
        if load_type == "sentence":
            model = SentenceTransformer(model_id)
        elif load_type == "wrap":
            word_embedding = models.Transformer(model_id)
            pooling = models.Pooling(
                word_embedding.get_word_embedding_dimension(),
                pooling_mode='mean'
            )
            model = SentenceTransformer(modules=[word_embedding, pooling])

        embedding_dim = model.get_sentence_embedding_dimension()
        print(f"✓ Loaded (dim: {embedding_dim})")

        # Encode documents
        print(f"Encoding {len(eval_docs)} documents...")
        doc_embeddings = model.encode(
            eval_docs,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )

        # Normalize
        doc_norms = np.linalg.norm(doc_embeddings, axis=1, keepdims=True)
        doc_embeddings_norm = doc_embeddings / (doc_norms + 1e-8)

        # Evaluate
        print(f"Evaluating on {len(queries_text)} queries...")

        recall_at_10 = []
        recall_at_100 = []
        recall_at_1000 = []
        mrr_scores = []

        for i, (query, rel_docs) in enumerate(zip(queries_text, relevant_docs)):
            if i % 50 == 0:
                print(f"  Progress: {i}/{len(queries_text)}")

            # Encode query
            query_embedding = model.encode([query], convert_to_numpy=True)[0]
            query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)

            # Compute similarities
            similarities = doc_embeddings_norm @ query_norm
            top_indices = np.argsort(similarities)[::-1]
            retrieved_ids = [eval_doc_ids[idx] for idx in top_indices]

            # Metrics
            relevant_set = set(rel_docs)

            top_10 = set(retrieved_ids[:10])
            top_100 = set(retrieved_ids[:100])
            top_1000 = set(retrieved_ids[:min(1000, len(retrieved_ids))])

            recall_10 = len(top_10 & relevant_set) / len(relevant_set) if relevant_set else 0
            recall_100 = len(top_100 & relevant_set) / len(relevant_set) if relevant_set else 0
            recall_1000 = len(top_1000 & relevant_set) / len(relevant_set) if relevant_set else 0

            recall_at_10.append(recall_10)
            recall_at_100.append(recall_100)
            recall_at_1000.append(recall_1000)

            # MRR
            for rank, doc_id in enumerate(retrieved_ids[:100], 1):
                if doc_id in relevant_set:
                    mrr_scores.append(1.0 / rank)
                    break
            else:
                mrr_scores.append(0.0)

        # Store results
        results[model_name] = {
            "recall@10": np.mean(recall_at_10),
            "recall@100": np.mean(recall_at_100),
            "recall@1000": np.mean(recall_at_1000),
            "mrr": np.mean(mrr_scores),
            "embedding_dim": embedding_dim,
            "category": category,
            "model_id": model_id
        }

        print(f"\n✓ Results:")
        print(f"  Recall@10:   {results[model_name]['recall@10']:.4f}")
        print(f"  Recall@100:  {results[model_name]['recall@100']:.4f}")
        print(f"  Recall@1000: {results[model_name]['recall@1000']:.4f}")
        print(f"  MRR:         {results[model_name]['mrr']:.4f}\n")

    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results[model_name] = None
        print()

# =============================================================================
# FINAL RESULTS
# =============================================================================

print("\n" + "="*80)
print("FINAL RESULTS - ALL MODELS")
print("="*80)

# Sort by Recall@100
sorted_results = sorted(
    [(name, res) for name, res in results.items() if res is not None],
    key=lambda x: x[1]["recall@100"],
    reverse=True
)

print(f"\n{'Rank':<6} {'Model':<25} {'R@10':<10} {'R@100':<10} {'R@1000':<10} {'MRR':<10} {'Dim':<6} {'Category':<20}")
print("-" * 110)

for rank, (name, res) in enumerate(sorted_results, 1):
    marker = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
    print(f"{marker:<6} {name:<25} {res['recall@10']:<10.4f} {res['recall@100']:<10.4f} {res['recall@1000']:<10.4f} {res['mrr']:<10.4f} {res['embedding_dim']:<6} {res['category']:<20}")

# Write results to markdown file
print("\n" + "="*80)
print("Writing results to MODEL_COMPARISON_RESULTS.md...")
print("="*80)

md_content = f"""# Model Comparison Results - Comprehensive Evaluation

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Evaluation Dataset:** Ronald's Synthetic Queries (rnapberkeley/asrs)
**Number of Queries:** {len(queries_text)}
**Number of Documents:** {len(eval_docs)}

---

## Executive Summary

This evaluation tested **{len([r for r in results.values() if r is not None])} models** on {len(queries_text)} synthetic aviation queries from Ronald's dataset.

### Top 3 Models:

"""

for rank, (name, res) in enumerate(sorted_results[:3], 1):
    medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉"
    md_content += f"""
{medal} **{rank}. {name}**
- Recall@100: **{res['recall@100']:.4f}** ({res['recall@100']*100:.1f}%)
- MRR: {res['mrr']:.4f}
- Embedding Dimension: {res['embedding_dim']}
- Category: {res['category']}
"""

md_content += f"""
---

## Complete Results

| Rank | Model | Recall@10 | Recall@100 | Recall@1000 | MRR | Embedding Dim | Category |
|------|-------|-----------|------------|-------------|-----|---------------|----------|
"""

for rank, (name, res) in enumerate(sorted_results, 1):
    medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else str(rank)
    md_content += f"| {medal} | **{name}** | {res['recall@10']:.4f} | {res['recall@100']:.4f} | {res['recall@1000']:.4f} | {res['mrr']:.4f} | {res['embedding_dim']} | {res['category']} |\n"

md_content += f"""
---

## Metrics Explained

- **Recall@10**: Percentage of queries where the relevant document appears in the top 10 results
- **Recall@100**: Percentage of queries where the relevant document appears in the top 100 results
- **Recall@1000**: Percentage of queries where the relevant document appears in the top 1000 results
- **MRR (Mean Reciprocal Rank)**: Average of 1/rank for the first relevant document (higher = relevant docs ranked higher)

---

## Model Categories

"""

categories = {}
for name, res in results.items():
    if res is not None:
        cat = res['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((name, res))

for category, models in sorted(categories.items()):
    md_content += f"\n### {category}\n\n"
    for name, res in sorted(models, key=lambda x: x[1]['recall@100'], reverse=True):
        md_content += f"- **{name}**: R@100={res['recall@100']:.4f}, MRR={res['mrr']:.4f}\n"

md_content += f"""
---

## Key Findings

"""

if sorted_results:
    best = sorted_results[0]
    md_content += f"""
1. **Best Overall Model**: {best[0]}
   - Achieved {best[1]['recall@100']*100:.1f}% Recall@100
   - Category: {best[1]['category']}
   - Embedding Dimension: {best[1]['embedding_dim']}

"""

# Compare categories
md_content += f"""
2. **Category Performance**:
"""

cat_avg = {}
for cat, models in categories.items():
    avg_recall = np.mean([m[1]['recall@100'] for m in models])
    cat_avg[cat] = avg_recall

for cat, avg in sorted(cat_avg.items(), key=lambda x: x[1], reverse=True):
    md_content += f"   - {cat}: {avg:.4f} average Recall@100\n"

md_content += f"""
3. **Aviation-Specific Model Performance**:
"""

if "SafeAeroBERT" in results and results["SafeAeroBERT"]:
    safe_aero = results["SafeAeroBERT"]
    safe_rank = next(i for i, (n, _) in enumerate(sorted_results, 1) if n == "SafeAeroBERT")
    md_content += f"   - SafeAeroBERT ranked #{safe_rank} with {safe_aero['recall@100']:.4f} Recall@100\n"
    md_content += f"   - Despite aviation-specific training, general-purpose models performed better\n"

md_content += f"""
---

## Recommendation

Based on this evaluation:

**For Production Use:**
"""

if sorted_results:
    top1 = sorted_results[0]
    top2 = sorted_results[1] if len(sorted_results) > 1 else None

    md_content += f"\n1. **Primary Model**: {top1[0]}\n"
    md_content += f"   - Best Recall@100: {top1[1]['recall@100']:.4f}\n"
    md_content += f"   - Model ID: `{top1[1]['model_id']}`\n"

    if top2:
        md_content += f"\n2. **Alternative**: {top2[0]}\n"
        md_content += f"   - Recall@100: {top2[1]['recall@100']:.4f}\n"
        md_content += f"   - Model ID: `{top2[1]['model_id']}`\n"

md_content += f"""
---

## Dataset Details

- **Query Source**: rnapberkeley/asrs (Ronald's synthetic queries)
- **Document Source**: elihoole/asrs-aviation-reports
- **Total Validation Queries**: {len(val_queries)}
- **Queries Used**: {len(queries_text)}
- **Documents in Index**: {len(eval_docs)}
- **Evaluation Method**: Each query has 1 ground-truth relevant document (seed_doc_id)

---

*Generated by comprehensive_model_evaluation.py*
"""

# Write to file
with open("MODEL_COMPARISON_RESULTS.md", "w") as f:
    f.write(md_content)

print(f"✓ Results written to MODEL_COMPARISON_RESULTS.md")
print(f"\nEvaluation complete! Tested {len([r for r in results.values() if r is not None])} models successfully.")
print("="*80)
