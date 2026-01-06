#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import sqlite3
import struct
from typing import List, Tuple

from src.kb.config import DB_PATH
from src.kb.store.db import get_conn, init_db
from src.kb.embed.openai_embed import embed_texts, DEFAULT_MODEL


def pack_f32(vec: List[float]) -> bytes:
    # pack as little-endian float32
    return struct.pack("<%sf" % len(vec), *vec)


def fetch_unembedded(conn: sqlite3.Connection, limit: int) -> List[Tuple[int, str]]:
    rows = conn.execute(
        """
        SELECT c.id AS chunk_id, c.content AS content
        FROM chunks c
        LEFT JOIN embeddings e ON e.chunk_id = c.id
        WHERE e.chunk_id IS NULL
        ORDER BY c.id
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [(int(r["chunk_id"]), str(r["content"])) for r in rows]


def insert_embeddings(conn: sqlite3.Connection, items: List[Tuple[int, bytes]], model: str, dims: int) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO embeddings(chunk_id, model, dims, vec)
        VALUES (?, ?, ?, ?)
        """,
        [(cid, model, dims, blob) for (cid, blob) in items],
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--max", type=int, default=10_000, help="max chunks to embed this run")
    args = ap.parse_args()

    conn = get_conn(DB_PATH)
    init_db(conn)

    done = 0
    while done < args.max:
        todo = fetch_unembedded(conn, limit=min(args.batch, args.max - done))
        if not todo:
            break

        ids = [cid for cid, _ in todo]
        texts = [t for _, t in todo]

        embs = embed_texts(texts, model=args.model)
        dims = len(embs[0])

        blobs = [(cid, pack_f32(vec)) for cid, vec in zip(ids, embs)]
        insert_embeddings(conn, blobs, model=args.model, dims=dims)

        conn.commit()
        done += len(todo)
        print(f"Embedded: {done} chunks (latest dims={dims})")

    conn.close()
    print("✅ build_embeddings finished.")


if __name__ == "__main__":
    main()
