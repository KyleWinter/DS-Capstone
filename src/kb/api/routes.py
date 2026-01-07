# src/kb/api/routes.py
from __future__ import annotations

from typing import Literal, List

from fastapi import APIRouter, Depends, HTTPException, Query
import sqlite3

from src.kb.config import DB_PATH
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
    SearchResponse,
    ClusterSuggestionOut,
    ClusterListItemOut,
    ClusterMetaOut,
    ClusterDetailOut,
    TopicSuggestionOut,
    TopicListItemOut,
    TopicMetaOut,
    TopicDetailOut,
    RelatedNoteOut,
    RelatedNotesResponse,
)

router = APIRouter()


# -------------------------
# DB dependency
# -------------------------

def get_db():
    conn = get_conn(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


# -------------------------
# Health
# -------------------------

@router.get("/health")
def health() -> dict:
    return {"ok": True}


# -------------------------
# Search (Lexical / FTS)
# -------------------------

@router.get("/search", response_model=SearchResponse)
def api_search(
    q: str = Query(..., min_length=1, description="FTS query string"),
    limit: int = Query(10, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
) -> SearchResponse:
    """
    Scalable lexical search using FTS (grep-style).
    Semantic search is intentionally NOT used here.
    """
    hits = fts_search(conn, q, limit=limit)
    items = [
        ChunkHitOut(
            chunk_id=h.chunk_id,
            file_path=h.file_path,
            heading=getattr(h, "heading", "") or "",
            preview=(h.preview or "").replace("\n", " "),
        )
        for h in hits
    ]
    return SearchResponse(
        mode="lexical",
        total=None,
        items=items,
    )


# -------------------------
# Chunk detail
# -------------------------

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


# -------------------------
# Context-aware recommendations
# -------------------------

@router.get("/chunks/{chunk_id}/related", response_model=list[RelatedItemOut])
def api_related(
    chunk_id: int,
    mode: Literal["cluster", "embed"] = Query("cluster"),
    k: int = Query(10, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[RelatedItemOut]:
    """
    Context-aware recommendations for a given chunk.
    - cluster: structural / topic-based (explainable)
    - embed: semantic similarity (embedding-based)
    """
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
                reason="same_topic",
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
            reason="semantic_similarity",
        )
        for it in items
    ]


# -------------------------
# Topic / Cluster suggestion
# -------------------------

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


# Topic alias (Track 3 friendly)
@router.get("/topics/suggest", response_model=list[TopicSuggestionOut])
def api_suggest_topics(
    q: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=50),
    fts_k: int = Query(50, ge=1, le=500),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[TopicSuggestionOut]:
    return api_suggest_clusters(q=q, limit=limit, fts_k=fts_k, conn=conn)


# -------------------------
# Topic / Cluster listing
# -------------------------

@router.get("/clusters", response_model=list[ClusterListItemOut])
def api_list_clusters(
    limit: int = Query(10, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[ClusterListItemOut]:
    ok = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='clusters'"
    ).fetchone()
    if not ok:
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


@router.get("/topics", response_model=list[TopicListItemOut])
def api_list_topics(
    limit: int = Query(10, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[TopicListItemOut]:
    return api_list_clusters(limit=limit, conn=conn)


# -------------------------
# Topic / Cluster detail
# -------------------------

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


@router.get("/topics/{topic_id}", response_model=TopicDetailOut)
def api_topic_detail(
    topic_id: int,
    limit: int = Query(50, ge=1, le=500),
    conn: sqlite3.Connection = Depends(get_db),
) -> TopicDetailOut:
    return api_cluster_detail(cluster_id=topic_id, limit=limit, conn=conn)


# -------------------------
# Context-aware note-level recommendations
# -------------------------

@router.get(
    "/chunks/{chunk_id}/related-notes",
    response_model=RelatedNotesResponse,
)
def api_related_notes(
    chunk_id: int,
    mode: Literal["cluster", "embed"] = Query("embed"),
    k: int = Query(5, ge=1, le=50),
    conn: sqlite3.Connection = Depends(get_db),
) -> RelatedNotesResponse:
    """
    Context-aware recommendations aggregated to full notes (file-level).

    We compute similarity at chunk-level for precision, then aggregate results
    by file_path for better human navigation.
    """
    # validate chunk exists
    row = get_chunk_by_id(conn, chunk_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Chunk not found: {chunk_id}")

    # 1) get chunk-level recommendations
    if mode == "cluster":
        chunk_items = related_by_cluster(conn, chunk_id, k=50)
        reason = "same_topic"
    else:
        chunk_items = related_by_embedding(conn, chunk_id, k=50)
        reason = "semantic_similarity"

    if not chunk_items:
        return RelatedNotesResponse(mode=mode, items=[])

    # 2) aggregate by file_path
    by_file: dict[str, list] = {}
    for it in chunk_items:
        by_file.setdefault(it.file_path, []).append(it)

    # 3) compute note-level score (max chunk score is the safest default)
    notes: list[RelatedNoteOut] = []
    for file_path, items in by_file.items():
        # score aggregation
        if mode == "embed":
            score = max(float(it.score) for it in items if it.score is not None)
        else:
            score = 1.0  # structural recommendation, score not meaningful

        notes.append(
            RelatedNoteOut(
                file_path=file_path,
                score=score,
                reason=reason,
                matched_chunks=len(items),
                top_chunk_ids=[it.chunk_id for it in items[:5]],
            )
        )

    # 4) sort and truncate
    notes.sort(key=lambda n: n.score, reverse=True)
    notes = notes[:k]

    return RelatedNotesResponse(
        mode=mode,
        items=notes,
    )
