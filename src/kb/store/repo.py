from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from ..search.text_utils import tokenize_for_fts


# ---------- Data Models (lightweight) ----------

@dataclass(frozen=True)
class ChunkRow:
    file_path: str
    content: str
    ordinal: int = 0
    heading: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None


@dataclass(frozen=True)
class SearchHit:
    chunk_id: int
    file_path: str
    heading: str
    preview: str


# ---------- Helpers ----------

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


# ---------- Repository ----------

class KBRepo:
    """
    A thin data-access layer for SQLite.
    Put ALL SQL here, keep the rest of the project clean.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ----- files -----

    def upsert_file(self, path: Path, mtime: float, size_bytes: int, sha256: Optional[str] = None) -> None:
        self.conn.execute(
            """
            INSERT INTO files(path, mtime, size_bytes, sha256)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
              mtime=excluded.mtime,
              size_bytes=excluded.size_bytes,
              sha256=excluded.sha256,
              updated_at=datetime('now')
            """,
            (str(path), mtime, size_bytes, sha256),
        )

    def get_file(self, path: Path) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM files WHERE path = ?",
            (str(path),),
        ).fetchone()

    # ----- chunks -----

    def delete_chunks_by_file(self, file_path: str) -> int:
        # Get chunk IDs to delete from FTS
        chunk_ids = self.conn.execute(
            "SELECT id FROM chunks WHERE file_path = ?", (file_path,)
        ).fetchall()

        # Delete from FTS table
        for row in chunk_ids:
            self.conn.execute(
                "DELETE FROM chunks_fts WHERE rowid = ?", (row['id'],)
            )

        # Delete from chunks table
        cur = self.conn.execute("DELETE FROM chunks WHERE file_path = ?", (file_path,))
        return cur.rowcount

    def insert_chunks(self, chunks: Iterable[ChunkRow]) -> int:
        # Convert to list to allow multiple iterations
        chunk_list = list(chunks)
        if not chunk_list:
            return 0

        # Insert chunks one by one to track row IDs
        inserted_ids = []
        for c in chunk_list:
            cur = self.conn.execute(
                """
                INSERT INTO chunks(file_path, heading, start_line, end_line, ordinal, content, content_len)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (c.file_path, c.heading, c.start_line, c.end_line, c.ordinal, c.content, len(c.content)),
            )
            inserted_ids.append(cur.lastrowid)

        # Insert into FTS table with tokenized content
        fts_rows = []
        for row_id, c in zip(inserted_ids, chunk_list):
            fts_rows.append(
                (
                    row_id,
                    tokenize_for_fts(c.content),
                    tokenize_for_fts(c.heading or ''),
                    c.file_path,
                )
            )

        self.conn.executemany(
            """
            INSERT INTO chunks_fts(rowid, content, heading, file_path)
            VALUES (?, ?, ?, ?)
            """,
            fts_rows,
        )

        return len(chunk_list)

    def count_chunks(self) -> int:
        r = self.conn.execute("SELECT COUNT(*) AS c FROM chunks").fetchone()
        return int(r["c"])

    def count_files(self) -> int:
        r = self.conn.execute("SELECT COUNT(*) AS c FROM files").fetchone()
        return int(r["c"])

    # ----- FTS search -----

    def fts_search(self, query: str, limit: int = 10) -> list[SearchHit]:
        """
        Search FTS table, return best matches with a short preview.
        Uses snippet() for readable highlights.
        """
        # Tokenize query for CJK support
        tokenized_query = tokenize_for_fts(query)

        rows = self.conn.execute(
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
            (tokenized_query, limit),
        ).fetchall()

        hits: list[SearchHit] = []
        for r in rows:
            hits.append(
                SearchHit(
                    chunk_id=int(r["chunk_id"]),
                    file_path=str(r["file_path"]),
                    heading=str(r["heading"]),
                    preview=str(r["preview"]),
                )
            )
        return hits

    # ----- transaction helpers -----

    def commit(self) -> None:
        self.conn.commit()
