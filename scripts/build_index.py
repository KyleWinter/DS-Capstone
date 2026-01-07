#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List

# Make project root importable when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sqlite3

from src.kb.store.db import get_conn, init_db
from src.kb.store.repo import KBRepo, ChunkRow, sha256_text
from src.kb.ingest.loader import iter_markdown_files, load_markdown
from src.kb.ingest.chunker import chunk_text
from src.kb.config import DB_PATH, NOTES_DIR


# -------------------------
# Helpers
# -------------------------

def _to_rel_path(md_path: Path, notes_root: Path) -> str:
    """
    Convert absolute path to a portable relative path stored in DB.
    """
    rel = md_path.resolve().relative_to(notes_root.resolve())
    return rel.as_posix()


def _chunk_ids_by_file(conn: sqlite3.Connection, file_path: str) -> List[int]:
    rows = conn.execute(
        "SELECT id FROM chunks WHERE file_path=? ORDER BY id",
        (file_path,),
    ).fetchall()
    return [int(r["id"]) for r in rows]


def _delete_by_chunk_ids(conn: sqlite3.Connection, table: str, chunk_ids: List[int]) -> None:
    """
    Delete rows from `table` where chunk_id IN (...).
    Safe no-op for empty list.
    """
    if not chunk_ids:
        return
    qmarks = ",".join(["?"] * len(chunk_ids))
    conn.execute(
        f"DELETE FROM {table} WHERE chunk_id IN ({qmarks})",
        [int(x) for x in chunk_ids],
    )


def _rebuild_fts(conn: sqlite3.Connection) -> None:
    """
    Rebuild FTS index if chunks_fts exists.
    This is critical because your DB currently has no triggers.
    """
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='chunks_fts'"
    ).fetchone()
    if not row:
        return
    # FTS5 rebuild command
    conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")


def _set_sqlite_pragmas(conn: sqlite3.Connection) -> None:
    """
    Optional pragmas for faster bulk ingestion.
    Safe defaults for local KB.
    """
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")


def _get_file_meta(conn: sqlite3.Connection, file_path: str):
    """
    Return (mtime, sha256) if files table has entry; else None.
    """
    row = conn.execute(
        "SELECT mtime, sha256 FROM files WHERE path=?",
        (file_path,),
    ).fetchone()
    return row


# -------------------------
# Core indexing
# -------------------------

def index_one_file(
    conn: sqlite3.Connection,
    repo: KBRepo,
    md_path: Path,
    notes_root: Path,
    *,
    incremental: bool = True,
) -> int:
    """
    Rebuild chunks for a single markdown file.
    Returns number of inserted chunks.

    Guarantees consistency:
    - When rebuilding a file, remove downstream rows for old chunk_ids:
      embeddings, cluster_members (if those tables exist / are used).
    - Rebuild chunks (delete then insert).
    """
    stat = md_path.stat()
    text, _ = load_markdown(md_path)
    digest = sha256_text(text)

    rel_path = _to_rel_path(md_path, notes_root)

    # Incremental skip if unchanged
    if incremental:
        meta = _get_file_meta(conn, rel_path)
        if meta:
            old_mtime = float(meta["mtime"] or 0.0)
            old_sha = str(meta["sha256"] or "")
            # Either check sha only, or both sha+mtime. Here we check sha first.
            if old_sha == digest:
                # Still update mtime/size just in case (optional)
                repo.upsert_file(rel_path, mtime=stat.st_mtime, size_bytes=stat.st_size, sha256=digest)
                return 0

    # Upsert file metadata
    repo.upsert_file(rel_path, mtime=stat.st_mtime, size_bytes=stat.st_size, sha256=digest)

    # Collect old chunk ids for cleanup
    old_chunk_ids = _chunk_ids_by_file(conn, rel_path)

    # Clean downstream tables that reference chunk_id
    # (No harm if the table exists but has no rows.)
    # If some tables do not exist in your schema, wrap in try/except.
    if old_chunk_ids:
        for table in ("embeddings", "cluster_members"):
            try:
                _delete_by_chunk_ids(conn, table, old_chunk_ids)
            except sqlite3.OperationalError:
                # table doesn't exist in this schema -> ignore
                pass

    # Delete old chunks for this file
    repo.delete_chunks_by_file(rel_path)

    # Chunk markdown
    chunk_dicts = chunk_text(text, file_path=rel_path)
    chunk_rows = [
        ChunkRow(
            file_path=c["file_path"],
            content=c["content"],
            ordinal=int(c.get("ordinal", 0)),
            heading=c.get("heading"),
            start_line=c.get("start_line"),
            end_line=c.get("end_line"),
        )
        for c in chunk_dicts
        if (c.get("content") or "").strip()
    ]

    return repo.insert_chunks(chunk_rows)


# -------------------------
# Main
# -------------------------

def main() -> None:
    notes_root = NOTES_DIR
    if not notes_root.exists():
        raise FileNotFoundError(f"Notes directory not found: {notes_root.resolve()}")

    conn = get_conn(DB_PATH)
    init_db(conn)
    _set_sqlite_pragmas(conn)

    repo = KBRepo(conn)

    file_count = 0
    inserted_chunks = 0
    skipped_files = 0
    failed_files = 0

    # Process all markdown files
    for md_path in iter_markdown_files(notes_root):
        file_count += 1
        try:
            n = index_one_file(conn, repo, md_path, notes_root, incremental=True)
            if n == 0:
                skipped_files += 1
            else:
                inserted_chunks += n
        except Exception as e:
            failed_files += 1
            print(f"[WARN] Failed indexing {md_path}: {e}")

        # Moderate commit cadence
        if file_count % 50 == 0:
            repo.commit()
            print(f"Indexed {file_count} files... (skipped={skipped_files}, failed={failed_files})")

    repo.commit()

    # Rebuild FTS to keep chunks_fts consistent with chunks (no triggers)
    try:
        with conn:
            _rebuild_fts(conn)
    except sqlite3.OperationalError as e:
        # If FTS table doesn't exist or rebuild not supported in current config
        print(f"[WARN] FTS rebuild skipped: {e}")

    repo.commit()
    conn.close()

    print("\n✅ Build index finished.")
    print(f"📄 Files scanned: {file_count}")
    print(f"⏭️ Files skipped (unchanged): {skipped_files}")
    print(f"⚠️ Files failed: {failed_files}")
    print(f"🧩 Chunks inserted: {inserted_chunks}")
    print(f"📦 Database: {DB_PATH.resolve()}")
    print(f"🗂️ Notes root: {notes_root.resolve()}")


if __name__ == "__main__":
    main()
