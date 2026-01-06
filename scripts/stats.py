#!/usr/bin/env python3
import sys
from pathlib import Path

# Make project root importable when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sqlite3
from collections import Counter
from typing import Dict, Tuple

from src.kb.config import DB_PATH
from src.kb.store.db import get_conn, init_db


def _fmt_int(n: int) -> str:
    return f"{n:,}"


def main() -> int:
    conn = get_conn(DB_PATH)
    init_db(conn)

    # Basic counts
    files = conn.execute("SELECT COUNT(*) AS c FROM files").fetchone()["c"]
    chunks = conn.execute("SELECT COUNT(*) AS c FROM chunks").fetchone()["c"]

    # FTS exists?
    fts_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='chunks_fts'"
    ).fetchone() is not None

    # Embeddings stats (table may not exist yet)
    emb_table_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='embeddings'"
    ).fetchone() is not None

    embs = 0
    emb_model_dims: Dict[Tuple[str, int], int] = {}
    bad_blobs = 0

    if emb_table_exists:
        embs = conn.execute("SELECT COUNT(*) AS c FROM embeddings").fetchone()["c"]
        rows = conn.execute(
            "SELECT model, dims, length(vec) AS nbytes FROM embeddings"
        ).fetchall()
        ctr = Counter()
        for r in rows:
            model = str(r["model"])
            dims = int(r["dims"])
            nbytes = int(r["nbytes"])
            ctr[(model, dims)] += 1
            if nbytes != dims * 4:
                bad_blobs += 1
        emb_model_dims = dict(ctr)

    # Clusters stats (optional)
    clusters_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='clusters'"
    ).fetchone() is not None

    clusters = 0
    members = 0
    top_clusters = []
    if clusters_exists:
        clusters = conn.execute("SELECT COUNT(*) AS c FROM clusters").fetchone()["c"]
        members = conn.execute("SELECT COUNT(*) AS c FROM cluster_members").fetchone()["c"]
        top_clusters = conn.execute(
            """
            SELECT id, name, size, method, k
            FROM clusters
            ORDER BY size DESC
            LIMIT 10
            """
        ).fetchall()

    # Print summary
    print("📊 Track3 KB — System Statistics")
    print("=" * 72)
    print(f"DB: {DB_PATH}")
    print("-" * 72)

    print("Core tables")
    print(f"  files:  {_fmt_int(files)}")
    print(f"  chunks: {_fmt_int(chunks)}")
    print(f"  FTS:    {'YES' if fts_exists else 'NO'}")
    print("-" * 72)

    print("Embeddings")
    if not emb_table_exists:
        print("  embeddings table: NO (run scripts/build_embeddings.py)")
    else:
        cov = f"{embs}/{chunks}" if chunks else "0/0"
        pct = (embs / chunks * 100.0) if chunks else 0.0
        print(f"  rows:       {_fmt_int(embs)}")
        print(f"  coverage:   {cov}  ({pct:.1f}%)")
        print(f"  bad blobs:  {_fmt_int(bad_blobs)} (expected 0)")
        if emb_model_dims:
            print("  by model & dims:")
            for (m, d), c in sorted(emb_model_dims.items(), key=lambda x: (-x[1], x[0][0], x[0][1])):
                print(f"    - {m}  dims={d}: {_fmt_int(c)}")
    print("-" * 72)

    print("Clusters")
    if not clusters_exists:
        print("  clusters table: NO (apply schema + run scripts/build_clusters.py)")
    else:
        print(f"  clusters:        {_fmt_int(clusters)}")
        print(f"  memberships:     {_fmt_int(members)}")
        cov = (members / chunks * 100.0) if chunks else 0.0
        print(f"  member coverage: {cov:.1f}% (cluster_members/chunks)")
        if top_clusters:
            print("  top clusters (by size):")
            for r in top_clusters:
                print(f"    - id={r['id']}  size={r['size']}  name={r['name']}  ({r['method']}, k={r['k']})")

    print("=" * 72)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
