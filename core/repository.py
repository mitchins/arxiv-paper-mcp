from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from core.models import Paper, SearchResult

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    title TEXT,
    abstract TEXT,
    authors TEXT,
    categories TEXT,
    update_date TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
    title,
    abstract,
    content='papers',
    content_rowid='rowid'
);
"""


class PaperRepository:
    """Synchronous SQLite repository for arXiv paper metadata."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    # -- lifecycle -----------------------------------------------------------

    def _connect_readonly_immutable(self) -> None:
        readonly_uri = f"file:{self._db_path}?mode=ro&immutable=1"
        self._conn = sqlite3.connect(readonly_uri, uri=True, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA query_only = ON")
        self._conn.execute("PRAGMA temp_store = MEMORY")

    def connect(self) -> None:
        if os.getenv("ARXIV_DB_IMMUTABLE", "").lower() in {"1", "true", "yes"}:
            self._connect_readonly_immutable()
            return

        try:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA synchronous = NORMAL")
            self._conn.execute("PRAGMA temp_store = MEMORY")
            return
        except sqlite3.OperationalError:
            # SMB/CIFS mounts can fail read-write/WAL setup; retry read-only.
            self._connect_readonly_immutable()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def ensure_schema(self) -> None:
        assert self._conn is not None
        self._conn.executescript(_SCHEMA_SQL)

    @property
    def conn(self) -> sqlite3.Connection:
        assert self._conn is not None, "Call connect() first"
        return self._conn

    # -- queries -------------------------------------------------------------

    def search(self, query: str, limit: int) -> list[SearchResult]:
        sql = """
            SELECT p.id, p.title,
                   snippet(papers_fts, 1, '[', ']', '...', 20) AS snippet
            FROM papers_fts
            JOIN papers p ON papers_fts.rowid = p.rowid
            WHERE papers_fts MATCH ?
            ORDER BY bm25(papers_fts)
            LIMIT ?
        """
        rows = self.conn.execute(sql, (query, limit)).fetchall()
        return [SearchResult(id=r["id"], title=r["title"], snippet=r["snippet"]) for r in rows]

    def get_by_id(self, arxiv_id: str) -> Paper | None:
        sql = "SELECT id, title, abstract, authors, categories, update_date FROM papers WHERE id = ?"
        row = self.conn.execute(sql, (arxiv_id,)).fetchone()
        if row is None:
            return None
        return Paper(
            id=row["id"],
            title=row["title"],
            abstract=row["abstract"],
            authors=row["authors"],
            categories=row["categories"],
            update_date=row["update_date"],
        )
