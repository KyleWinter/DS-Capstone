from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class SuggestItem:
    chunk_id: int
    file_path: str
    heading: str
    preview: str
    score: float


@dataclass(frozen=True)
class ClusterSuggestion:
    cluster_id: int
    name: str
    score: float   # normalized vote ratio


def _preview(text: str, n: int = 180) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text[:n] + ("…" if len(text) > n else "")


def _fetch_chunk(conn: sqlite3.Connection, chunk_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT id, file_path, COALESCE(heading,'') AS heading, content FROM chunks WHERE id=?",
        (chunk_id,),
    ).fetchone()


def _fetch_embedding(conn: sqlite3.Connection, chunk_id: int) -> Optional[np.ndarray]:
    """
    Load one embedding vector (float32) from DB.
    Assumes embeddings.vec is a float32 bytes blob.
    """
    row = conn.execute(
        "SELECT vec, dims FROM embeddings WHERE chunk_id=? ORDER BY rowid DESC LIMIT 1",
        (chunk_id,),
    ).fetchone()
    if not row:
        return None
    vec_bytes = row["vec"]
    dims = int(row["dims"])
    v = np.frombuffer(vec_bytes, dtype=np.float32)
    if v.size != dims:
        return None
    return v


def _fetch_all_embeddings(conn: sqlite3.Connection) -> Tuple[np.ndarray, np.ndarray]:
    """
    Returns (chunk_ids, matrix):
      chunk_ids: (N,) int64
      matrix: (N, D) float32
    """
    rows = conn.execute("SELECT chunk_id, vec, dims FROM embeddings").fetchall()
    if not rows:
        return np.array([], dtype=np.int64), np.zeros((0, 0), dtype=np.float32)

    dims = int(rows[0]["dims"])
    ids = np.empty((len(rows),), dtype=np.int64)
    mat = np.empty((len(rows), dims), dtype=np.float32)

    for i, r in enumerate(rows):
        ids[i] = int(r["chunk_id"])
        v = np.frombuffer(r["vec"], dtype=np.float32)
        if v.size != dims:
            raise ValueError(f"Bad embedding blob for chunk_id={ids[i]}: got {v.size}, expected {dims}")
        mat[i] = v

    return ids, mat


def related_by_cluster(conn: sqlite3.Connection, chunk_id: int, k: int = 10) -> List[SuggestItem]:
    """
    Recommend other chunks in the same cluster as `chunk_id`.
    Requires `cluster_members` and `clusters` to exist (build_clusters.py).
    """
    row = conn.execute(
        "SELECT cluster_id FROM cluster_members WHERE chunk_id=?",
        (chunk_id,),
    ).fetchone()
    if not row:
        return []

    cluster_id = int(row["cluster_id"])
    rows = conn.execute(
        """
        SELECT c.id AS chunk_id, c.file_path, COALESCE(c.heading,'') AS heading, c.content
        FROM cluster_members m
        JOIN chunks c ON c.id = m.chunk_id
        WHERE m.cluster_id=? AND c.id != ?
        ORDER BY c.id
        LIMIT ?
        """,
        (cluster_id, chunk_id, k),
    ).fetchall()

    out: List[SuggestItem] = []
    for r in rows:
        out.append(
            SuggestItem(
                chunk_id=int(r["chunk_id"]),
                file_path=str(r["file_path"]),
                heading=str(r["heading"]),
                preview=_preview(str(r["content"])),
                score=1.0,
            )
        )
    return out


def related_by_embedding(conn: sqlite3.Connection, chunk_id: int, k: int = 10) -> List[SuggestItem]:
    """
    Recommend by nearest neighbors in embedding space (cosine similarity).
    Uses brute-force cosine similarity over all embeddings (fine for ~10k scale demo).
    """
    q = _fetch_embedding(conn, chunk_id)
    if q is None:
        return []

    ids, mat = _fetch_all_embeddings(conn)
    if mat.size == 0:
        return []

    # normalize for fast cosine
    qn = q / (np.linalg.norm(q) + 1e-12)
    mn = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12)

    sims = mn @ qn  # (N,)

    # exclude self
    self_idx = np.where(ids == int(chunk_id))[0]
    if self_idx.size > 0:
        sims[int(self_idx[0])] = -1.0

    top_idx = np.argsort(-sims)[:k]

    out: List[SuggestItem] = []
    for i in top_idx:
        cid = int(ids[i])
        sim = float(sims[i])
        row = _fetch_chunk(conn, cid)
        if not row:
            continue
        out.append(
            SuggestItem(
                chunk_id=cid,
                file_path=str(row["file_path"]),
                heading=str(row["heading"]),
                preview=_preview(str(row["content"])),
                score=sim,
            )
        )
    return out


def suggest_clusters_from_weighted_hits(
    conn: sqlite3.Connection,
    weighted_chunk_ids: List[Tuple[int, float]],
    k: int = 5,
) -> List[ClusterSuggestion]:
    """
    Given evidence chunks (chunk_id, weight), vote for clusters.
    Requires: cluster_members, clusters.

    score is normalized: cluster_weight / total_weight.
    """
    if not weighted_chunk_ids:
        return []

    chunk_ids = [cid for cid, _ in weighted_chunk_ids]
    weight_map = {int(cid): float(w) for cid, w in weighted_chunk_ids}

    qmarks = ",".join(["?"] * len(chunk_ids))
    rows = conn.execute(
        f"SELECT chunk_id, cluster_id FROM cluster_members WHERE chunk_id IN ({qmarks})",
        chunk_ids,
    ).fetchall()
    if not rows:
        return []

    score_by_cluster: Dict[int, float] = {}
    for r in rows:
        cid = int(r["chunk_id"])
        cl = int(r["cluster_id"])
        score_by_cluster[cl] = score_by_cluster.get(cl, 0.0) + weight_map.get(cid, 1.0)

    total = sum(score_by_cluster.values()) or 1.0
    top = sorted(score_by_cluster.items(), key=lambda x: x[1], reverse=True)[:k]

    out: List[ClusterSuggestion] = []
    for cluster_id, sc in top:
        c = conn.execute(
            "SELECT id, COALESCE(name,'') AS name FROM clusters WHERE id=?",
            (cluster_id,),
        ).fetchone()
        if not c:
            continue
        out.append(
            ClusterSuggestion(
                cluster_id=int(c["id"]),
                name=str(c["name"]),
                score=float(sc / total),
            )
        )
    return out


def suggest_clusters_from_chunk_hits(
    conn: sqlite3.Connection,
    chunk_ids: List[int],
    k: int = 5,
) -> List[ClusterSuggestion]:
    """
    Convenience wrapper: unweighted voting.
    """
    weighted = [(int(cid), 1.0) for cid in chunk_ids]
    return suggest_clusters_from_weighted_hits(conn, weighted, k=k)
