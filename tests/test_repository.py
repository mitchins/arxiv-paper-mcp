from __future__ import annotations

import sqlite3

from core.repository import PaperRepository


def test_repository_search_and_lookup(tmp_path) -> None:
    db_path = tmp_path / "arxiv.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE papers (
            id TEXT PRIMARY KEY,
            title TEXT,
            abstract TEXT,
            authors TEXT,
            categories TEXT,
            update_date TEXT
        );
        CREATE VIRTUAL TABLE papers_fts USING fts5(
            title,
            abstract,
            content='papers',
            content_rowid='rowid'
        );
        INSERT INTO papers (id, title, abstract, authors, categories, update_date)
        VALUES ('1234.56789', 'Transformer Retrieval', 'Sparse autoencoder interpretability', 'A. Author', 'cs.IR', '2026-03-29');
        INSERT INTO papers_fts(rowid, title, abstract)
        SELECT rowid, title, abstract FROM papers;
        """
    )
    conn.commit()
    conn.close()

    repo = PaperRepository(db_path)
    repo.connect()
    try:
        rows = repo.search('"Transformer"', 5)
        assert len(rows) == 1
        assert rows[0].id == "1234.56789"

        paper = repo.get_by_id("1234.56789")
        assert paper is not None
        assert paper.title == "Transformer Retrieval"
    finally:
        repo.close()
