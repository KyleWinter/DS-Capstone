# src/kb/api/schemas.py
from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field


class ChunkHitOut(BaseModel):
    chunk_id: int
    file_path: str
    heading: str = ""
    preview: str = ""


class ChunkOut(BaseModel):
    id: int
    file_path: str
    heading: str = ""
    ordinal: int
    content: str


class RelatedItemOut(BaseModel):
    chunk_id: int
    file_path: str
    heading: str = ""
    preview: str = ""
    score: Optional[float] = None  # embed 模式有分数，cluster 模式为 null


class ClusterSuggestionOut(BaseModel):
    cluster_id: int
    name: str = ""
    score: float


class ClusterMetaOut(BaseModel):
    id: int
    name: str = ""
    summary: str = ""
    size: int = 0


class ClusterListItemOut(BaseModel):
    id: int
    name: str = ""
    size: int = 0
    method: str = ""
    k: int = 0


class ClusterDetailOut(BaseModel):
    meta: ClusterMetaOut
    members: List[ChunkHitOut] = Field(default_factory=list)
