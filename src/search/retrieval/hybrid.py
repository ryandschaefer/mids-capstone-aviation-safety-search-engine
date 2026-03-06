from typing import List, Dict, Optional

def min_max_normalize(scores: List[float]) -> List[float]:
    if not scores:
        return []
    mn, mx = min(scores), max(scores)
    if mx == mn:
        return [1.0] * len(scores)
    return [(s - mn) / (mx - mn) for s in scores]

def rank_normalize(scores: List[float]) -> List[float]:
    if not scores:
        return []
    indexed = [(s, i) for i, s in enumerate(scores)]
    indexed.sort(reverse=True, key=lambda x: x[0])
    ranks = [0] * len(scores)
    for r, (_s, idx) in enumerate(indexed, start=1):
        ranks[idx] = r
    max_rank = len(scores)
    return [(max_rank - r + 1) / max_rank for r in ranks]


class HybridFusion:
    def __init__(self, bm25_service, semantic_service, alpha: float = 0.5, normalization: str = "min_max", retrieve_k: int = 200):
        self.bm25 = bm25_service
        self.semantic = semantic_service
        self.alpha = alpha
        self.normalization = normalization
        self.retrieve_k = retrieve_k

    def search(self, query: str, top_k: int = 10, filters: Optional[Dict] = None, alpha: Optional[float] = None) -> List[Dict]:
        a = alpha if alpha is not None else self.alpha
        bm25_results = self.bm25.search(query, top_k=self.retrieve_k, filters=filters)
        semantic_results = self.semantic.search(query, top_k=self.retrieve_k, filters=filters)
        return self._fuse(bm25_results, semantic_results, alpha=a, top_k=top_k)

    def _fuse(self, bm25_results: List[Dict], semantic_results: List[Dict], alpha: float, top_k: int) -> List[Dict]:
        bm25_scores = {r["chunk_id"]: r["score"] for r in bm25_results}
        sem_scores = {r["chunk_id"]: r["score"] for r in semantic_results}
        all_ids = set(bm25_scores) | set(sem_scores)

        bm25_list = [bm25_scores.get(cid, 0.0) for cid in all_ids]
        sem_list = [sem_scores.get(cid, 0.0) for cid in all_ids]

        if self.normalization == "rank":
            bm25_norm = dict(zip(all_ids, rank_normalize(bm25_list)))
            sem_norm = dict(zip(all_ids, rank_normalize(sem_list)))
        else:
            bm25_norm = dict(zip(all_ids, min_max_normalize(bm25_list)))
            sem_norm = dict(zip(all_ids, min_max_normalize(sem_list)))

        meta = {}
        for r in bm25_results:
            meta[r["chunk_id"]] = r
        for r in semantic_results:
            meta.setdefault(r["chunk_id"], r)

        fused = []
        for cid in all_ids:
            fused_score = alpha * bm25_norm.get(cid, 0.0) + (1 - alpha) * sem_norm.get(cid, 0.0)
            m = meta.get(cid, {})
            fused.append({
                "chunk_id": cid,
                "score": float(fused_score),
                "bm25_score": bm25_scores.get(cid, 0.0),
                "semantic_score": sem_scores.get(cid, 0.0),
                "parent_doc_id": m.get("parent_doc_id", ""),
                "chunk_j": m.get("chunk_j", 0),
                "when": m.get("when"),
                "where": m.get("where"),
                "anomaly": m.get("anomaly"),
                "source": "hybrid",
            })

        fused.sort(key=lambda x: x["score"], reverse=True)
        return fused[:top_k]


class ReciprocalRankFusion:
    def __init__(self, bm25_service, semantic_service, k: int = 60, retrieve_k: int = 200):
        self.bm25 = bm25_service
        self.semantic = semantic_service
        self.k = k
        self.retrieve_k = retrieve_k

    def search(self, query: str, top_k: int = 10, filters: Optional[Dict] = None) -> List[Dict]:
        bm25_results = self.bm25.search(query, top_k=self.retrieve_k, filters=filters)
        sem_results = self.semantic.search(query, top_k=self.retrieve_k, filters=filters)

        bm25_ranks = {r["chunk_id"]: i + 1 for i, r in enumerate(bm25_results)}
        sem_ranks = {r["chunk_id"]: i + 1 for i, r in enumerate(sem_results)}
        all_ids = set(bm25_ranks) | set(sem_ranks)

        meta = {}
        for r in bm25_results:
            meta[r["chunk_id"]] = r
        for r in sem_results:
            meta.setdefault(r["chunk_id"], r)

        fused = []
        for cid in all_ids:
            score = 0.0
            if cid in bm25_ranks:
                score += 1.0 / (self.k + bm25_ranks[cid])
            if cid in sem_ranks:
                score += 1.0 / (self.k + sem_ranks[cid])
            m = meta.get(cid, {})
            fused.append({
                "chunk_id": cid,
                "score": float(score),
                "bm25_rank": bm25_ranks.get(cid),
                "semantic_rank": sem_ranks.get(cid),
                "parent_doc_id": m.get("parent_doc_id", ""),
                "chunk_j": m.get("chunk_j", 0),
                "when": m.get("when"),
                "where": m.get("where"),
                "anomaly": m.get("anomaly"),
                "source": "rrf",
            })
        fused.sort(key=lambda x: x["score"], reverse=True)
        return fused[:top_k]


hybrid_fusion = None

def init(bm25_service, semantic_service, fusion_type: str = "linear", alpha: float = 0.5, normalization: str = "min_max", rrf_k: int = 60, retrieve_k: int = 200):
    global hybrid_fusion
    if fusion_type == "rrf":
        hybrid_fusion = ReciprocalRankFusion(bm25_service, semantic_service, k=rrf_k, retrieve_k=retrieve_k)
    else:
        hybrid_fusion = HybridFusion(bm25_service, semantic_service, alpha=alpha, normalization=normalization, retrieve_k=retrieve_k)

def search(query: str, top_k: int = 10, filters: Optional[Dict] = None) -> List[Dict]:
    return hybrid_fusion.search(query, top_k, filters)