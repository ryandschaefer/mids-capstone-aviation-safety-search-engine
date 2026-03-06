from typing import Dict, Optional, Any, Tuple, List

from ..retrieval.bm25 import tokenize, chunk_tokens, get_doc_id, get_text


class ChunkStore:
    def __init__(self, chunk_size: int = 250, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self._chunks: Dict[str, str] = {}

    def put(self, chunk_id: str, text: str):
        if text and chunk_id:
            self._chunks[chunk_id] = text

    def get(self, chunk_id: str) -> Optional[str]:
        return self._chunks.get(chunk_id)

    def build_from_semantic_meta(self, semantic_meta: List[Tuple[Any, ...]]):
        for row in semantic_meta:
            if len(row) < 6:
                continue
            parent_id, j = str(row[0]), int(row[1])
            chunk_text = row[5]
            cid = f"{parent_id}__chunk{j}"
            self.put(cid, chunk_text)

    def build_from_work(self, work):
        for r in work:
            pid = get_doc_id(r)
            text = get_text(r)
            if not pid or not text:
                continue
            toks = tokenize(text)
            chunks = chunk_tokens(toks, self.chunk_size, self.overlap)
            for j, ctoks in enumerate(chunks):
                cid = f"{pid}__chunk{j}"
                self.put(cid, " ".join(ctoks))