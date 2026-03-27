"""Build the SQLite FTS5 index from the Kaggle arXiv JSONL dataset.

Usage:
    python -m scripts.build_index [--jsonl PATH] [--db PATH] [--batch-size N]

Streams the JSONL file line-by-line so memory usage stays constant regardless
of dataset size.
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
import time
from pathlib import Path

import orjson

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BATCH_SIZE = 10_000

INSERT_PAPER = """
    INSERT OR IGNORE INTO papers (id, title, abstract, authors, categories, update_date)
    VALUES (?, ?, ?, ?, ?, ?)
"""

INSERT_FTS = """
    INSERT INTO papers_fts (rowid, title, abstract)
    SELECT rowid, title, abstract FROM papers
    WHERE id = ?
"""


def _authors_to_str(authors_raw: object) -> str:
    """Convert the authors field to a comma-separated string."""
    if isinstance(authors_raw, list):
        return ", ".join(str(a) for a in authors_raw)
    if isinstance(authors_raw, str):
        return authors_raw
    return ""


def _parse_row(raw: bytes) -> tuple[str, str, str, str, str, str] | None:
    """Parse a JSONL line into (id, title, abstract, authors, categories, update_date)."""
    try:
        obj = orjson.loads(raw)
    except orjson.JSONDecodeError:
        return None

    paper_id = obj.get("id")
    if not paper_id or not isinstance(paper_id, str):
        return None

    return (
        paper_id.strip(),
        (obj.get("title") or "").strip(),
        (obj.get("abstract") or "").strip(),
        _authors_to_str(obj.get("authors", "")),
        (obj.get("categories") or "").strip(),
        (obj.get("update_date") or "").strip(),
    )


def build_index(jsonl_path: Path, db_path: Path, batch_size: int = BATCH_SIZE) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")

    # Create schema
    conn.executescript("""
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
    """)

    total = 0
    skipped = 0
    batch: list[tuple[str, str, str, str, str, str]] = []
    t0 = time.perf_counter()

    log.info("Reading %s ...", jsonl_path)

    with open(jsonl_path, "rb") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parsed = _parse_row(line)
            if parsed is None:
                skipped += 1
                continue

            batch.append(parsed)

            if len(batch) >= batch_size:
                _flush_batch(conn, batch)
                total += len(batch)
                batch.clear()
                if total % 100_000 == 0:
                    log.info("  %d rows ingested ...", total)

    if batch:
        _flush_batch(conn, batch)
        total += len(batch)

    log.info("Running ANALYZE ...")
    conn.execute("ANALYZE")
    conn.commit()
    conn.close()

    elapsed = time.perf_counter() - t0
    log.info(
        "Done. %d papers indexed, %d rows skipped, %.1fs elapsed.",
        total,
        skipped,
        elapsed,
    )


def _flush_batch(conn: sqlite3.Connection, batch: list[tuple[str, str, str, str, str, str]]) -> None:
    cur = conn.cursor()
    for row in batch:
        cur.execute(INSERT_PAPER, row)
        # Only insert into FTS if the paper was actually inserted (not a dup)
        if cur.rowcount > 0:
            cur.execute(INSERT_FTS, (row[0],))
    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build arXiv FTS5 index from JSONL")
    parser.add_argument("--jsonl", type=Path, default=Path("./data/arxiv.jsonl"))
    parser.add_argument("--db", type=Path, default=Path("./data/arxiv.db"))
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = parser.parse_args()

    if not args.jsonl.exists():
        log.error("JSONL file not found: %s", args.jsonl)
        sys.exit(1)

    build_index(args.jsonl, args.db, args.batch_size)


if __name__ == "__main__":
    main()
