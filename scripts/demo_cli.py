#!/usr/bin/env python3
import sys
from pathlib import Path

# Make project root importable when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import sqlite3

from src.kb.config import DB_PATH
from src.kb.store.db import get_conn, init_db
from src.kb.search.lexical import fts_search, get_chunk_by_id

from src.kb.suggest.recommender import (
    related_by_cluster,
    related_by_embedding,
    suggest_clusters_from_chunk_hits,
)


def cmd_search(args: argparse.Namespace) -> int:
    conn = get_conn(DB_PATH)
    init_db(conn)

    hits = fts_search(conn, args.query, limit=args.limit)

    if not hits:
        print("No results.")
        return 0

    print(f"✅ Found {len(hits)} results (showing top {len(hits)}):\n")
    for i, h in enumerate(hits, start=1):
        heading = f" — {h.heading}" if getattr(h, "heading", "") else ""
        print(f"{i:02d}. chunk_id={h.chunk_id}  {h.file_path}{heading}")
        print(f"    {h.preview.replace(chr(10), ' ')}")
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


def cmd_related(args: argparse.Namespace) -> int:
    conn = get_conn(DB_PATH)
    init_db(conn)

    # validate chunk exists
    row = get_chunk_by_id(conn, args.chunk_id)
    if row is None:
        print(f"Chunk not found: {args.chunk_id}")
        return 1

    mode = args.mode.lower()
    if mode == "cluster":
        items = related_by_cluster(conn, args.chunk_id, k=args.limit)
        title = "Same-cluster recommendations"
    elif mode == "embed":
        items = related_by_embedding(conn, args.chunk_id, k=args.limit)
        title = "Embedding-nearest recommendations"
    else:
        print(f"Unknown mode: {args.mode} (use 'cluster' or 'embed')")
        return 2

    if not items:
        print("No recommendations.")
        return 0

    print(f"✅ {title} for chunk_id={args.chunk_id} (top {len(items)}):\n")
    for i, it in enumerate(items, start=1):
        heading = f" — {it.heading}" if it.heading else ""
        score = f"{it.score:.4f}" if mode == "embed" else "-"
        print(f"{i:02d}. chunk_id={it.chunk_id}  score={score}  {it.file_path}{heading}")
        print(f"    {it.preview}")
        print()

    return 0


def cmd_suggest_clusters(args: argparse.Namespace) -> int:
    conn = get_conn(DB_PATH)
    init_db(conn)

    # Use FTS hits as evidence, then vote clusters
    hits = fts_search(conn, args.query, limit=args.fts_k)
    if not hits:
        print("No hits from FTS, cannot suggest clusters.")
        return 0

    chunk_ids = [h.chunk_id for h in hits]
    clusters = suggest_clusters_from_chunk_hits(conn, chunk_ids, k=args.limit)
    if not clusters:
        print("No clusters found for these hits (did you run build_clusters.py?).")
        return 0

    print(f"✅ Suggested clusters for query: {args.query!r}\n")
    for i, c in enumerate(clusters, start=1):
        print(f"{i:02d}. cluster_id={c.cluster_id}  score={c.score:.2f}  name={c.name}")

    return 0


def cmd_clusters(args: argparse.Namespace) -> int:
    conn = get_conn(DB_PATH)
    init_db(conn)

    # Ensure clusters table exists
    ok = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='clusters'"
    ).fetchone()
    if not ok:
        print("No clusters table. Run: python scripts/build_clusters.py --k 30 --reset")
        return 0

    rows = conn.execute(
        """
        SELECT id, COALESCE(name,'') AS name, COALESCE(size,0) AS size, method, k
        FROM clusters
        ORDER BY size DESC, id ASC
        LIMIT ?
        """,
        (args.limit,),
    ).fetchall()

    if not rows:
        print("No clusters yet. Run build_clusters.py first.")
        return 0

    print(f"✅ Top clusters (showing {len(rows)}):\n")
    for i, r in enumerate(rows, start=1):
        print(
            f"{i:02d}. id={r['id']}  size={r['size']}  name={r['name']}  ({r['method']}, k={r['k']})"
        )
    return 0


def cmd_cluster(args: argparse.Namespace) -> int:
    conn = get_conn(DB_PATH)
    init_db(conn)

    # cluster meta
    meta = conn.execute(
        "SELECT id, COALESCE(name,'') AS name, COALESCE(summary,'') AS summary, COALESCE(size,0) AS size "
        "FROM clusters WHERE id=?",
        (args.cluster_id,),
    ).fetchone()
    if not meta:
        print(f"Cluster not found: {args.cluster_id}")
        return 1

    print(f"cluster_id: {meta['id']}")
    print(f"name: {meta['name']}")
    print(f"size: {meta['size']}")
    if meta["summary"]:
        print(f"summary: {meta['summary']}")
    print("-" * 80)

    rows = conn.execute(
        """
        SELECT c.id AS chunk_id, c.file_path, COALESCE(c.heading,'') AS heading, c.content
        FROM cluster_members m
        JOIN chunks c ON c.id = m.chunk_id
        WHERE m.cluster_id=?
        ORDER BY c.id
        LIMIT ?
        """,
        (args.cluster_id, args.limit),
    ).fetchall()

    if not rows:
        print("(no members)")
        return 0

    for i, r in enumerate(rows, start=1):
        heading = f" — {r['heading']}" if r["heading"] else ""
        preview = str(r["content"]).replace("\n", " ").strip()
        if len(preview) > 180:
            preview = preview[:180] + "…"
        print(f"{i:02d}. chunk_id={r['chunk_id']}  {r['file_path']}{heading}")
        print(f"    {preview}")
        print()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="demo_cli", description="Track3 KB demo CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", help="Full-text search (FTS5)")
    p_search.add_argument("query", type=str, help="FTS query string, e.g. transformer OR attention")
    p_search.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")
    p_search.set_defaults(func=cmd_search)

    p_show = sub.add_parser("show", help="Show full content of a chunk by id")
    p_show.add_argument("chunk_id", type=int, help="Chunk id")
    p_show.set_defaults(func=cmd_show)

    p_related = sub.add_parser("related", help="Recommend related chunks for a given chunk id")
    p_related.add_argument("chunk_id", type=int, help="Chunk id")
    p_related.add_argument("--mode", choices=["cluster", "embed"], default="cluster",
                           help="Recommendation mode: cluster (fast, explainable) or embed (semantic neighbors)")
    p_related.add_argument("--limit", type=int, default=10, help="Max recommendations (default: 10)")
    p_related.set_defaults(func=cmd_related)

    p_scl = sub.add_parser("suggest-clusters", help="Suggest clusters based on FTS hits for a query")
    p_scl.add_argument("query", type=str, help="Query string")
    p_scl.add_argument("--limit", type=int, default=5, help="Max clusters (default: 5)")
    p_scl.add_argument("--fts-k", type=int, default=50, help="How many FTS hits to vote on (default: 50)")
    p_scl.set_defaults(func=cmd_suggest_clusters)

    p_cls = sub.add_parser("clusters", help="List top clusters by size")
    p_cls.add_argument("--limit", type=int, default=10, help="Max clusters (default: 10)")
    p_cls.set_defaults(func=cmd_clusters)

    p_cl = sub.add_parser("cluster", help="Show members of a cluster")
    p_cl.add_argument("cluster_id", type=int, help="Cluster id")
    p_cl.add_argument("--limit", type=int, default=10, help="Max members to show (default: 10)")
    p_cl.set_defaults(func=cmd_cluster)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
