#!/usr/bin/env python3
import sys
from pathlib import Path

# Make project root importable when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse

from src.kb.config import DB_PATH
from src.kb.store.db import get_conn, init_db
from src.kb.search.lexical import fts_search, get_chunk_by_id


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

    p_show = sub.add_parser("show", help="Show full content of a chunk by id")
    p_show.add_argument("chunk_id", type=int, help="Chunk id")
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
