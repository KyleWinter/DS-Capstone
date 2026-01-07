#!/usr/bin/env python3
import sys
from pathlib import Path

# Make project root importable when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.kb.store.db import get_conn, init_db
from src.kb.store.repo import KBRepo, ChunkRow, sha256_text
from src.kb.ingest.loader import iter_markdown_files, load_markdown
from src.kb.ingest.chunker import chunk_text
from src.kb.config import DB_PATH, NOTES_DIR


def _to_rel_path(md_path: Path, notes_root: Path) -> str:
    """
    Convert absolute path to a portable relative path stored in DB.
    """
    # Use resolve() for stability, then store POSIX style for cross-platform consistency
    rel = md_path.resolve().relative_to(notes_root.resolve())
    return rel.as_posix()


def index_one_file(repo: KBRepo, md_path: Path, notes_root: Path) -> int:
    """
    Rebuild chunks for a single markdown file.
    Returns number of inserted chunks.
    """
    stat = md_path.stat()
    text, _ = load_markdown(md_path)
    digest = sha256_text(text)

    # ✅ store relative path in DB
    rel_path = _to_rel_path(md_path, notes_root)

    # 记录文件元数据（可用于后续增量）
    repo.upsert_file(rel_path, mtime=stat.st_mtime, size_bytes=stat.st_size, sha256=digest)

    # 重建该文件 chunks（先删再插）
    repo.delete_chunks_by_file(rel_path)

    # chunk -> ChunkRow
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
    ]

    return repo.insert_chunks(chunk_rows)


def main() -> None:
    notes_root = NOTES_DIR
    if not notes_root.exists():
        raise FileNotFoundError(f"Notes directory not found: {notes_root.resolve()}")

    conn = get_conn(DB_PATH)
    init_db(conn)
    repo = KBRepo(conn)

    file_count = 0
    inserted_chunks = 0

    for md_path in iter_markdown_files(notes_root):
        file_count += 1
        inserted_chunks += index_one_file(repo, md_path, notes_root)

        # 适度 commit，避免一次性内存/事务过大
        if file_count % 50 == 0:
            repo.commit()
            print(f"Indexed {file_count} files...")

    repo.commit()
    conn.close()

    print("\n✅ Build index finished.")
    print(f"📄 Files scanned: {file_count}")
    print(f"🧩 Chunks inserted: {inserted_chunks}")
    print(f"📦 Database: {DB_PATH.resolve()}")
    print(f"🗂️ Notes root: {notes_root.resolve()}")


if __name__ == "__main__":
    main()
