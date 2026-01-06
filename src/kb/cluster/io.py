from __future__ import annotations

import sqlite3
import struct
from typing import List, Tuple

import numpy as np


def load_embedding_matrix(
    conn: sqlite3.Connection,
    model: str,
) -> Tuple[List[int], np.ndarray]:
    """
    Load (chunk_id, vec) from embeddings table and return:
      - ids: List[int]
      - X: np.ndarray shape (n, d), dtype float32
    """
    rows = conn.execute(
        """
        SELECT chunk_id, dims, vec
        FROM embeddings
        WHERE model = ?
        ORDER BY chunk_id
        """,
        (model,),
    ).fetchall()

    if not rows:
        return [], np.zeros((0, 0), dtype=np.float32)

    dims = int(rows[0]["dims"])
    ids: List[int] = []
    X = np.zeros((len(rows), dims), dtype=np.float32)

    for i, r in enumerate(rows):
        cid = int(r["chunk_id"])
        d = int(r["dims"])
        blob = bytes(r["vec"])
        if d != dims:
            raise ValueError(f"Embedding dims mismatch: got {d}, expected {dims} (chunk_id={cid})")
        if len(blob) != dims * 4:
            raise ValueError(f"Bad embedding blob length: {len(blob)} vs {dims*4} (chunk_id={cid})")

        vec = struct.unpack("<%sf" % dims, blob)
        ids.append(cid)
        X[i, :] = np.array(vec, dtype=np.float32)

    return ids, X
