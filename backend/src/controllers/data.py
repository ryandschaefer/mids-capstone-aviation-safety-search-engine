from datasets import load_dataset
from ..models import bm25_service as bm25
from .. import db as db
import polars as pl

# Load HuggingFace dataset
ds = load_dataset("elihoole/asrs-aviation-reports")
df: pl.DataFrame = ds["train"].to_polars()

# Load BM25 index
bm25.init(df.to_dicts())


_chunks_populate_started = False

def _populate_chunks_once():
    """Start background population of SQLite chunks (once). First request uses computed snippets."""
    global _chunks_populate_started
    if _chunks_populate_started:
        return
    _chunks_populate_started = True
    import threading
    def _run():
        try:
            row = db._get_conn().execute("SELECT 1 FROM chunks LIMIT 1").fetchone()
            if row:
                return
        except Exception:
            pass
        batch = []
        for d_id in range(len(bm25.meta)):
            parent_id, chunk_j, *_ = bm25.meta[d_id]
            text = bm25.text_lookup.get(str(parent_id)) or ""
            snippet = bm25.get_chunk_snippet(text, int(chunk_j))
            batch.append((str(parent_id), int(chunk_j), snippet))
            if len(batch) >= 5000:
                db.insert_chunks(batch)
                batch = []
        if batch:
            db.insert_chunks(batch)
    threading.Thread(target=_run, daemon=True).start()


def _get_text(row):
    """Same narrative resolution as bm25_service.get_text (for snippet)."""
    t = (row.get("Report 1_Narrative") or "") or (row.get("Report 2_Narrative") or "") or (row.get("Report 1.2_Synopsis") or "")
    return (t or "").strip()


def get_test_data():
    # Return the top 15 records
    return df[:15].to_dicts()


def get_bm25_data(query: str, when_prefix: str | None = None, where_contains: str | None = None, anomaly_contains: str | None = None):
    _populate_chunks_once()  # lazy: fill SQLite chunks on first search
    # Search with BM25 (keep chunk_j for snippet)
    raw_hits = bm25.search(query, 100)
    df_bm25 = pl.DataFrame(raw_hits).unique("parent_doc_id", keep="first")
    # Join with full dataset
    df_with_acn = df.with_columns(pl.col("acn_num_ACN").cast(pl.Utf8).alias("_acn_str"))
    df_results = df_with_acn.join(
        df_bm25,
        left_on="_acn_str",
        right_on="parent_doc_id"
    ).sort("score", descending=True)

    # Apply metadata filters (on full row columns)
    if when_prefix:
        df_results = df_results.filter(
            pl.col("Time_Date").cast(pl.Utf8).str.starts_with(str(when_prefix).strip())
        )
    if where_contains:
        where_val = str(where_contains).strip()
        col_place = "Place_Locale Reference"
        if col_place in df_results.columns:
            df_results = df_results.filter(
                pl.col(col_place).cast(pl.Utf8).str.to_lowercase().str.contains(where_val.lower())
            )
    if anomaly_contains:
        ano_val = str(anomaly_contains).strip().lower()
        col_ano = "Events_Anomaly"
        if col_ano in df_results.columns:
            df_results = df_results.filter(
                pl.col(col_ano).cast(pl.Utf8).str.to_lowercase().str.contains(ano_val)
            )

    out = df_results.drop("_acn_str")
    rows = out.to_dicts()
    # Add snippet (matching chunk text) for frontend to bold; prefer SQLite if available
    for r in rows:
        pid, chunk_j = r.get("parent_doc_id"), r.get("chunk_j", 0)
        snippet = db.get_chunk(pid, chunk_j) if pid is not None else None
        if snippet is None or snippet == "":
            snippet = bm25.get_chunk_snippet(_get_text(r), chunk_j)
        r["snippet"] = snippet or ""
    # Optional: log query for analytics
    try:
        db.log_query(query, len(rows), when_prefix=when_prefix, where_contains=where_contains, anomaly_contains=anomaly_contains)
    except Exception:
        pass
    return rows


def submit_feedback(query_text: str, doc_id: str, relevant: bool, annotator_id: str | None = None, session_id: str | None = None):
    """Store relevance feedback (human-in-the-loop)."""
    db.insert_feedback(query_text, doc_id, relevant, annotator_id=annotator_id, session_id=session_id)
    return {"ok": True}