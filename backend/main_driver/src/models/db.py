import os
import sqlite3
from contextlib import contextmanager


DB_PATH = os.environ.get("SQLITE_DB_PATH", "/tmp/aviation_safety.db")


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


@contextmanager
def get_connection():
    _ensure_parent_dir(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                chunk_id INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                source TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(doc_id, chunk_id)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                chunk_id INTEGER,
                feedback_value TEXT NOT NULL CHECK(feedback_value IN ('up', 'down')),
                query_text TEXT,
                mode TEXT,
                use_qe INTEGER NOT NULL DEFAULT 0,
                use_qe_judge INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (doc_id, chunk_id) REFERENCES chunks(doc_id, chunk_id)
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_feedback_doc_id ON feedback(doc_id);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);"
        )


def upsert_chunk(doc_id: str, chunk_id: int, chunk_text: str, source: str | None = None) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chunks (doc_id, chunk_id, chunk_text, source)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(doc_id, chunk_id) DO UPDATE SET
                chunk_text = excluded.chunk_text,
                source = excluded.source;
            """,
            (doc_id, chunk_id, chunk_text, source),
        )


def insert_feedback(
    doc_id: str,
    feedback_value: str,
    chunk_id: int | None = None,
    query_text: str | None = None,
    mode: str | None = None,
    use_qe: bool = False,
    use_qe_judge: bool = False,
    notes: str | None = None,
) -> int:
    with get_connection() as conn:
        payload = (
            doc_id,
            chunk_id,
            feedback_value,
            query_text,
            mode,
            int(use_qe),
            int(use_qe_judge),
            notes,
        )
        try:
            cur = conn.execute(
                """
                INSERT INTO feedback (
                    doc_id, chunk_id, feedback_value, query_text, mode, use_qe, use_qe_judge, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                payload,
            )
        except sqlite3.IntegrityError:
            # If chunk reference doesn't exist yet, store feedback at doc level.
            cur = conn.execute(
                """
                INSERT INTO feedback (
                    doc_id, chunk_id, feedback_value, query_text, mode, use_qe, use_qe_judge, notes
                )
                VALUES (?, NULL, ?, ?, ?, ?, ?, ?);
                """,
                (
                    doc_id,
                    feedback_value,
                    query_text,
                    mode,
                    int(use_qe),
                    int(use_qe_judge),
                    notes,
                ),
            )
        return int(cur.lastrowid)


def list_feedback(limit: int = 100) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, doc_id, chunk_id, feedback_value, query_text, mode, use_qe, use_qe_judge, notes, created_at
            FROM feedback
            ORDER BY id DESC
            LIMIT ?;
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_chunks(limit: int = 100) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, doc_id, chunk_id, chunk_text, source, created_at
            FROM chunks
            ORDER BY id DESC
            LIMIT ?;
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_db_summary() -> dict:
    with get_connection() as conn:
        chunk_count = conn.execute("SELECT COUNT(*) AS c FROM chunks;").fetchone()["c"]
        feedback_count = conn.execute("SELECT COUNT(*) AS c FROM feedback;").fetchone()["c"]
    return {
        "db_path": DB_PATH,
        "chunks": int(chunk_count),
        "feedback": int(feedback_count),
    }
