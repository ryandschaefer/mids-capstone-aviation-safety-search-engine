import time
import argparse
from datasets import load_dataset

from search.llm.factory import build_llm
from search.config import PipelineConfig

from search.pipeline.query_refiner import QueryRefiner
from search.pipeline.reranker import LLMReranker
from search.pipeline.search import SearchEnginePipeline

from search.retrieval import bm25, semantic, hybrid
from search.retrieval.chunk_store import ChunkStore


def mark(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def build_lookup(docs):
    out = {}
    for r in docs:
        doc_id = str(r.get("acn_num_ACN", "")).strip()
        if not doc_id:
            continue
        out[doc_id] = (r.get("Report 1_Narrative") or "").strip()
    return out


def run_query(pipeline, lookup, query):
    out = pipeline.search(query)

    print(f"\nQuery: {query}")
    print(f"Used query: {out.used_query}")
    print(f"Loops: {out.loops} | Best relevance: {out.best_relevance:.3f}\n")

    print("=== ORIGINAL (Hybrid retrieval) ===")
    print("acn_num_ACN\tscore\tsnippet")
    for r in out.initial:
        doc_id = str(r.get("acn_num_ACN", "")).strip()
        score = float(r.get("score", 0.0))
        text = lookup.get(doc_id, "")
        snippet = " ".join(text.split())[:250]
        print(f"{doc_id}\t{score:.3f}\t{snippet}")

    print("\n=== RERANKED (LLM) ===")
    print("acn_num_ACN\trelevance\tsnippet")
    for r in out.final:
        doc_id = str(r.get("acn_num_ACN", "")).strip()
        rel = float(r.get("relevance", 0.0))
        text = lookup.get(doc_id, "")
        snippet = " ".join(text.split())[:250]
        print(f"{doc_id}\t{rel:.3f}\t{snippet}")

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", default=None)
    args = ap.parse_args()

    t0 = time.time()
    mark("1) Load ASRS dataset")
    ds     = load_dataset("elihoole/asrs-aviation-reports")
    docs   = ds["train"]
    lookup = build_lookup(docs)
    mark(f"   done (+{time.time()-t0:.1f}s) docs={len(docs)}")

    mark("2) Init BM25 + Semantic + Hybrid fusion")
    bm25.init(docs)
    semantic.init(docs)
    hybrid.init(bm25_service=bm25, semantic_service=semantic)
    mark(f"   done (+{time.time()-t0:.1f}s)")

    mark("3) Build ChunkStore")
    cfg   = PipelineConfig()
    store = ChunkStore(chunk_size=cfg.chunk_size, overlap=cfg.overlap)
    mark("   ChunkStore: build_from_semantic_meta()")
    store.build_from_semantic_meta(semantic.semantic_index.meta)
    mark(f"   meta done (+{time.time()-t0:.1f}s)")
    mark("   ChunkStore: build_from_work() (slow)")
    store.build_from_work(docs)
    mark(f"   work done (+{time.time()-t0:.1f}s)")
    mark(f"   ChunkStore done (+{time.time()-t0:.1f}s)")

    mark("4) Create pipeline components")
    llm      = build_llm()
    refiner  = QueryRefiner(llm)
    reranker = LLMReranker(llm, threshold=cfg.accept_threshold)
    pipeline = SearchEnginePipeline(refiner, hybrid, reranker, store, cfg)
    mark(f"   done (+{time.time()-t0:.1f}s)")

    mark("5) (type a query or 'quit' to exit)")
    if args.query:
        run_query(pipeline, lookup, args.query)

    while True:
        try:
            q = input("\nEnter query (or 'stop'): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nstop")
            break

        if not q:
            continue
        if q.lower() in ("stop", "quit", "exit"):
            break

        run_query(pipeline, lookup, q)

    mark("END")


if __name__ == "__main__":
    main()