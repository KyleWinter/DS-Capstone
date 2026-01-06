from __future__ import annotations

import sqlite3
from typing import Dict, List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer


def _fetch_texts_for_cluster(
    conn: sqlite3.Connection,
    chunk_ids: List[int],
    max_docs: int = 30,
) -> List[str]:
    if not chunk_ids:
        return []
    ids = chunk_ids[:max_docs]
    qmarks = ",".join(["?"] * len(ids))
    rows = conn.execute(
        f"""
        SELECT content
        FROM chunks
        WHERE id IN ({qmarks})
        """,
        ids,
    ).fetchall()
    return [str(r["content"]) for r in rows]


def label_clusters_tfidf(
    conn: sqlite3.Connection,
    members: Dict[int, List[int]],   # cluster_idx -> [chunk_id...]
    top_terms: int = 6,
) -> Dict[int, Tuple[str, str]]:
    """
    Returns mapping:
      cluster_idx -> (name, summary)

    name: "term1 / term2 / term3"
    summary: "Top keywords: ..."
    """
    labels: Dict[int, Tuple[str, str]] = {}

    for cidx, chunk_ids in members.items():
        texts = _fetch_texts_for_cluster(conn, chunk_ids, max_docs=40)
        if not texts:
            labels[cidx] = (f"Cluster {cidx}", "No texts available")
            continue

        # TF-IDF within this cluster only: extract the most salient terms
        vec = TfidfVectorizer(
            max_features=2000,
            stop_words=None,  # 中英混合笔记时，不强行英文停用词
            ngram_range=(1, 2),
        )
        X = vec.fit_transform(texts)
        terms = vec.get_feature_names_out()

        scores = X.sum(axis=0).A1  # (features,)
        top_idx = scores.argsort()[::-1][:top_terms]
        top = [terms[i] for i in top_idx if scores[i] > 0]

        if not top:
            name = f"Cluster {cidx}"
            summary = "Top keywords: (none)"
        else:
            name = " / ".join(top[:3])
            summary = "Top keywords: " + ", ".join(top)

        labels[cidx] = (name, summary)

    return labels
