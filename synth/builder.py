import time
import pandas as pd
from tqdm import tqdm

from .cache import JSONLCache
from .llm import LLMQueryGenerator
from .mining import MetadataNeighborMiner


class IRDatasetBuilder:

    def __init__(self, cfg, loader):
        self.cfg    = cfg
        self.loader = loader
        self.cache  = JSONLCache(cfg.cache_path)
        self.llm    = LLMQueryGenerator(cfg)
        self.meta   = MetadataNeighborMiner(cfg, loader=loader)

    def fit_corpus(self, corpus_df):
        self.meta.fit(corpus_df)

    def _ensure_queries_cached(self, seed_df, cache_key_prefix, sleep_s):
        to_make = []

        for _, row in seed_df.iterrows():
            seed_id   = str(row[self.cfg.id_col])
            cache_key = f"{cache_key_prefix}{seed_id}"
            if self.cache.get(cache_key) is not None:
                continue

            rec = self.loader.build_record(row)
            to_make.append((cache_key, rec["record_json"], self.cfg.queries_per_doc))

        if not to_make:
            return

        if self.cfg.use_openai_batch:
            reqs    = self.llm.build_batch_requests(to_make)
            results = self.llm.run_batch_and_collect(reqs)
            for cache_key, qobjs in results.items():
                if qobjs:
                    self.cache.set(cache_key, qobjs)
        else:
            for cache_key, record_json, n in to_make:
                qobjs = self.llm.generate(record_json, n=n)
                self.cache.set(cache_key, qobjs)
                if sleep_s > 0:
                    time.sleep(sleep_s)

    def build(self, corpus_df, seed_df, max_docs=None, sleep_s=0.0, cache_key_prefix=""):
        if max_docs is not None:
            seed_df = seed_df.head(max_docs).copy()

        self.fit_corpus(corpus_df)
        self._ensure_queries_cached(seed_df, cache_key_prefix=cache_key_prefix, sleep_s=sleep_s)

        queries_rows = []
        qrels_rows   = []

        for _, row in seed_df.iterrows():
            seed_id   = str(row[self.cfg.id_col])
            cache_key = f"{cache_key_prefix}{seed_id}"
            qobjs     = self.cache.get(cache_key) or []

            for qi, qobj in enumerate(qobjs):
                qtext = str(qobj.get("query", "")).strip()
                if not qtext:
                    continue

                query_id = f"{seed_id}_q{qi}"

                queries_rows.append({
                    "query_id"   : query_id,
                    "seed_doc_id": seed_id,
                    "query"      : qtext,
                    "style"      : qobj.get("style", ""),
                    "used_fields": qobj.get("used_fields", []),
                    "facets"     : qobj.get("facets", {}) or {}
                })

                # rel=2
                qrels_rows.append({"query_id": query_id, "doc_id": seed_id, "relevance": self.cfg.seed_rel})

                # rel=1
                meta_pos = self.meta.neighbors(row, k=self.cfg.meta_pos_per_query)
                for did in meta_pos:
                    if str(did) == seed_id:
                        continue
                    qrels_rows.append({"query_id": query_id, "doc_id": str(did), "relevance": 1})

        queries_df = pd.DataFrame(queries_rows)
        qrels_df   = pd.DataFrame(qrels_rows)
        if len(qrels_df) > 0:
            qrels_df = qrels_df.groupby(["query_id", "doc_id"], as_index=False)["relevance"].max()

        corpus_export = self.loader.build_corpus_df(corpus_df)
        return queries_df, qrels_df, corpus_export


    def finalize_from_cache(self, corpus_df, seed_df, max_docs=None, cache_key_prefix=""):
        if max_docs is not None:
            seed_df = seed_df.head(max_docs).copy()

        self.fit_corpus(corpus_df)

        queries_rows = []
        qrels_rows   = []

        for _, row in tqdm(seed_df.iterrows(), total=len(seed_df), desc="Building qrels"):
            seed_id   = str(row[self.cfg.id_col])
            cache_key = f"{cache_key_prefix}{seed_id}"
            qobjs     = self.cache.get(cache_key) or []

            for qi, qobj in enumerate(qobjs):
                qtext = str(qobj.get("query", "")).strip()
                if not qtext:
                    continue

                query_id = f"{seed_id}_q{qi}"
                queries_rows.append({
                    "query_id"   : query_id,
                    "seed_doc_id": seed_id,
                    "query"      : qtext,
                    "style"      : qobj.get("style", ""),
                    "used_fields": qobj.get("used_fields", []),
                    "facets"     : qobj.get("facets", {}) or {},
                })

                # rel=2
                qrels_rows.append({"query_id": query_id, "doc_id": seed_id, "relevance": self.cfg.seed_rel})

                # rel=1
                meta_pos = self.meta.neighbors_with_rels(row, k=self.cfg.meta_pos_per_query)
                for did, rel in meta_pos:
                    if str(did) == seed_id:
                        continue
                    qrels_rows.append({"query_id": query_id, "doc_id": str(did), "relevance": int(rel)})

        queries_df = pd.DataFrame(queries_rows)
        qrels_df   = pd.DataFrame(qrels_rows)
        if len(qrels_df) > 0:
            qrels_df = qrels_df.groupby(["query_id", "doc_id"], as_index=False)["relevance"].max()

        corpus_export = self.loader.build_corpus_df(corpus_df)
        return queries_df, qrels_df, corpus_export