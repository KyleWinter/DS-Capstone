#!/usr/bin/env python3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import argparse

from src.kb.store.db import get_conn, init_db



def list_objects(conn) -> list[tuple[str, str]]:
    rows = conn.execute(
        """
        SELECT name, type FROM sqlite_master
        WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%'
        ORDER BY type, name
        """
    ).fetchall()
    return [(r["type"], r["name"]) for r in rows]


def fts_sanity_check(conn) -> int:
    """
    Verify that FTS table exists and can execute a MATCH query.
    Returns number of rows matched by a trivial query.
    """
    # Ensure chunks_fts exists
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE name='chunks_fts' AND type='table' LIMIT 1"
    ).fetchone()
    if not exists:
        raise RuntimeError("FTS table 'chunks_fts' not found in sqlite_master.")

    # MATCH query sanity check:
    # If DB is empty, this returns 0 and that's fine.
    # Use a token that's likely to exist, but we don't require it.
    rows = conn.execute(
        """
        SELECT count(*) AS c
        FROM chunks_fts
        WHERE chunks_fts MATCH ?
        """,
        ("test",),
    ).fetchone()
    return int(rows["c"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify KB SQLite schema + FTS.")
    parser.add_argument(
        "--db",
        type=str,
        default="data/kb.sqlite",
        help="Path to SQLite DB (default: data/kb.sqlite)",
    )
    args = parser.parse_args()

    db_path = Path(args.db)

    try:
        conn = get_conn(db_path)
        init_db(conn)

        objs = list_objects(conn)

        required = {"chunks", "files", "chunks_fts"}
        present = {name for _, name in objs}
        missing = sorted(list(required - present))

        print("✅ DB initialized (schema applied).")
        print(f"📦 Database: {db_path.resolve()}")
        print("\nObjects:")
        for t, name in objs:
            print(f" - {t:5s} {name}")

        if missing:
            print("\n❌ Missing required objects:", ", ".join(missing))
            return 2

        # FTS sanity
        count = fts_sanity_check(conn)
        print("\n✅ FTS sanity check: MATCH query executed successfully.")
        print(f"ℹ️  Sample MATCH('test') count: {count} (0 is OK if DB is empty)")

        return 0

    except Exception as e:
        print("\n❌ Verification failed:", str(e))
        return 1

    finally:
        try:
            conn.close()  # type: ignore[name-defined]
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
