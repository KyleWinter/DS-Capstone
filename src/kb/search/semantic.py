from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional

import numpy as np

from src.kb.embed.openai_embed import embed_texts, DEFAULT_MODEL


@dataclass(frozen=True)
class SemanticHit:
    chunk_id: int
    score: float  # cosine similarity


def _fetch_embeddings(
    conn: sqlite3.Connection,
    chunk_ids: List[int],
    model: str,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fetch embeddings for given chunk_ids (for one model).

    Returns:
      ids: (N,) int64
      mat: (N, D) float32
    """
    if not chunk_ids:
        return np.array([], dtype=np.int64), np.zeros((0, 0), dtype=np.float32)

    qmarks = ",".join(["?"] * len(chunk_ids))
    rows = conn.execute(
        f"""
        SELECT chunk_id, vec, dims
        FROM embeddings
        WHERE model = ? AND chunk_id IN ({qmarks})
        """,
        [model, *chunk_ids],
    ).fetchall()

    if not rows:
        return np.array([], dtype=np.int64), np.zeros((0, 0), dtype=np.float32)

    dims0 = int(rows[0]["dims"])
    if dims0 <= 0:
        raise RuntimeError(f"Bad dims in embeddings table: {dims0}")

    ids = np.empty((len(rows),), dtype=np.int64)
    mat = np.empty((len(rows), dims0), dtype=np.float32)

    for i, r in enumerate(rows):
        cid = int(r["chunk_id"])
        dims = int(r["dims"])
        if dims != dims0:
            raise RuntimeError(f"Inconsistent dims for model={model}: {dims} vs {dims0} (chunk_id={cid})")

        v = np.frombuffer(r["vec"], dtype=np.float32)  # zero-copy view
        if v.size != dims0:
            raise RuntimeError(f"Bad embedding blob for chunk_id={cid}: got {v.size}, expected {dims0}")

        ids[i] = cid
        mat[i] = v  # copy into matrix row

    return ids, mat


def _l2_normalize_rows(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12
    return mat / norms


def _embed_query(q: str, model: str) -> np.ndarray:
    """
    Compatible with your embed_texts() that returns dict:
      {"model": ..., "dims": ..., "embeddings": [...]}
    """
    res: Dict[str, Any] = embed_texts([q], model=model, batch_size=1)
    embs = res.get("embeddings") or []
    if len(embs) != 1:
        raise RuntimeError(f"Embedding API returned bad result for query: got {len(embs)}")
    qvec = np.asarray(embs[0], dtype=np.float32)
    if qvec.ndim != 1 or qvec.size == 0:
        raise RuntimeError("Query embedding is empty/invalid")
    return qvec


def semantic_rerank(
    conn: sqlite3.Connection,
    query: str,
    candidate_chunk_ids: List[int],
    model: str = DEFAULT_MODEL,
    top_k: Optional[int] = None,
) -> List[SemanticHit]:
    """
    Rerank candidates by cosine similarity in embedding space.

    Optimizations:
    - zero-copy blob -> float32 via np.frombuffer
    - vectorized cosine (single matmul)
    - optional top_k truncation
    """
    q = (query or "").strip()
    if not q or not candidate_chunk_ids:
        return []

    qvec = _embed_query(q, model=model)

    ids, mat = _fetch_embeddings(conn, candidate_chunk_ids, model=model)
    if mat.size == 0:
        return []

    # cosine: normalize and dot
    qn = qvec / (np.linalg.norm(qvec) + 1e-12)
    mn = _l2_normalize_rows(mat)
    sims = mn @ qn  # (N,)

    order = np.argsort(-sims)  # descending
    if top_k is not None:
        order = order[: int(top_k)]

    return [SemanticHit(chunk_id=int(ids[i]), score=float(sims[i])) for i in order]
