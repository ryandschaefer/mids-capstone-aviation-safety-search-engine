from dataclasses import dataclass

@dataclass
class BuildConfig:
    dataset_name: str = "elihoole/asrs-aviation-reports"
    id_col: str = "acn_num_ACN"
    narrative_col: str = "Report 1_Narrative"
    synopsis_col: str = "Report 1.2_Synopsis"
    time_col: str = "Time_Date"
    seed: int = 42

    queries_per_doc: int = 2
    openai_model: str = "gpt-5-nano"
    api_key_env: str = "OPENAI_API_KEY"
    cache_path: str = "llm_query_cache.jsonl"

    max_record_chars: int = 7000

    meta_pos_per_query: int = 3
    seed_rel: int = 2

    use_openai_batch: bool = True
    batch_completion_window: str = "24h"
    batch_poll_seconds: float = 5.0

    out_queries_csv: str = "queries.csv"
    out_qrels_csv: str = "qrels.csv"
    out_corpus_csv: str = "corpus.csv"