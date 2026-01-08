from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import List, Optional

from .text_utils import tokenize_for_fts


@dataclass(frozen=True)
class LexicalHit:
    chunk_id: int
    file_path: str
    heading: str
    preview: str
    score: float  # lower is better for bm25()


# -------------------------
# Query building (safe for FTS MATCH)
# -------------------------

# FTS5 MATCH query has special syntax; keep tokens conservative.
# Remove characters that often break MATCH parsing.
_BAD_CHARS_RE = re.compile(r"""[^\w\u4e00-\u9fff]+""", re.UNICODE)


def _build_match_query(user_query: str) -> str:
    """
    Build a safe FTS5 MATCH query with prefix matching.
    - tokenizes CJK via tokenize_for_fts()
    - splits into tokens
    - builds: "tok1"* AND "tok2"* ...
    This is robust and gives a nice "grep-ish" behavior.
    """
    q = (user_query or "").strip()
    if not q:
        return ""

    # Your tokenizer can expand CJK to spaced tokens
    q = tokenize_for_fts(q)
    # Normalize symbols to spaces
    q = _BAD_CHARS_RE.sub(" ", q).strip()
    if not q:
        return ""

    toks = [t for t in q.split() if t]
    if not toks:
        return ""

    # Quote tokens to avoid MATCH syntax issues; add * for prefix match
    # Example: "deadlock"* AND "java"*
    return " AND ".join([f"\"{t}\"*" for t in toks])


# -------------------------
# FTS search
# -------------------------

def fts_search(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 10,
    *,
    module_id: Optional[int] = None,
    # weights for bm25: content, heading, file_path
    bm25_w_content: float = 1.0,
    bm25_w_heading: float = 0.3,
    bm25_w_file_path: float = 2.0,
    snippet_tokens: int = 16,
) -> List[LexicalHit]:
    """
    Full-text search over chunks_fts (FTS5), returning best matches.

    Improvements:
    - Stable ranking using bm25(chunks_fts, ...)
    - Safer MATCH query building (prefix match, less parse errors)
    - Optional module filter via file_modules
    - Returns bm25 score for downstream hybrid fusion (lower is better)
    """
    match_q = _build_match_query(query)
    if not match_q:
        return []

    # Optional module filter: join file_modules on file_path
    module_join = ""
    module_where = ""
    params: List[object] = []

    if module_id is not None:
        module_join = "JOIN file_modules fm ON fm.file_path = c.file_path"
        module_where = "AND fm.module_id = ?"
        params.append(int(module_id))

    sql = f"""
        SELECT
          c.id AS chunk_id,
          c.file_path AS file_path,
          COALESCE(c.heading, '') AS heading,
          snippet(chunks_fts, 0, '[', ']', '…', ?) AS preview,
          bm25(chunks_fts, ?, ?, ?) AS score
        FROM chunks_fts
        JOIN chunks c ON c.id = chunks_fts.rowid
        {module_join}
        WHERE chunks_fts MATCH ?
        {module_where}
        ORDER BY score ASC
        LIMIT ?
    """

    # params order: snippet_tokens, bm25 weights, match, (module_id?), limit
    full_params: List[object] = [
        int(snippet_tokens),
        float(bm25_w_content),
        float(bm25_w_heading),
        float(bm25_w_file_path),
        match_q,
        *params,
        int(limit),
    ]

    rows = conn.execute(sql, full_params).fetchall()

    hits: List[LexicalHit] = []
    for r in rows:
        hits.append(
            LexicalHit(
                chunk_id=int(r["chunk_id"]),
                file_path=str(r["file_path"]),
                heading=str(r["heading"]),
                preview=str(r["preview"]),
                score=float(r["score"]),
            )
        )
    return hits


def get_chunk_by_id(conn: sqlite3.Connection, chunk_id: int) -> sqlite3.Row | None:
    """
    Fetch the full chunk record for displaying in CLI / API.
    """
    return conn.execute(
        """
        SELECT id, file_path, COALESCE(heading,'') AS heading, ordinal, content
        FROM chunks
        WHERE id = ?
        """,
        (chunk_id,),
    ).fetchone()
