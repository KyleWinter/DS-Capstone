from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Dict, List

from src.kb.search.lexical import LexicalHit, fts_search
from src.kb.search.semantic import semantic_rerank


@dataclass(frozen=True)
class HybridHit:
    chunk_id: int
    file_path: str
    heading: str
    preview: str
    semantic_score: float


def hybrid_search(
    conn: sqlite3.Connection,
    query: str,
    fts_k: int = 50,
    top_k: int = 10,
    model: str = "text-embedding-3-small",
) -> List[HybridHit]:
    q = query.strip()
    if not q:
        return []

    lexical_hits: List[LexicalHit] = fts_search(conn, q, limit=fts_k)
    if not lexical_hits:
        return []

    by_id: Dict[int, LexicalHit] = {h.chunk_id: h for h in lexical_hits}
    candidate_ids = list(by_id.keys())

    reranked = semantic_rerank(conn, q, candidate_ids, model=model)

    out: List[HybridHit] = []
    for s in reranked[:top_k]:
        l = by_id.get(s.chunk_id)
        if not l:
            continue
        out.append(
            HybridHit(
                chunk_id=int(s.chunk_id),
                file_path=l.file_path,
                heading=l.heading,
                preview=l.preview,
                semantic_score=float(s.score),
            )
        )
    return out
