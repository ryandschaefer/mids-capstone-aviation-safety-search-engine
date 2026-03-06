import numpy as np
import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer, models as st_models

_WRAP_MODELS = {"bert-base-cased", "bert-base-uncased", "roberta-base", "roberta-large"}

def _load_sentence_transformer(model_name: str, device: str = "cpu") -> SentenceTransformer:
    if model_name in _WRAP_MODELS:
        word_embedding = st_models.Transformer(model_name)
        pooling = st_models.Pooling(
            word_embedding.get_word_embedding_dimension(),
            pooling_mode="mean"
        )
        return SentenceTransformer(modules=[word_embedding, pooling], device=device)
    return SentenceTransformer(model_name, device=device)

class SemanticIndex:
    def __init__(
        self,
        model_name: str,
        embeddings: np.ndarray,
        meta: List[Tuple],
        chunk_size: int,
        overlap: int
    ):
        self.model_name = model_name
        self.model = None
        self.embeddings = embeddings
        self.meta = meta
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.N = len(embeddings)

        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        self.normalized_embeddings = embeddings / (norms + 1e-8)

    def _load_model(self):
        if self.model is None:
            self.model = _load_sentence_transformer(self.model_name)

    @staticmethod
    def build(
        work,
        model_name: str = "bert-base-cased",
        chunk_size: int = 250,
        overlap: int = 50,
        batch_size: int = 32,
        show_progress: bool = True,
        device: str = "cpu",
    ):
        from ..retrieval.bm25 import get_text, get_doc_id, tokenize, chunk_tokens

        model = _load_sentence_transformer(model_name, device=device)
        chunks_text = []
        meta = []

        for r in work:
            text = get_text(r)
            if not text:
                continue

            toks = tokenize(text)
            chunk_list = chunk_tokens(toks, chunk_size, overlap)

            parent_id = get_doc_id(r)
            when = r.get("Time_Date")
            where = r.get("Place_Locale Reference")
            anomaly = r.get("Events_Anomaly")

            for j, ctoks in enumerate(chunk_list):
                chunk_text = " ".join(ctoks)
                chunks_text.append(chunk_text)
                meta.append((parent_id, j, when, where, anomaly, chunk_text))

        embeddings = model.encode(
            chunks_text,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=False
        )

        return SemanticIndex(
            model_name=model_name,
            embeddings=embeddings,
            meta=meta,
            chunk_size=chunk_size,
            overlap=overlap
        )

    def search(self, query: str, top_k: int = 10, filters: Optional[Dict] = None) -> List[Dict]:
        self._load_model()
        query_embedding = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=False)[0]
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        scores = self.normalized_embeddings @ query_norm

        if filters:
            mask = self._apply_filters(filters)
            scores = scores * mask - (1 - mask) * 1e9

        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < -1e8:
                continue

            parent_id, chunk_j, when, where, anomaly, _chunk_text = self.meta[idx]
            results.append({
                "score": score,
                "doc_int_id": int(idx),
                "parent_doc_id": str(parent_id),
                "chunk_j": int(chunk_j),
                "chunk_id": f"{parent_id}__chunk{chunk_j}",
                "when": when,
                "where": where,
                "anomaly": anomaly,
                "source": "semantic",
            })
        return results

    def _apply_filters(self, filters: Dict) -> np.ndarray:
        mask = np.ones(self.N, dtype=np.float32)

        for idx in range(self.N):
            parent_id, chunk_j, when, where, anomaly, _chunk_text = self.meta[idx]
            wp = filters.get("when_prefix")
            if wp and (when is None or not str(when).startswith(str(wp))):
                mask[idx] = 0
                continue

            wc = filters.get("where_contains")
            if wc and (where is None or str(wc) not in str(where)):
                mask[idx] = 0
                continue

            ac = filters.get("anomaly_contains")
            if ac and (anomaly is None or str(ac) not in str(anomaly)):
                mask[idx] = 0
                continue

        return mask

    @staticmethod
    def load(path: str = "/models/semantic_index.pkl"):
        with open(path, "rb") as f:
            payload = pickle.load(f)
        return SemanticIndex(
            model_name=payload["model_name"],
            embeddings=payload["embeddings"],
            meta=payload["meta"],
            chunk_size=payload["chunk_size"],
            overlap=payload["overlap"],
        )


semantic_index: Optional[SemanticIndex] = None
text_lookup: Optional[Dict[str, str]] = None

def init(work):
    global semantic_index, text_lookup
    from ..retrieval.bm25 import get_doc_id, get_text
    BASE_DIR = Path(__file__).resolve().parent
    index_path = BASE_DIR / "models" / "semantic_index.pkl"
    semantic_index = SemanticIndex.load(index_path)
    text_lookup = {get_doc_id(r): get_text(r) for r in work}

def search(query: str, top_k: int = 10, filters: Optional[Dict] = None) -> List[Dict]:
    return semantic_index.search(query, top_k, filters)