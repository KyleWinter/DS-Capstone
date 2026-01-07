#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import sqlite3
from typing import List, Tuple, Optional

from src.kb.config import DB_PATH
from src.kb.store.db import get_conn, init_db


def _fetch_modules(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    return conn.execute(
        """
        SELECT m.id, m.name, COALESCE(m.description,'') AS description,
               COUNT(fm.file_path) AS file_count
        FROM modules m
        LEFT JOIN file_modules fm ON fm.module_id = m.id
        GROUP BY m.id
        ORDER BY file_count DESC, m.name ASC
        """
    ).fetchall()


def _fetch_files_in_module(conn: sqlite3.Connection, module_id: int) -> List[sqlite3.Row]:
    return conn.execute(
        """
        SELECT fm.file_path, COALESCE(fm.score, 1.0) AS score
        FROM file_modules fm
        WHERE fm.module_id = ?
        ORDER BY score DESC, fm.file_path ASC
        """,
        (module_id,),
    ).fetchall()


def _fetch_module_id_by_name(conn: sqlite3.Connection, name: str) -> Optional[int]:
    row = conn.execute("SELECT id FROM modules WHERE name=?", (name,)).fetchone()
    return int(row["id"]) if row else None


def _print_module_header(mid: int, name: str, desc: str, count: int) -> None:
    print(f"\n=== Module #{mid}: {name}  ({count} files) ===")
    if desc.strip():
        print(f"  {desc.strip()}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Inspect module classification results in kb.sqlite")
    ap.add_argument("--top", type=int, default=30, help="show top N modules by file count")
    ap.add_argument("--module", type=str, default="", help="show files for a specific module name")
    ap.add_argument("--id", type=int, default=0, help="show files for a specific module id")
    ap.add_argument("--limit-files", type=int, default=50, help="max files to show per module")
    ap.add_argument("--show-all", action="store_true", help="show all modules (ignores --top)")
    args = ap.parse_args()

    conn = get_conn(DB_PATH)
    init_db(conn)

    # Check tables exist
    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "modules" not in tables or "file_modules" not in tables:
        conn.close()
        raise SystemExit("modules/file_modules tables not found. Run scripts/build_modules.py first.")

    # If user asks for a specific module
    module_id = 0
    if args.id and args.id > 0:
        module_id = int(args.id)
    elif args.module.strip():
        mid = _fetch_module_id_by_name(conn, args.module.strip())
        if mid is None:
            conn.close()
            raise SystemExit(f"Module not found by name: {args.module.strip()}")
        module_id = mid

    if module_id > 0:
        row = conn.execute(
            """
            SELECT m.id, m.name, COALESCE(m.description,'') AS description,
                   COUNT(fm.file_path) AS file_count
            FROM modules m
            LEFT JOIN file_modules fm ON fm.module_id = m.id
            WHERE m.id=?
            GROUP BY m.id
            """,
            (module_id,),
        ).fetchone()

        if not row:
            conn.close()
            raise SystemExit(f"Module id not found: {module_id}")

        files = _fetch_files_in_module(conn, module_id)
        _print_module_header(int(row["id"]), str(row["name"]), str(row["description"]), int(row["file_count"]))

        shown = 0
        for r in files:
            if shown >= args.limit_files:
                break
            print(f" - {r['file_path']}  (score={float(r['score']):.3f})")
            shown += 1

        if len(files) > shown:
            print(f" ... ({len(files) - shown} more)")
        conn.close()
        return

    # Otherwise list modules
    mods = _fetch_modules(conn)
    if not mods:
        conn.close()
        print("No modules found. Run scripts/build_modules.py first.")
        return

    to_show = mods if args.show_all else mods[: max(1, int(args.top))]

    print(f"Found {len(mods)} modules.")
    print("Top modules by file count:\n")
    for r in to_show:
        mid = int(r["id"])
        name = str(r["name"])
        desc = str(r["description"])
        count = int(r["file_count"])
        print(f"- #{mid:03d}  {name:<24}  files={count}")

    print("\nTips:")
    print("  - Show a module by id:      python scripts/inspect_modules.py --id 3")
    print("  - Show a module by name:    python scripts/inspect_modules.py --module \"二叉树专题\"")
    print("  - Show all modules:         python scripts/inspect_modules.py --show-all")
    conn.close()


if __name__ == "__main__":
    main()
