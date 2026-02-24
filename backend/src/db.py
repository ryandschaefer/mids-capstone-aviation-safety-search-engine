# SQLite: chunks (for snippet lookup) and optional query_logs
# ----------------------------------------------------------
import os
import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"
_conn: sqlite3.Connection | None = None


def _get_conn():
    global _conn
    if _conn is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(_DB_PATH))
        _conn.row_factory = sqlite3.Row
        _init_schema(_conn)
    return _conn


def _init_schema(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS chunks (
            parent_doc_id TEXT NOT NULL,
            chunk_j INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            PRIMARY KEY (parent_doc_id, chunk_j)
        );
        CREATE TABLE IF NOT EXISTS query_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            query TEXT NOT NULL,
            when_prefix TEXT,
            where_contains TEXT,
            anomaly_contains TEXT,
            result_count INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS relevance_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            query_text TEXT NOT NULL,
            doc_id TEXT NOT NULL,
            relevant INTEGER NOT NULL,
            annotator_id TEXT,
            session_id TEXT
        );
    """)
    conn.commit()


def get_chunk(parent_doc_id: str, chunk_j: int) -> str | None:
    """Return chunk text for (parent_doc_id, chunk_j), or None if not found."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT chunk_text FROM chunks WHERE parent_doc_id = ? AND chunk_j = ?",
        (str(parent_doc_id), int(chunk_j)),
    ).fetchone()
    return row["chunk_text"] if row else None


def insert_chunks(chunk_rows: list[tuple[str, int, str]]):
    """Insert (parent_doc_id, chunk_j, chunk_text). Idempotent (replace if exists)."""
    if not chunk_rows:
        return
    conn = _get_conn()
    conn.executemany(
        "REPLACE INTO chunks (parent_doc_id, chunk_j, chunk_text) VALUES (?, ?, ?)",
        chunk_rows,
    )
    conn.commit()


def log_query(query: str, result_count: int, when_prefix: str | None = None, where_contains: str | None = None, anomaly_contains: str | None = None):
    """Append a query log entry (optional)."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO query_logs (query, when_prefix, where_contains, anomaly_contains, result_count) VALUES (?, ?, ?, ?, ?)",
        (query, when_prefix, where_contains, anomaly_contains, result_count),
    )
    conn.commit()


def insert_feedback(query_text: str, doc_id: str, relevant: bool, annotator_id: str | None = None, session_id: str | None = None):
    """Store one relevance feedback (human-in-the-loop). relevant=True means result was helpful."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO relevance_feedback (query_text, doc_id, relevant, annotator_id, session_id) VALUES (?, ?, ?, ?, ?)",
        (query_text.strip(), str(doc_id).strip(), 1 if relevant else 0, annotator_id, session_id),
    )
    conn.commit()


def close():
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
