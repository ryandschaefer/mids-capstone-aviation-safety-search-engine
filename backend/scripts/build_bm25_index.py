#!/usr/bin/env python3
"""
Build BM25 index for ASRS and save to backend/src/models/bm25_asrs_full.pkl.gz.

Run from project root or backend/:
    poetry run python scripts/build_bm25_index.py
    # or: cd backend && poetry run python scripts/build_bm25_index.py

Output: backend/src/models/bm25_asrs_full.pkl.gz (format compatible with bm25_service.py)
"""

import gzip
import math
import pickle
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Ensure we can import datasets
try:
    from datasets import load_dataset
except ImportError:
    print("Run: poetry install (or pip install datasets)")
    sys.exit(1)

# --- Schema + tokenizer (match BM25MVP / Real_BM25_Evaluation_Colab) ---
def get_text(r):
    return (r.get("Report 1_Narrative") or r.get("Report 2_Narrative") or "").strip()

def get_doc_id(r):
    return str(r.get("acn_num_ACN") or r.get("Person 1.10_ASRS Report Number.Accession Number") or "")

def get_anomaly(r):
    return r.get("Events_Anomaly")

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "has", "have", "he", "her", "his",
    "i", "if", "in", "into", "is", "it", "its", "me", "my", "not", "of", "on", "or", "our", "she", "so", "that",
    "the", "their", "them", "then", "there", "these", "they", "this", "to", "was", "we", "were", "what", "when",
    "where", "which", "who", "with", "would", "you", "your"
}
_token_re = re.compile(r"[a-z0-9]+(?:[-/][a-z0-9]+)*", re.IGNORECASE)

def tokenize(text, lowercase=True, remove_stopwords=True, min_len=2):
    if text is None:
        return []
    if lowercase:
        text = text.lower()
    toks = _token_re.findall(text)
    if min_len:
        toks = [t for t in toks if len(t) >= min_len]
    if remove_stopwords:
        toks = [t for t in toks if t not in STOPWORDS]
    return toks

def chunk_tokens(tokens, chunk_size=250, overlap=50):
    step = chunk_size - overlap
    chunks = []
    for start in range(0, len(tokens), step):
        end = start + chunk_size
        chunk = tokens[start:end]
        if not chunk:
            break
        chunks.append(chunk)
        if end >= len(tokens):
            break
    return chunks


def main():
    script_dir = Path(__file__).resolve().parent
    backend_dir = script_dir.parent
    models_dir = backend_dir / "src" / "models"
    out_path = models_dir / "bm25_asrs_full.pkl.gz"

    models_dir.mkdir(parents=True, exist_ok=True)

    print("Loading ASRS dataset...")
    ds = load_dataset("elihoole/asrs-aviation-reports")
    work = ds["train"]
    work_list = [work[i] for i in range(len(work))]
    print(f"  Loaded {len(work_list)} reports")

    print("Building BM25 index (chunk_size=250, overlap=50)...")
    postings = defaultdict(list)
    doc_len = []
    meta = []
    chunk_size, overlap = 250, 50

    for r in work_list:
        text = get_text(r)
        if not text:
            continue
        toks = tokenize(text)
        chunk_list = chunk_tokens(toks, chunk_size, overlap)
        parent_id = get_doc_id(r)
        anomaly = get_anomaly(r)
        for j, ctoks in enumerate(chunk_list):
            d_id = len(doc_len)
            doc_len.append(len(ctoks))
            meta.append((parent_id, j, None, None, anomaly))
            tf = Counter(ctoks)
            for term, freq in tf.items():
                postings[term].append((d_id, freq))

    N = len(doc_len)
    avgdl = sum(doc_len) / N if N else 0.0
    df = {t: len(lst) for t, lst in postings.items()}
    idf = {t: math.log((N - df_t + 0.5) / (df_t + 0.5) + 1.0) for t, df_t in df.items()}
    for t in postings:
        postings[t].sort(key=lambda x: x[0])

    payload = {
        "postings": dict(postings),
        "doc_len": doc_len,
        "avgdl": avgdl,
        "idf": idf,
        "meta": meta,
        "chunk_size": chunk_size,
        "overlap": overlap,
    }

    print(f"  Index: {N} chunks, {len(postings)} unique terms")

    print(f"Saving to {out_path}...")
    with gzip.open(out_path, "wb") as f:
        pickle.dump(payload, f)

    print("Done. Backend can now load this index.")


if __name__ == "__main__":
    main()
