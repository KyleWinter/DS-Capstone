from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


def ensure_db_dir(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)


def get_conn(db_path: Path) -> sqlite3.Connection:
    """
    Create a SQLite connection with sensible defaults.
    """
    ensure_db_dir(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    # Practical pragmas for local KB
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(
    conn: sqlite3.Connection,
    schema_path: Optional[Path] = None,
) -> None:
    """
    Initialize DB schema (idempotent).
    """
    if schema_path is None:
        # schema.sql is located next to this file: src/kb/store/schema.sql
        schema_path = Path(__file__).resolve().parent / "schema.sql"

    sql = schema_path.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()
