# src/kb/api/schemas.py
from __future__ import annotations

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# -------------------------
# Basic chunk views
# -------------------------

class ChunkHitOut(BaseModel):
    """
    Lightweight chunk representation for lists / search results.
    """
    chunk_id: int
    file_path: str
    heading: str = ""
    preview: str = ""


class ChunkOut(BaseModel):
    """
    Full chunk content view.
    """
    id: int
    file_path: str
    heading: str = ""
    ordinal: int
    content: str


# -------------------------
# Context-aware recommendation (chunk-level)
# -------------------------

class RelatedItemOut(BaseModel):
    """
    Recommendation result for a given context chunk (chunk-level).
    """
    chunk_id: int
    file_path: str
    heading: str = ""
    preview: str = ""

    # Similarity score (only meaningful for semantic / embedding mode)
    score: Optional[float] = None

    # Explanation of why this item is recommended
    reason: Literal["same_topic", "semantic_similarity"]


# -------------------------
# Context-aware recommendation (note-level / full note)
# -------------------------

class RelatedNoteOut(BaseModel):
    """
    Recommendation result aggregated to a full note (file-level).

    We compute similarity at chunk-level for precision, then aggregate to file-level
    for better navigation.
    """
    file_path: str

    # Aggregated score for the whole note (e.g., max chunk score in that file)
    score: float

    # Why this note is recommended (based on the selected mode)
    reason: Literal["same_topic", "semantic_similarity"]

    # How many recommended chunks were found in this note
    matched_chunks: int = 0

    # Optional: show which chunks in that note contributed (for explainability / UI)
    top_chunk_ids: List[int] = Field(default_factory=list)


class RelatedNotesResponse(BaseModel):
    """
    Unified note-level recommendation response.
    """
    mode: Literal["cluster", "embed"]
    items: List[RelatedNoteOut]


# -------------------------
# Search responses
# -------------------------

class SearchResponse(BaseModel):
    """
    Unified search response.
    mode indicates whether the search is lexical (FTS) or semantic.
    """
    mode: Literal["lexical", "semantic"]
    total: Optional[int] = None
    items: List[ChunkHitOut]


# -------------------------
# Topic (Cluster) views
# -------------------------

class ClusterSuggestionOut(BaseModel):
    """
    Suggested topic (cluster) inferred from search hits.
    """
    cluster_id: int
    name: str = ""
    score: float   # normalized vote ratio


class ClusterMetaOut(BaseModel):
    """
    Metadata for a topic (cluster).
    """
    id: int
    name: str = ""
    summary: str = ""
    size: int = 0


class ClusterListItemOut(BaseModel):
    """
    Lightweight topic (cluster) list item.
    """
    id: int
    name: str = ""
    size: int = 0
    method: str = ""
    k: int = 0


class ClusterDetailOut(BaseModel):
    """
    Topic (cluster) detail view with member chunks.
    """
    meta: ClusterMetaOut
    members: List[ChunkHitOut] = Field(default_factory=list)


# -------------------------
# Topic aliases (semantic alignment with Track 3)
# -------------------------
# Internally we still use "cluster", but externally we speak in terms of "topic".

TopicSuggestionOut = ClusterSuggestionOut
TopicMetaOut = ClusterMetaOut
TopicListItemOut = ClusterListItemOut
TopicDetailOut = ClusterDetailOut
