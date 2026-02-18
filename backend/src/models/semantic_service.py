# semantic_service.py
# ---------------------------------------------------------
# Dual-Encoder Semantic Retrieval Service
# Implements dense retrieval using sentence transformers
# ---------------------------------------------------------

import numpy as np
import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer, models as st_models

# Models that need manual wrapping (not native sentence-transformers)
_WRAP_MODELS = {"bert-base-cased", "bert-base-uncased", "roberta-base", "roberta-large"}

def _load_sentence_transformer(model_name: str) -> SentenceTransformer:
    """Load model, wrapping raw transformers with mean pooling if needed."""
    if model_name in _WRAP_MODELS:
        word_embedding = st_models.Transformer(model_name)
        pooling = st_models.Pooling(
            word_embedding.get_word_embedding_dimension(),
            pooling_mode='mean'
        )
        return SentenceTransformer(modules=[word_embedding, pooling])
    return SentenceTransformer(model_name)

# =========================
# Semantic Index
# =========================

class SemanticIndex:
    """
    Dual-encoder semantic search using sentence transformers.

    Key design decisions based on project requirements:
    - Pre-compute document embeddings for all chunks
    - Encode queries at search time
    - Use cosine similarity for ranking
    - Support recall-oriented retrieval (return top-k with k up to 1000)
    """

    def __init__(
        self,
        model_name: str,
        embeddings: np.ndarray,
        meta: List[Tuple],
        chunk_size: int,
        overlap: int
    ):
        """
        Initialize semantic index.

        Args:
            model_name: Name of the sentence-transformer model
            embeddings: Pre-computed document embeddings (N x embedding_dim)
            meta: Metadata for each chunk [(parent_id, chunk_j, when, where, anomaly), ...]
            chunk_size: Chunk size used during indexing
            overlap: Overlap size used during chunking
        """
        self.model_name = model_name
        self.model = None  # Lazy load to save memory
        self.embeddings = embeddings  # Shape: (num_docs, embedding_dim)
        self.meta = meta
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.N = len(embeddings)

        # Normalize embeddings for fast cosine similarity
        # cosine_sim(q, d) = dot(normalize(q), normalize(d))
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        self.normalized_embeddings = embeddings / (norms + 1e-8)

    def _load_model(self):
        """Lazy load the model when needed for encoding queries."""
        if self.model is None:
            print(f"Loading model: {self.model_name}")
            self.model = _load_sentence_transformer(self.model_name)

    @staticmethod
    def build(
        work,
        model_name: str = "bert-base-cased",
        chunk_size: int = 250,
        overlap: int = 50,
        batch_size: int = 32,
        show_progress: bool = True
    ):
        """
        Build semantic index by computing embeddings for all chunks.

        Args:
            work: HuggingFace dataset or list of records
            model_name: Sentence-transformer model to use
            chunk_size: Tokens per chunk
            overlap: Overlap between chunks
            batch_size: Batch size for encoding
            show_progress: Show progress bar during encoding

        Returns:
            SemanticIndex instance
        """
        from models.bm25_service import get_text, get_doc_id, tokenize, chunk_tokens

        print(f"Building semantic index with model: {model_name}")
        model = _load_sentence_transformer(model_name)

        # Collect all chunks and metadata (reuse BM25 chunking logic)
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
                # Reconstruct text from tokens
                chunk_text = " ".join(ctoks)
                chunks_text.append(chunk_text)
                meta.append((parent_id, j, when, where, anomaly))

        print(f"Encoding {len(chunks_text)} chunks...")

        # Encode all chunks
        embeddings = model.encode(
            chunks_text,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=False  # We'll normalize separately
        )

        print(f"Embeddings shape: {embeddings.shape}")

        return SemanticIndex(
            model_name=model_name,
            embeddings=embeddings,
            meta=meta,
            chunk_size=chunk_size,
            overlap=overlap
        )

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for semantically similar chunks.

        Args:
            query: Search query text
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of search results with scores and metadata
        """
        # Load model if needed
        self._load_model()

        # Encode query
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=False
        )[0]  # Shape: (embedding_dim,)

        # Normalize query embedding
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)

        # Compute cosine similarity with all documents
        # scores = normalized_embeddings @ query_norm
        scores = self.normalized_embeddings @ query_norm  # Shape: (N,)

        # Apply filters if provided
        if filters:
            mask = self._apply_filters(filters)
            scores = scores * mask - (1 - mask) * 1e9  # Set filtered out scores to very low

        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]

        # Build results
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < -1e8:  # Skip filtered out results
                continue

            parent_id, chunk_j, when, where, anomaly = self.meta[idx]
            results.append({
                "score": score,
                "doc_int_id": int(idx),
                "parent_doc_id": str(parent_id),
                "chunk_j": int(chunk_j),
                "chunk_id": f"{parent_id}__chunk{chunk_j}",
                "when": when,
                "where": where,
                "anomaly": anomaly,
            })

        return results

    def _apply_filters(self, filters: Dict) -> np.ndarray:
        """
        Create a binary mask for filtering results.

        Returns:
            Binary mask array (1 = keep, 0 = filter out)
        """
        mask = np.ones(self.N, dtype=np.float32)

        for idx in range(self.N):
            parent_id, chunk_j, when, where, anomaly = self.meta[idx]

            # When prefix filter
            wp = filters.get("when_prefix")
            if wp and (when is None or not str(when).startswith(str(wp))):
                mask[idx] = 0
                continue

            # Where contains filter
            wc = filters.get("where_contains")
            if wc and (where is None or str(wc) not in str(where)):
                mask[idx] = 0
                continue

            # Anomaly contains filter
            ac = filters.get("anomaly_contains")
            if ac and (anomaly is None or str(ac) not in str(anomaly)):
                mask[idx] = 0
                continue

        return mask

    def save(self, path: str = "models/semantic_index.pkl"):
        """
        Save semantic index to disk.

        Note: Model is not saved, only embeddings and metadata.
        Model will be re-loaded from HuggingFace when needed.
        """
        payload = {
            "model_name": self.model_name,
            "embeddings": self.embeddings,
            "meta": self.meta,
            "chunk_size": self.chunk_size,
            "overlap": self.overlap,
        }

        Path(path).parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as f:
            pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)

        print(f"Semantic index saved to {path}")
        print(f"Size: {Path(path).stat().st_size / 1024 / 1024:.2f} MB")

    @staticmethod
    def load(path: str = "models/semantic_index.pkl"):
        """Load semantic index from disk."""
        with open(path, "rb") as f:
            payload = pickle.load(f)

        return SemanticIndex(
            model_name=payload["model_name"],
            embeddings=payload["embeddings"],
            meta=payload["meta"],
            chunk_size=payload["chunk_size"],
            overlap=payload["overlap"],
        )


# =========================
# Service API (UI-facing)
# =========================

semantic_index = None
text_lookup = None

def init(work, index_path: str = "models/semantic_index.pkl", force_rebuild: bool = False):
    """
    Initialize semantic search service.

    Args:
        work: HuggingFace dataset or list of records
        index_path: Path to saved index
        force_rebuild: Force rebuild even if index exists
    """
    global semantic_index, text_lookup
    from models.bm25_service import get_doc_id, get_text

    index_file = Path(index_path)

    if index_file.exists() and not force_rebuild:
        print(f"Loading existing semantic index from {index_path}")
        semantic_index = SemanticIndex.load(index_path)
    else:
        print("Building new semantic index...")
        semantic_index = SemanticIndex.build(work)
        semantic_index.save(index_path)

    # Build text lookup for snippet generation
    text_lookup = {get_doc_id(r): get_text(r) for r in work}
    print(f"Semantic search initialized. {semantic_index.N} chunks indexed.")

def search(query: str, top_k: int = 10, filters: Optional[Dict] = None) -> List[Dict]:
    """
    Search API for UI / FastAPI.

    Args:
        query: Search query
        top_k: Number of results
        filters: Optional metadata filters

    Returns:
        List of results with scores and metadata
    """
    if semantic_index is None:
        raise RuntimeError("Semantic index not initialized. Call init(work).")

    return semantic_index.search(query, top_k, filters)
