# bm25_service.py
# ---------------------------------------------------------
# Lightweight BM25 service layer
# ---------------------------------------------------------

import gzip
import pickle
import math
import heapq
import re
from collections import defaultdict, Counter
import boto3
import os

# =========================
# Tokenizer + chunking
# =========================

_token_re = re.compile(r"[a-z0-9]+(?:[-/][a-z0-9]+)*", re.IGNORECASE)

def tokenize(text):
    if not text:
        return []
    text = text.lower()
    return _token_re.findall(text)

def chunk_tokens(tokens, chunk_size=250, overlap=50):
    step = chunk_size - overlap
    chunks = []
    for start in range(0, len(tokens), step):
        chunk = tokens[start:start + chunk_size]
        if not chunk:
            break
        chunks.append(chunk)
        if start + chunk_size >= len(tokens):
            break
    return chunks

# =========================
# Dataset adapters (ASRS)
# =========================

def get_doc_id(r):
    return str(r.get("acn_num_ACN", ""))

def get_text(r):
    return (
        (r.get("Report 1_Narrative") or "").strip()
        or (r.get("Report 2_Narrative") or "").strip()
        or (r.get("Report 1.2_Synopsis") or "").strip()
    )

# =========================
# BM25 Index
# =========================

class BM25Index:
    def __init__(self, postings, doc_len, avgdl, idf, meta, chunk_size, overlap):
        self.postings = postings
        self.doc_len = doc_len
        self.avgdl = avgdl
        self.idf = idf
        self.meta = meta
        self.chunk_size = chunk_size
        self.overlap = overlap

    @staticmethod
    def load(path):
        with gzip.open(path, "rb") as f:
            payload = pickle.load(f)

        return BM25Index(
            postings=defaultdict(list, payload["postings"]),
            doc_len=payload["doc_len"],
            avgdl=payload["avgdl"],
            idf=payload["idf"],
            meta=payload["meta"],
            chunk_size=payload["chunk_size"],
            overlap=payload["overlap"],
        )

    def search(self, query, top_k=10, k1=1.2, b=0.75):
        q_tokens = list(dict.fromkeys(tokenize(query)))
        scores = defaultdict(float)

        for term in q_tokens:
            if term not in self.postings:
                continue
            term_idf = self.idf.get(term, 0.0)

            for d_id, tf in self.postings[term]:
                dl = self.doc_len[d_id]
                denom = tf + k1 * (1 - b + b * (dl / self.avgdl))
                scores[d_id] += term_idf * (tf * (k1 + 1)) / denom

        return heapq.nlargest(top_k, scores.items(), key=lambda x: x[1])

# =========================
# Service API (UI-facing)
# =========================

bm25 = None

def init(index_path="src/models/bm25_asrs_full.pkl.gz"):
    """
    Initialize once at app startup.
    """
    # Download index from s3
    S3_BUCKET = os.environ.get("S3_BUCKET")
    S3_KEY = os.environ.get("S3_KEY")
    print(f"Downloading s3://{S3_BUCKET}/{S3_KEY}...")
    s3 = boto3.client("s3")
    s3.download_file(S3_BUCKET, S3_KEY, index_path)
    print("Download complete.")
    
    global bm25
    bm25 = BM25Index.load(index_path)

def search(query, top_k=10):
    """
    Search API for UI / FastAPI.
    """
    if bm25 is None:
        raise RuntimeError("BM25 not initialized. Call init(work).")

    hits = bm25.search(query, top_k)
    results = []

    for d_id, score in hits:
        parent_id, chunk_j, *_ = bm25.meta[d_id]
        results.append({
            "id": f"{parent_id}__chunk{chunk_j}",
            "score": float(score),
            "doc_id": parent_id,
            "chunk_id": int(chunk_j),
        })

    return results
