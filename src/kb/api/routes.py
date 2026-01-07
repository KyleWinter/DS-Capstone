# src/kb/api/routes.py
from __future__ import annotations

from typing import Literal, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
import sqlite3
from pathlib import Path

from src.kb.config import DB_PATH, NOTES_DIR
from src.kb.store.db import get_conn

from src.kb.search.lexical import fts_search, get_chunk_by_id
from src.kb.suggest.recommender import (
    related_by_cluster,
    related_by_embedding,
    suggest_clusters_from_chunk_hits,
)

from .schemas import (
    ChunkHitOut,
    ChunkOut,
    RelatedItemOut,
    ClusterSuggestionOut,
    ClusterListItemOut,
    ClusterMetaOut,
    ClusterDetailOut,
    FileTreeNode,
)

router = APIRouter()


def get_db() -> sqlite3.Connection:
    # 每次请求拿一个连接（SQLite 够用，且简单）
    conn = get_conn(DB_PATH)
    return conn


@router.get("/health")
def health() -> dict:
    return {"ok": True}


@router.get("/search", response_model=list[ChunkHitOut])
def api_search(
    q: str = Query(..., min_length=1, description="FTS query string"),
    limit: int = Query(10, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[ChunkHitOut]:
    hits = fts_search(conn, q, limit=limit)
    return [
        ChunkHitOut(
            chunk_id=h.chunk_id,
            file_path=h.file_path,
            heading=getattr(h, "heading", "") or "",
            preview=(h.preview or "").replace("\n", " "),
        )
        for h in hits
    ]


@router.get("/chunks/{chunk_id}", response_model=ChunkOut)
def api_chunk(
    chunk_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> ChunkOut:
    row = get_chunk_by_id(conn, chunk_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Chunk not found: {chunk_id}")
    return ChunkOut(
        id=int(row["id"]),
        file_path=str(row["file_path"]),
        heading=str(row["heading"] or ""),
        ordinal=int(row["ordinal"]),
        content=str(row["content"] or ""),
    )


@router.get("/files/chunks", response_model=list[ChunkOut])
def api_file_chunks(
    file_path: str = Query(..., description="File path to get chunks for"),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[ChunkOut]:
    """Get all chunks for a specific file, ordered by ordinal."""
    rows = conn.execute(
        """
        SELECT id, file_path, heading, ordinal, content
        FROM chunks
        WHERE file_path = ?
        ORDER BY ordinal ASC
        """,
        (file_path,),
    ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No chunks found for file: {file_path}")

    return [
        ChunkOut(
            id=int(row["id"]),
            file_path=str(row["file_path"]),
            heading=str(row["heading"] or ""),
            ordinal=int(row["ordinal"]),
            content=str(row["content"] or ""),
        )
        for row in rows
    ]


@router.get("/chunks/{chunk_id}/related", response_model=list[RelatedItemOut])
def api_related(
    chunk_id: int,
    mode: Literal["cluster", "embed"] = Query("cluster"),
    k: int = Query(10, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[RelatedItemOut]:
    # validate chunk exists
    row = get_chunk_by_id(conn, chunk_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Chunk not found: {chunk_id}")

    if mode == "cluster":
        items = related_by_cluster(conn, chunk_id, k=k)
        return [
            RelatedItemOut(
                chunk_id=it.chunk_id,
                file_path=it.file_path,
                heading=it.heading or "",
                preview=(it.preview or "").replace("\n", " "),
                score=None,
            )
            for it in items
        ]

    items = related_by_embedding(conn, chunk_id, k=k)
    return [
        RelatedItemOut(
            chunk_id=it.chunk_id,
            file_path=it.file_path,
            heading=it.heading or "",
            preview=(it.preview or "").replace("\n", " "),
            score=float(it.score),
        )
        for it in items
    ]


@router.get("/clusters/suggest", response_model=list[ClusterSuggestionOut])
def api_suggest_clusters(
    q: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=50),
    fts_k: int = Query(50, ge=1, le=500),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[ClusterSuggestionOut]:
    hits = fts_search(conn, q, limit=fts_k)
    if not hits:
        return []

    chunk_ids = [h.chunk_id for h in hits]
    clusters = suggest_clusters_from_chunk_hits(conn, chunk_ids, k=limit)
    return [
        ClusterSuggestionOut(
            cluster_id=c.cluster_id,
            name=c.name or "",
            score=float(c.score),
        )
        for c in clusters
    ]


@router.get("/clusters", response_model=list[ClusterListItemOut])
def api_list_clusters(
    limit: int = Query(10, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[ClusterListItemOut]:
    ok = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='clusters'"
    ).fetchone()
    if not ok:
        # 用 200 + 提示信息更友好，但这里保持纯 JSON
        return []

    rows = conn.execute(
        """
        SELECT id, COALESCE(name,'') AS name, COALESCE(size,0) AS size, method, k
        FROM clusters
        ORDER BY size DESC, id ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    return [
        ClusterListItemOut(
            id=int(r["id"]),
            name=str(r["name"] or ""),
            size=int(r["size"] or 0),
            method=str(r["method"] or ""),
            k=int(r["k"] or 0),
        )
        for r in rows
    ]


@router.get("/clusters/{cluster_id}", response_model=ClusterDetailOut)
def api_cluster_detail(
    cluster_id: int,
    limit: int = Query(50, ge=1, le=500),
    conn: sqlite3.Connection = Depends(get_db),
) -> ClusterDetailOut:
    meta = conn.execute(
        """
        SELECT id,
               COALESCE(name,'') AS name,
               COALESCE(summary,'') AS summary,
               COALESCE(size,0) AS size
        FROM clusters WHERE id=?
        """,
        (cluster_id,),
    ).fetchone()
    if not meta:
        raise HTTPException(status_code=404, detail=f"Cluster not found: {cluster_id}")

    rows = conn.execute(
        """
        SELECT c.id AS chunk_id, c.file_path, COALESCE(c.heading,'') AS heading, c.content
        FROM cluster_members m
        JOIN chunks c ON c.id = m.chunk_id
        WHERE m.cluster_id=?
        ORDER BY c.id
        LIMIT ?
        """,
        (cluster_id, limit),
    ).fetchall()

    members: List[ChunkHitOut] = []
    for r in rows:
        content = str(r["content"] or "").replace("\n", " ").strip()
        preview = content[:240] + ("…" if len(content) > 240 else "")
        members.append(
            ChunkHitOut(
                chunk_id=int(r["chunk_id"]),
                file_path=str(r["file_path"]),
                heading=str(r["heading"] or ""),
                preview=preview,
            )
        )

    return ClusterDetailOut(
        meta=ClusterMetaOut(
            id=int(meta["id"]),
            name=str(meta["name"] or ""),
            summary=str(meta["summary"] or ""),
            size=int(meta["size"] or 0),
        ),
        members=members,
    )


@router.get("/files/tree", response_model=FileTreeNode)
def api_file_tree(
    conn: sqlite3.Connection = Depends(get_db),
) -> FileTreeNode:
    """Build a hierarchical file tree from all markdown files in the database."""

    # Get all unique file paths and their chunks
    rows = conn.execute(
        """
        SELECT DISTINCT file_path,
               GROUP_CONCAT(id) as chunk_ids
        FROM chunks
        GROUP BY file_path
        ORDER BY file_path
        """
    ).fetchall()

    if not rows:
        # Return empty root if no files
        return FileTreeNode(
            name="root",
            path="",
            type="directory",
            children=[]
        )

    # Build tree structure
    root: dict = {"name": "root", "path": "", "type": "directory", "children": {}}

    for row in rows:
        file_path = str(row["file_path"])
        chunk_ids_str = str(row["chunk_ids"] or "")
        chunk_ids = [int(cid) for cid in chunk_ids_str.split(",") if cid]

        # Split path into parts
        parts = file_path.split("/")
        current = root

        # Navigate/create directory structure
        for i, part in enumerate(parts):
            is_last = i == len(parts) - 1

            if is_last:
                # It's a file
                if "children" not in current:
                    current["children"] = {}
                current["children"][part] = {
                    "name": part,
                    "path": file_path,
                    "type": "file",
                    "chunk_ids": chunk_ids
                }
            else:
                # It's a directory
                if "children" not in current:
                    current["children"] = {}
                if part not in current["children"]:
                    current["children"][part] = {
                        "name": part,
                        "path": "/".join(parts[:i+1]),
                        "type": "directory",
                        "children": {}
                    }
                current = current["children"][part]

    # Convert dict structure to FileTreeNode
    def dict_to_node(d: dict) -> FileTreeNode:
        children_dict = d.get("children", {})
        children_list = None

        if children_dict:
            # Sort: directories first, then files, alphabetically within each group
            sorted_items = sorted(
                children_dict.items(),
                key=lambda x: (x[1]["type"] == "file", x[0].lower())
            )
            children_list = [dict_to_node(child) for _, child in sorted_items]

        return FileTreeNode(
            name=d["name"],
            path=d["path"],
            type=d["type"],
            children=children_list,
            chunk_ids=d.get("chunk_ids")
        )

    return dict_to_node(root)


@router.get("/files/content", response_class=PlainTextResponse)
def api_file_content(
    file_path: str = Query(..., description="File path to read"),
) -> str:
    """Read the raw markdown file content from disk.

    Accepts either:
    - Just the filename (e.g., "14. 剪绳子.md")
    - A relative path (e.g., "notes/14. 剪绳子.md")
    - An absolute path (extracts the filename)
    """

    # Security: prevent path traversal attacks
    try:
        requested_path = Path(file_path)

        # Extract just the filename (basename)
        # This handles both absolute paths and relative paths
        filename = requested_path.name

        # Security: prevent directory traversal in filename
        if '/' in filename or '\\' in filename or filename in ['.', '..']:
            raise HTTPException(status_code=400, detail="Invalid filename")

        # Build the full path in NOTES_DIR
        full_path = NOTES_DIR / filename

        # Resolve to get absolute path
        resolved_path = full_path.resolve()
        resolved_notes_dir = NOTES_DIR.resolve()

        # Verify the resolved path is within NOTES_DIR
        if not str(resolved_path).startswith(str(resolved_notes_dir)):
            raise HTTPException(status_code=403, detail="Access denied: path outside notes directory")

        # Check if file exists
        if not resolved_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")

        # Check if it's a file (not a directory)
        if not resolved_path.is_file():
            raise HTTPException(status_code=400, detail=f"Path is not a file: {filename}")

        # Read and return file content
        return resolved_path.read_text(encoding='utf-8')

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")
