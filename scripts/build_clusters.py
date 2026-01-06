#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import sqlite3
from collections import defaultdict
from typing import Dict, List

from src.kb.config import DB_PATH
from src.kb.store.db import get_conn, init_db
from src.kb.cluster.io import load_embedding_matrix
from src.kb.cluster.clusterer import kmeans_cluster
from src.kb.cluster.labeler import label_clusters_tfidf


def clear_old_clusters(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM cluster_members")
    conn.execute("DELETE FROM clusters")


def insert_cluster(conn: sqlite3.Connection, method: str, k: int, name: str, summary: str, size: int) -> int:
    cur = conn.execute(
        """
        INSERT INTO clusters(method, k, name, summary, size)
        VALUES (?, ?, ?, ?, ?)
        """,
        (method, k, name, summary, size),
    )
    return int(cur.lastrowid)


def insert_members(conn: sqlite3.Connection, cluster_id: int, chunk_ids: List[int]) -> None:
    conn.executemany(
        """
        INSERT OR IGNORE INTO cluster_members(cluster_id, chunk_id)
        VALUES (?, ?)
        """,
        [(cluster_id, cid) for cid in chunk_ids],
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Build clusters from embeddings and store in SQLite.")
    ap.add_argument("--model", default="text-embedding-3-small")
    ap.add_argument("--k", type=int, default=30, help="Number of clusters for KMeans (default: 30)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--reset", action="store_true", help="Delete existing clusters before insert")
    args = ap.parse_args()

    conn = get_conn(DB_PATH)
    init_db(conn)

    ids, X = load_embedding_matrix(conn, model=args.model)
    if len(ids) == 0:
        raise SystemExit("No embeddings found. Run build_embeddings.py first.")

    print(f"Loaded embeddings: n={len(ids)}, d={X.shape[1]}, model={args.model}")

    res = kmeans_cluster(X, k=args.k, seed=args.seed)
    print(f"KMeans finished: k={res.k}")

    members: Dict[int, List[int]] = defaultdict(list)
    for cid, lab in zip(ids, res.labels):
        members[int(lab)].append(int(cid))

    # label clusters
    labels = label_clusters_tfidf(conn, members)

    if args.reset:
        clear_old_clusters(conn)

    # write to DB
    # map cluster index -> cluster table id
    cluster_id_map: Dict[int, int] = {}

    for cidx, chunk_ids in sorted(members.items(), key=lambda kv: len(kv[1]), reverse=True):
        name, summary = labels.get(cidx, (f"Cluster {cidx}", ""))
        cid_db = insert_cluster(
            conn,
            method="kmeans",
            k=res.k,
            name=name,
            summary=summary,
            size=len(chunk_ids),
        )
        cluster_id_map[cidx] = cid_db
        insert_members(conn, cid_db, chunk_ids)

    conn.commit()
    conn.close()

    print("✅ build_clusters finished.")
    print(f"Clusters inserted: {len(cluster_id_map)}")


if __name__ == "__main__":
    main()
