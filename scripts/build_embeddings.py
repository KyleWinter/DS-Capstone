#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import sqlite3
from typing import List, Tuple, Dict, Any

import numpy as np

from src.kb.config import DB_PATH
from src.kb.store.db import get_conn, init_db
from src.kb.embed.openai_embed import embed_texts, DEFAULT_MODEL


def pack_f32(vec: List[float]) -> bytes:
    # Fast + safe: float32 little-endian bytes
    return np.asarray(vec, dtype=np.float32).tobytes()


def fetch_unembedded(conn: sqlite3.Connection, model: str, limit: int) -> List[Tuple[int, str]]:
    """
    Fetch chunks that do NOT have embeddings for the given model.
    """
    rows = conn.execute(
        """
        SELECT c.id AS chunk_id, c.content AS content
        FROM chunks c
        LEFT JOIN embeddings e
          ON e.chunk_id = c.id AND e.model = ?
        WHERE e.chunk_id IS NULL
        ORDER BY c.id
        LIMIT ?
        """,
        (model, limit),
    ).fetchall()
    return [(int(r["chunk_id"]), str(r["content"])) for r in rows]


def insert_embeddings(
    conn: sqlite3.Connection,
    items: List[Tuple[int, bytes]],
    model: str,
    dims: int,
) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO embeddings(chunk_id, model, dims, vec)
        VALUES (?, ?, ?, ?)
        """,
        [(int(cid), str(model), int(dims), blob) for (cid, blob) in items],
    )


def _set_sqlite_pragmas(conn: sqlite3.Connection) -> None:
    # Optional but helpful for batch ingestion
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")


def _unpack_embed_result(res: Dict[str, Any]) -> Tuple[str, int, List[List[float]]]:
    """
    embed_texts returns:
      {"model": str, "dims": int, "embeddings": List[List[float]]}
    """
    if not isinstance(res, dict) or "embeddings" not in res:
        raise RuntimeError(f"Unexpected embed_texts return type: {type(res)}")
    embs = res["embeddings"]
    model_used = str(res.get("model", ""))
    dims = int(res.get("dims") or (len(embs[0]) if embs else 0))
    return model_used, dims, embs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--max", type=int, default=10_000, help="max chunks to embed this run")
    args = ap.parse_args()

    conn = get_conn(DB_PATH)
    init_db(conn)
    _set_sqlite_pragmas(conn)

    done = 0
    while done < args.max:
        todo = fetch_unembedded(conn, model=args.model, limit=min(args.batch, args.max - done))
        if not todo:
            break

        ids = [cid for cid, _ in todo]
        texts = [t for _, t in todo]

        # ✅ embed_texts returns dict (model/dims/embeddings)
        res = embed_texts(texts, model=args.model, batch_size=args.batch)
        model_used, dims, embs = _unpack_embed_result(res)

        if not embs or len(embs) != len(texts):
            raise RuntimeError(
                f"Embedding API returned bad result: got {len(embs) if embs else 0}, expected {len(texts)}"
            )

        if dims <= 0:
            raise RuntimeError("Embedding dims is invalid (<=0).")

        # (Optional sanity check)
        if any(len(v) != dims for v in embs):
            raise RuntimeError("Inconsistent embedding dims within a batch")

        blobs = [(cid, pack_f32(vec)) for cid, vec in zip(ids, embs)]

        # One transaction per batch
        with conn:
            insert_embeddings(conn, blobs, model=model_used or args.model, dims=dims)

        done += len(todo)
        print(f"Embedded: {done} chunks (model={model_used or args.model}, dims={dims})")

    conn.close()
    print("✅ build_embeddings finished.")


if __name__ == "__main__":
    main()
