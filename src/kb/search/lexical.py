from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class LexicalHit:
    chunk_id: int
    file_path: str
    heading: str
    preview: str


def fts_search(conn: sqlite3.Connection, query: str, limit: int = 10) -> List[LexicalHit]:
    """
    Full-text search over chunks_fts (FTS5), returning best matches.

    Notes:
    - Uses snippet() for readable highlights.
    - If you want ranking, you can later use bm25(chunks_fts) ordering.
    """
    q = query.strip()
    if not q:
        return []

    rows = conn.execute(
        """
        SELECT
          c.id AS chunk_id,
          c.file_path AS file_path,
          COALESCE(c.heading, '') AS heading,
          snippet(chunks_fts, 0, '[', ']', '…', 12) AS preview
        FROM chunks_fts
        JOIN chunks c ON c.id = chunks_fts.rowid
        WHERE chunks_fts MATCH ?
        LIMIT ?
        """,
        (q, limit),
    ).fetchall()

    hits: List[LexicalHit] = []
    for r in rows:
        hits.append(
            LexicalHit(
                chunk_id=int(r["chunk_id"]),
                file_path=str(r["file_path"]),
                heading=str(r["heading"]),
                preview=str(r["preview"]),
            )
        )
    return hits


def get_chunk_by_id(conn: sqlite3.Connection, chunk_id: int) -> sqlite3.Row | None:
    """
    Fetch the full chunk record for displaying in CLI.
    """
    return conn.execute(
        """
        SELECT id, file_path, COALESCE(heading,'') AS heading, ordinal, content
        FROM chunks
        WHERE id = ?
        """,
        (chunk_id,),
    ).fetchone()
