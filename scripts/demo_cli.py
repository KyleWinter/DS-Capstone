#!/usr/bin/env python3
import sys
from pathlib import Path

# Make project root importable when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse

from src.kb.config import DB_PATH
from src.kb.store.db import get_conn, init_db
from src.kb.search.lexical import fts_search, get_chunk_by_id
from src.kb.search.hybrid import hybrid_search


def cmd_search(args: argparse.Namespace) -> int:
    conn = get_conn(DB_PATH)
    init_db(conn)

    hits = fts_search(conn, args.query, limit=args.limit)

    if not hits:
        print("No results.")
        return 0

    print(f"✅ Found {len(hits)} results (showing top {len(hits)}):\n")
    for i, h in enumerate(hits, start=1):
        heading = f" — {h.heading}" if h.heading else ""
        print(f"{i:02d}. chunk_id={h.chunk_id}  {h.file_path}{heading}")
        print(f"    {h.preview.replace(chr(10), ' ')}")
        print()

    return 0


def cmd_hybrid(args: argparse.Namespace) -> int:
    conn = get_conn(DB_PATH)
    init_db(conn)

    hits = hybrid_search(conn, args.query, fts_k=args.fts_k, top_k=args.limit, model=args.model)

    if not hits:
        print("No results.")
        return 0

    print(f"✅ Hybrid results (top {len(hits)}):\n")
    for i, h in enumerate(hits, start=1):
        heading = f" — {h.heading}" if h.heading else ""
        print(f"{i:02d}. chunk_id={h.chunk_id}  score={h.semantic_score:.4f}  {h.file_path}{heading}")
        print(f"    {h.preview.replace(chr(10), ' ')}")
        print()

    return 0


def cmd_clusters(args: argparse.Namespace) -> int:
    conn = get_conn(DB_PATH)
    init_db(conn)

    rows = conn.execute(
        """
        SELECT id, name, size, method, k, created_at
        FROM clusters
        ORDER BY size DESC
        LIMIT ?
        """,
        (args.limit,),
    ).fetchall()

    if not rows:
        print("No clusters. Run: python scripts/build_clusters.py --k 30 --reset")
        return 0

    print(f"✅ Top {len(rows)} clusters:\n")
    for r in rows:
        print(f"- cluster_id={r['id']}  size={r['size']}  name={r['name']}  ({r['method']}, k={r['k']})")
    return 0


def cmd_cluster(args: argparse.Namespace) -> int:
    conn = get_conn(DB_PATH)
    init_db(conn)

    c = conn.execute(
        "SELECT id, name, summary, size FROM clusters WHERE id=?",
        (args.cluster_id,),
    ).fetchone()
    if not c:
        print(f"Cluster not found: {args.cluster_id}")
        return 1

    print(f"cluster_id: {c['id']}")
    print(f"name: {c['name']}")
    print(f"size: {c['size']}")
    if c["summary"]:
        print(f"summary: {c['summary']}")
    print("-" * 80)

    rows = conn.execute(
        """
        SELECT c.id AS chunk_id, c.file_path, COALESCE(c.heading,'') AS heading,
               substr(replace(c.content, char(10), ' '), 1, 160) AS preview
        FROM cluster_members m
        JOIN chunks c ON c.id = m.chunk_id
        WHERE m.cluster_id = ?
        ORDER BY c.id
        LIMIT ?
        """,
        (args.cluster_id, args.limit),
    ).fetchall()

    for i, r in enumerate(rows, 1):
        heading = f" — {r['heading']}" if r["heading"] else ""
        print(f"{i:02d}. chunk_id={r['chunk_id']}  {r['file_path']}{heading}")
        print(f"    {r['preview']}...")
        print()

    return 0


def cmd_related(args: argparse.Namespace) -> int:
    conn = get_conn(DB_PATH)
    init_db(conn)

    row = conn.execute(
        """
        SELECT m.cluster_id, cl.name
        FROM cluster_members m
        JOIN clusters cl ON cl.id = m.cluster_id
        WHERE m.chunk_id = ?
        """,
        (args.chunk_id,),
    ).fetchone()

    if not row:
        print(f"Chunk {args.chunk_id} is not assigned to any cluster. Run build_clusters.py first.")
        return 1

    cluster_id = int(row["cluster_id"])
    cluster_name = str(row["name"])
    print(f"✅ chunk_id={args.chunk_id} belongs to cluster_id={cluster_id}  name={cluster_name}")
    print("-" * 80)

    rows = conn.execute(
        """
        SELECT c.id AS chunk_id, c.file_path, COALESCE(c.heading,'') AS heading,
               substr(replace(c.content, char(10), ' '), 1, 160) AS preview
        FROM cluster_members m
        JOIN chunks c ON c.id = m.chunk_id
        WHERE m.cluster_id = ? AND c.id != ?
        ORDER BY c.id
        LIMIT ?
        """,
        (cluster_id, args.chunk_id, args.limit),
    ).fetchall()

    for i, r in enumerate(rows, 1):
        heading = f" — {r['heading']}" if r["heading"] else ""
        print(f"{i:02d}. chunk_id={r['chunk_id']}  {r['file_path']}{heading}")
        print(f"    {r['preview']}...")
        print()

    return 0


def cmd_show(args: argparse.Namespace) -> int:
    conn = get_conn(DB_PATH)
    init_db(conn)

    row = get_chunk_by_id(conn, args.chunk_id)
    if row is None:
        print(f"Chunk not found: {args.chunk_id}")
        return 1

    print(f"chunk_id: {row['id']}")
    print(f"file_path: {row['file_path']}")
    if row["heading"]:
        print(f"heading: {row['heading']}")
    print(f"ordinal: {row['ordinal']}")
    print("-" * 80)
    print(row["content"])
    print("-" * 80)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="demo_cli", description="Track3 KB demo CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", help="Full-text search (FTS5)")
    p_search.add_argument("query", type=str, help="FTS query string, e.g. transformer OR attention")
    p_search.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")
    p_search.set_defaults(func=cmd_search)

    p_hybrid = sub.add_parser("hybrid", help="Hybrid search: FTS recall + embedding rerank")
    p_hybrid.add_argument("query", type=str, help="Query text")
    p_hybrid.add_argument("--limit", type=int, default=10)
    p_hybrid.add_argument("--fts-k", type=int, default=50, dest="fts_k")
    p_hybrid.add_argument("--model", type=str, default="text-embedding-3-small")
    p_hybrid.set_defaults(func=cmd_hybrid)

    p_clusters = sub.add_parser("clusters", help="List clusters (largest first)")
    p_clusters.add_argument("--limit", type=int, default=10)
    p_clusters.set_defaults(func=cmd_clusters)

    p_cluster = sub.add_parser("cluster", help="Show a cluster and sample members")
    p_cluster.add_argument("cluster_id", type=int)
    p_cluster.add_argument("--limit", type=int, default=10)
    p_cluster.set_defaults(func=cmd_cluster)

    p_related = sub.add_parser("related", help="Show chunks in the same cluster as a given chunk_id")
    p_related.add_argument("chunk_id", type=int)
    p_related.add_argument("--limit", type=int, default=10)
    p_related.set_defaults(func=cmd_related)

    p_show = sub.add_parser("show", help="Show full content of a chunk by id")
    p_show.add_argument("chunk_id", type=int, help="Chunk id")
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
