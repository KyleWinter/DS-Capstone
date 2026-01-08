from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.kb.search.lexical import LexicalHit, fts_search
from src.kb.search.semantic import semantic_rerank


@dataclass(frozen=True)
class HybridHit:
    chunk_id: int
    file_path: str
    heading: str
    preview: str
    score: float          # final score (higher is better)
    semantic_score: float # cosine similarity (higher is better)
    lexical_score: float  # bm25 (lower is better)


def _minmax_norm_invert(values: List[float]) -> List[float]:
    """
    Convert 'lower is better' scores into [0,1] where higher is better.
    """
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi - lo < 1e-12:
        return [1.0 for _ in values]
    # invert: lo -> 1.0, hi -> 0.0
    return [(hi - v) / (hi - lo) for v in values]


def hybrid_search(
    conn: sqlite3.Connection,
    query: str,
    *,
    module_id: Optional[int] = None,
    fts_k: int = 200,
    top_k: int = 20,
    model: str = "text-embedding-3-small",
    alpha: float = 0.8,            # weight for semantic score
    dedup_by_file: bool = True,    # avoid many chunks from same file
    per_file_limit: int = 2,       # if not dedup, cap chunks per file
) -> List[HybridHit]:
    """
    Two-stage retrieval:
      1) FTS5 (lexical) recall K candidates
      2) semantic rerank on those candidates
      3) optional fusion score & file-level dedup
    """
    q = (query or "").strip()
    if not q:
        return []

    # 1) Lexical recall (fast)
    #    Use module_id filter so "click module -> search within module" is easy
    lexical_hits: List[LexicalHit] = fts_search(conn, q, limit=fts_k, module_id=module_id)
    if not lexical_hits:
        return []

    # Map chunk_id -> lexical hit
    by_id: Dict[int, LexicalHit] = {h.chunk_id: h for h in lexical_hits}
    candidate_ids = list(by_id.keys())

    # Prepare lexical normalization for fusion
    # If LexicalHit doesn't have score yet, we fallback to 1.0
    lex_scores_raw: List[float] = []
    for h in lexical_hits:
        lex_scores_raw.append(float(getattr(h, "score", 0.0)))

    # bm25: lower is better -> normalize to [0,1] where higher is better
    lex_norm = _minmax_norm_invert(lex_scores_raw)
    lex_norm_by_id: Dict[int, float] = {h.chunk_id: lex_norm[i] for i, h in enumerate(lexical_hits)}

    # 2) Semantic rerank (may fail if embeddings missing)
    try:
        sem_hits = semantic_rerank(conn, q, candidate_ids, model=model, top_k=None)
    except Exception:
        sem_hits = []

    # If semantic failed or no embeddings, fallback to lexical order
    if not sem_hits:
        # Best-effort: return lexical top_k directly
        out: List[HybridHit] = []
        file_used: Dict[str, int] = {}
        for h in lexical_hits:
            if len(out) >= top_k:
                break
            if dedup_by_file and h.file_path in file_used:
                continue
            if not dedup_by_file and file_used.get(h.file_path, 0) >= per_file_limit:
                continue

            file_used[h.file_path] = file_used.get(h.file_path, 0) + 1

            out.append(
                HybridHit(
                    chunk_id=h.chunk_id,
                    file_path=h.file_path,
                    heading=h.heading,
                    preview=h.preview,
                    score=float(lex_norm_by_id.get(h.chunk_id, 0.0)),
                    semantic_score=0.0,
                    lexical_score=float(getattr(h, "score", 0.0)),
                )
            )
        return out

    # 3) Fusion score + assemble results
    # semantic cosine is already higher is better.
    # We combine with normalized lexical score.
    alpha = max(0.0, min(1.0, float(alpha)))

    scored_rows: List[Tuple[int, float, float, float]] = []
    for s in sem_hits:
        cid = int(s.chunk_id)
        sem = float(s.score)
        lex = float(lex_norm_by_id.get(cid, 0.0))
        final = alpha * sem + (1.0 - alpha) * lex
        scored_rows.append((cid, final, sem, float(getattr(by_id[cid], "score", 0.0)) if cid in by_id else 0.0))

    # sort by final score desc
    scored_rows.sort(key=lambda x: x[1], reverse=True)

    # 4) file-level dedup / cap per file
    out: List[HybridHit] = []
    file_used: Dict[str, int] = {}

    for cid, final, sem, lex_raw in scored_rows:
        if len(out) >= top_k:
            break
        l = by_id.get(cid)
        if not l:
            continue

        if dedup_by_file and l.file_path in file_used:
            continue
        if not dedup_by_file and file_used.get(l.file_path, 0) >= per_file_limit:
            continue

        file_used[l.file_path] = file_used.get(l.file_path, 0) + 1

        out.append(
            HybridHit(
                chunk_id=cid,
                file_path=l.file_path,
                heading=l.heading,
                preview=l.preview,
                score=float(final),
                semantic_score=float(sem),
                lexical_score=float(lex_raw),
            )
        )

    return out
