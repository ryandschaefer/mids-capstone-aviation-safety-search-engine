import json
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

from ..llm.base import BaseLLM, ChatMessage


@dataclass
class RerankResult:
    scored_docs: List[Dict]
    best_relevance: float
    suggested_query: Optional[str]


class LLMReranker:
    def __init__(self, llm: BaseLLM, threshold: float = 0.6):
        self.llm = llm
        self.threshold = threshold

    def rerank(
        self,
        user_query: str,
        candidates: List[Dict],
        chunk_store,
        max_chunk_chars: int = 250,
        batch_size: int = 8,
        top_docs: int = 10,
    ) -> RerankResult:
        chunk_score: Dict[str, float] = {}
        suggested: Optional[str] = None

        for start in range(0, len(candidates), batch_size):
            batch = candidates[start:start + batch_size]
            prompt = self._build_prompt(user_query, batch, chunk_store, max_chunk_chars)

            raw = self.llm.chat([ChatMessage(role="user", content=prompt)]).content
            ranking, local_suggested = self._parse_ranking_json(raw)

            if suggested is None and local_suggested:
                suggested = local_suggested

            for rank, cid in enumerate(ranking, start=1):
                score = 1.0 / rank
                chunk_score[cid] = max(chunk_score.get(cid, 0.0), score)

            for c in batch:
                cid = c["chunk_id"]
                chunk_score.setdefault(cid, 0.0)

        doc_best: Dict[str, Tuple[float, str]] = {}
        for c in candidates:
            cid = c["chunk_id"]
            doc_id = str(c.get("parent_doc_id", "")).strip()
            if not doc_id:
                continue
            s = float(chunk_score.get(cid, 0.0))
            prev = doc_best.get(doc_id)
            if prev is None or s > prev[0]:
                doc_best[doc_id] = (s, cid)

        scored_docs = [
            {"acn_num_ACN": doc_id, "relevance": score, "best_chunk_id": best_chunk}
            for doc_id, (score, best_chunk) in doc_best.items()
        ]
        scored_docs.sort(key=lambda x: x["relevance"], reverse=True)

        best = scored_docs[0]["relevance"] if scored_docs else 0.0
        suggested = self._clean_one_line(suggested)

        if best < self.threshold and not suggested:
            suggested = self._force_suggest(user_query)

        return RerankResult(scored_docs=scored_docs[:top_docs], best_relevance=best, suggested_query=suggested)

    def _build_prompt(self, user_query: str, batch: List[Dict], chunk_store, max_chunk_chars: int) -> str:
        lines = [
            "You are an ASRS relevance reranker.",
            "Given USER_QUERY and CHUNKS, output the chunk_ids sorted from MOST relevant to LEAST relevant.",
            "",
            "Output JSON ONLY in exactly this form:",
            '{"ranking":["chunk_id1","chunk_id2", "..."], "suggested_query":""}',
            "",
            "Rules:",
            "- ranking must include EVERY chunk_id exactly once",
            "- no explanation text",
            "- suggested_query: if the best chunk is not clearly relevant, output ONE LINE keyword rewrite; else empty string",
            "",
            f"USER_QUERY: {user_query}",
            "CHUNKS:",
        ]

        for c in batch:
            cid = c["chunk_id"]
            txt = (chunk_store.get(cid) or "")[:max_chunk_chars]
            txt = txt.replace("\n", " ").replace('"', '\\"').strip()
            lines.append(f'{{"chunk_id":"{cid}","text":"{txt}"}}')

        return "\n".join(lines)

    @staticmethod
    def _parse_ranking_json(raw: str) -> Tuple[List[str], Optional[str]]:
        """
        Parse a single JSON object. If model outputs garbage, fall back to original order.
        """
        raw = raw.strip()
        if "{" in raw and "}" in raw:
            raw = raw[raw.find("{"): raw.rfind("}") + 1]

        try:
            obj = json.loads(raw)
        except Exception:
            return [], None

        ranking = obj.get("ranking") or []
        if not isinstance(ranking, list):
            ranking = []
        ranking = [str(x) for x in ranking]

        suggested = obj.get("suggested_query")
        suggested = str(suggested).strip() if suggested is not None else None
        return ranking, suggested

    @staticmethod
    def _clean_one_line(s: Optional[str]) -> Optional[str]:
        if not s:
            return None
        for line in s.splitlines():
            line = line.strip().strip('"')
            if not line:
                continue
            if "explanation" in line.lower():
                return None
            return line[:300]
        return None

    def _force_suggest(self, user_query: str) -> str:
        prompt = (
            "Rewrite as ASRS KEYWORDS ONLY (one line). No sentences. No explanation.\n"
            "Include abbreviations/synonyms like: NMAC, TCAS, RA, TA, traffic conflict, loss of separation.\n\n"
            f"Query: {user_query}\nRewrite:"
        )
        out = self.llm.chat([ChatMessage(role="user", content=prompt)]).content
        out = self._clean_one_line(out) or user_query
        return out