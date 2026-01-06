from __future__ import annotations

import sqlite3
import struct
from dataclasses import dataclass
from math import sqrt
from typing import List, Tuple

from src.kb.embed.openai_embed import embed_texts, DEFAULT_MODEL


@dataclass(frozen=True)
class SemanticHit:
    chunk_id: int
    score: float  # cosine similarity


def _unpack_f32(blob: bytes) -> List[float]:
    n = len(blob) // 4
    return list(struct.unpack("<%sf" % n, blob))


def _cosine(a: List[float], b: List[float]) -> float:
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    denom = sqrt(na) * sqrt(nb)
    return dot / denom if denom else 0.0


def _fetch_embeddings(conn: sqlite3.Connection, chunk_ids: List[int], model: str) -> List[Tuple[int, bytes]]:
    if not chunk_ids:
        return []
    qmarks = ",".join(["?"] * len(chunk_ids))
    rows = conn.execute(
        f"""
        SELECT chunk_id, vec
        FROM embeddings
        WHERE model = ? AND chunk_id IN ({qmarks})
        """,
        [model, *chunk_ids],
    ).fetchall()
    return [(int(r["chunk_id"]), bytes(r["vec"])) for r in rows]


def semantic_rerank(
    conn: sqlite3.Connection,
    query: str,
    candidate_chunk_ids: List[int],
    model: str = DEFAULT_MODEL,
) -> List[SemanticHit]:
    """
    Given query text and candidate chunk ids, compute cosine similarity between
    query embedding and stored chunk embeddings, then sort descending.
    """
    q = query.strip()
    if not q or not candidate_chunk_ids:
        return []

    qvec = embed_texts([q], model=model)[0]
    emb_rows = _fetch_embeddings(conn, candidate_chunk_ids, model=model)

    scored: List[SemanticHit] = []
    for cid, blob in emb_rows:
        v = _unpack_f32(blob)
        scored.append(SemanticHit(chunk_id=cid, score=_cosine(qvec, v)))

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored
