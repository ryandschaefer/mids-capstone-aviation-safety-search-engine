from dataclasses import dataclass
from typing import Dict, Optional, List
import time

from search.pipeline.query_refiner import QueryRefiner
from search.config import PipelineConfig


@dataclass
class PipelineOutput:
    initial: List[Dict]
    final: List[Dict]
    used_query: str
    loops: int
    best_relevance: float


class SearchEnginePipeline:
    def __init__(
        self,
        refiner: QueryRefiner,
        hybrid_service,
        reranker,
        chunk_store,
        cfg: PipelineConfig,
    ):
        self.refiner = refiner
        self.hybrid = hybrid_service
        self.reranker = reranker
        self.chunk_store = chunk_store
        self.cfg = cfg

    def _p(self, msg: str):
        print(f"[PIPE {time.strftime('%H:%M:%S')}] {msg}", flush=True)

    @staticmethod
    def _same_top_ids(a: List[Dict], b: List[Dict]) -> bool:
        a_ids = [str(x.get("acn_num_ACN", "")) for x in (a or [])]
        b_ids = [str(x.get("acn_num_ACN", "")) for x in (b or [])]
        return a_ids == b_ids and len(a_ids) > 0

    @staticmethod
    def _candidates_to_initial_docs(candidates: List[Dict], top_docs: int) -> List[Dict]:
        best: Dict[str, Dict] = {}
        for c in candidates:
            doc_id = str(c.get("parent_doc_id", "")).strip()
            if not doc_id:
                continue
            score = float(c.get("score", 0.0))
            cid = str(c.get("chunk_id", "")).strip()
            prev = best.get(doc_id)
            if prev is None or score > float(prev["score"]):
                best[doc_id] = {"acn_num_ACN": doc_id, "score": score, "best_chunk_id": cid}

        docs = list(best.values())
        docs.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
        return docs[:top_docs]

    def search(self, user_query: str, filters: Optional[Dict] = None) -> PipelineOutput:
        t_start = time.time()
        self._p(f"search() start | user_query='{user_query}'")
        if filters:
            self._p(f"filters={filters}")

        t0 = time.time()
        self._p("refiner.refine() start")
        refine_res = self.refiner.refine(user_query)
        self._p(f"refiner.refine() done (+{time.time()-t0:.2f}s)")

        current_query = (getattr(refine_res, "refined", None) or user_query).strip()
        self._p(f"refined_query='{current_query}'")

        best_relevance_seen = -1.0
        best_final: List[Dict] = []
        best_initial: List[Dict] = []
        best_used_query = current_query
        loops_ran = 0

        prev_top_docs: List[Dict] = []
        no_improve_streak = 0

        for loop_i in range(self.cfg.max_loops):
            loops_ran = loop_i + 1
            self._p(f"loop {loops_ran}/{self.cfg.max_loops} | current_query='{current_query}'")

            t1 = time.time()
            self._p(f"hybrid.search() start | top_k_candidates={self.cfg.top_k_candidates}")
            candidates = self.hybrid.search(
                current_query,
                top_k=self.cfg.top_k_candidates,
                filters=filters,
            )
            self._p(f"hybrid.search() done (+{time.time()-t1:.2f}s) | candidates={len(candidates)}")

            if not candidates:
                self._p("STOP: 0 candidates from hybrid.search()")
                break

            top = candidates[:5]
            top_str = ", ".join([f"{c.get('chunk_id')}:{float(c.get('score', 0.0)):.3f}" for c in top])
            self._p(f"top5(pre-rerank chunks): {top_str}")

            initial_docs = self._candidates_to_initial_docs(candidates, top_docs=self.cfg.top_k_final)
            if initial_docs:
                top_init = ", ".join([f"{d['acn_num_ACN']}:{float(d['score']):.3f}" for d in initial_docs[:5]])
                self._p(f"top_initial5(docs): {top_init}")

            t2 = time.time()
            self._p(
                f"reranker.rerank() start | batch_size={self.cfg.judge_batch_size} "
                f"max_chunk_chars={self.cfg.max_chunk_chars} top_docs={self.cfg.top_k_final}"
            )

            judged = self.reranker.rerank(
                user_query=user_query,
                candidates=candidates,
                chunk_store=self.chunk_store,
                max_chunk_chars=self.cfg.max_chunk_chars,
                batch_size=self.cfg.judge_batch_size,
                top_docs=self.cfg.top_k_final,
            )

            best_rel = float(getattr(judged, "best_relevance", 0.0))
            final_docs = (getattr(judged, "scored_docs", None) or [])[: self.cfg.top_k_final]
            suggested = (getattr(judged, "suggested_query", None) or "").strip()

            self._p(
                f"reranker.rerank() done (+{time.time()-t2:.2f}s) | best_rel={best_rel:.3f} "
                f"| scored_docs={len(getattr(judged, 'scored_docs', None) or [])}"
            )

            if final_docs:
                top_final = ", ".join(
                    [f"{r.get('acn_num_ACN')}:{float(r.get('relevance', 0.0)):.3f}" for r in final_docs[:5]]
                )
                self._p(f"top_final5(docs): {top_final}")
            else:
                self._p("WARNING: final doc list empty after rerank")

            if loop_i == 0 or best_rel > best_relevance_seen:
                self._p(f"update best: {best_relevance_seen:.3f} -> {best_rel:.3f}")
                best_relevance_seen = best_rel
                best_final = final_docs
                best_initial = initial_docs
                best_used_query = current_query
                no_improve_streak = 0
            else:
                no_improve_streak += 1

            if best_rel >= self.cfg.accept_threshold:
                self._p(f"ACCEPT: best_rel {best_rel:.3f} >= threshold {self.cfg.accept_threshold:.3f}")
                self._p(f"search() done total (+{time.time()-t_start:.2f}s)")
                return PipelineOutput(
                    initial=initial_docs,
                    final=final_docs,
                    used_query=current_query,
                    loops=loops_ran,
                    best_relevance=best_rel,
                )

            if loop_i > 0 and self._same_top_ids(final_docs, prev_top_docs):
                self._p("STOP: top docs unchanged from previous loop")
                break
            prev_top_docs = final_docs

            if no_improve_streak >= getattr(self.cfg, "max_no_improve_loops", 1):
                self._p("STOP: no improvement streak reached")
                break

            if not suggested:
                self._p("STOP: no suggested_query from reranker")
                break
            if suggested == current_query:
                self._p("STOP: suggested_query identical to current_query")
                break

            self._p(f"LOOP BACK: suggested_query='{suggested}'")
            current_query = suggested

        if best_relevance_seen < 0:
            best_relevance_seen = 0.0

        self._p(f"FALLBACK: returning best_seen={best_relevance_seen:.3f} using_query='{best_used_query}'")
        self._p(f"search() done total (+{time.time()-t_start:.2f}s)")
        return PipelineOutput(
            initial=best_initial,
            final=best_final,
            used_query=best_used_query,
            loops=loops_ran,
            best_relevance=best_relevance_seen,
        )