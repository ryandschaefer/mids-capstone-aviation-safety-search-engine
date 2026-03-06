import gzip
import pickle
from pathlib import Path
import heapq
import re
from collections import defaultdict
from typing import Dict, List, Optional

_token_re = re.compile(r"[a-z0-9]+(?:[-/][a-z0-9]+)*", re.IGNORECASE)

def tokenize(text: str) -> List[str]:
    if not text:
        return []
    return _token_re.findall(text.lower())

def chunk_tokens(tokens: List[str], chunk_size: int = 250, overlap: int = 50) -> List[List[str]]:
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

def get_doc_id(r: Dict) -> str:
    return str(r.get("acn_num_ACN", ""))

def get_text(r: Dict) -> str:
    return (
        (r.get("Report 1_Narrative") or "").strip()
        or (r.get("Report 2_Narrative") or "").strip()
        or (r.get("Report 1.2_Synopsis") or "").strip()
        or (r.get("Report 1_Synopsis") or "").strip()
    )


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
    def load(path: str):
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

    def search(self, query: str, top_k: int = 10, k1: float = 1.2, b: float = 0.75):
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


bm25: Optional[BM25Index] = None
text_lookup: Optional[Dict[str, str]] = None

def init(work):
    global bm25, text_lookup
    BASE_DIR = Path(__file__).resolve().parent
    index_path = BASE_DIR / "models" / "bm25_asrs_full.pkl.gz"
    bm25 = BM25Index.load(index_path)
    text_lookup = {get_doc_id(r): get_text(r) for r in work}

def search(query: str, top_k: int = 10, filters: Optional[Dict] = None) -> List[Dict]:
    hits = bm25.search(query, top_k)
    results = []
    for d_id, score in hits:
        parent_id, chunk_j, *rest = bm25.meta[d_id]
        when = rest[0] if len(rest) > 0 else None
        where = rest[1] if len(rest) > 1 else None
        anomaly = rest[2] if len(rest) > 2 else None

        if filters:
            wp = filters.get("when_prefix")
            if wp and (when is None or not str(when).startswith(str(wp))):
                continue
            wc = filters.get("where_contains")
            if wc and (where is None or str(wc) not in str(where)):
                continue
            ac = filters.get("anomaly_contains")
            if ac and (anomaly is None or str(ac) not in str(anomaly)):
                continue

        results.append({
            "chunk_id": f"{parent_id}__chunk{chunk_j}",
            "score": float(score),
            "doc_int_id": int(d_id),
            "parent_doc_id": str(parent_id),
            "chunk_j": int(chunk_j),
            "when": when,
            "where": where,
            "anomaly": anomaly,
            "source": "bm25",
        })
    return results