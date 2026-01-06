from __future__ import annotations

from pathlib import Path
from collections import Counter
import re
import sqlite3
from typing import Dict, List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer


# A small, practical stopword list for mixed CS notes (EN + common code/markdown noise)
STOPWORDS = {
    # very common English
    "the", "a", "an", "and", "or", "to", "of", "in", "for", "on", "with", "as", "is", "are", "be",
    "this", "that", "it", "we", "you", "i", "they", "at", "by", "from", "not", "can", "will",

    # markdown / docs noise
    "md", "markdown", "gfm", "toc", "readme", "https", "http", "www", "url",

    # code / leetcode noise
    "int", "long", "float", "double", "string", "char", "bool", "boolean", "void",
    "return", "new", "null", "true", "false", "public", "private", "protected", "static",
    "class", "interface", "import", "package", "def", "var", "let", "const",
    "if", "else", "for", "while", "break", "continue", "try", "catch", "throw",
    "system", "out", "println", "main",
    "node", "listnode", "treenode", "dp", "nums", "grid", "matrix",

    # shell / tar / etc
    "tar", "zip", "gz", "install", "download",

    # extra common noise we observed
    "head", "next", "l1", "l2", "l3", "id",
}

STOPWORDS.add("目录")

CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]+`")
URL_RE = re.compile(r"https?://\S+")
NONWORD_RE = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff]+")


def _clean_text(s: str) -> str:
    """Remove code blocks/urls and normalize."""
    s = CODE_FENCE_RE.sub(" ", s)
    s = INLINE_CODE_RE.sub(" ", s)
    s = URL_RE.sub(" ", s)
    s = s.lower()
    s = NONWORD_RE.sub(" ", s)
    return s


def _normalize_topic(t: str) -> str:
    """
    Make labels shorter and more product-like by collapsing repeated prefixes.
    """
    t = t.strip()
    t = re.sub(r"^leetcode\s*题解\s*", "LeetCode·", t, flags=re.IGNORECASE)
    t = re.sub(r"^剑指\s*offer\s*题解\s*", "剑指Offer·", t, flags=re.IGNORECASE)
    t = re.sub(r"^计算机网络\s*", "计算机网络·", t)
    t = re.sub(r"^java\s*", "Java·", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^\d+\.\s*", "", t)
    return t


def _is_noise_topic(t: str) -> bool:
    if not t:
        return True
    t = t.strip().lower()
    if len(t) < 2:
        return True
    if t.isdigit():
        return True
    # pure number-ish like "123" or "10"
    if re.fullmatch(r"\d+", t):
        return True
    if t in STOPWORDS:
        return True
    # file names like "题解 10" might become tokens - allow Chinese, but avoid mostly digits
    if re.fullmatch(r"[\d\s]+", t):
        return True
    return False


def _fetch_texts_for_cluster(conn: sqlite3.Connection, chunk_ids: List[int], max_docs: int = 30) -> List[str]:
    if not chunk_ids:
        return []
    ids = chunk_ids[:max_docs]
    qmarks = ",".join(["?"] * len(ids))
    rows = conn.execute(
        f"SELECT content FROM chunks WHERE id IN ({qmarks})",
        ids,
    ).fetchall()
    return [_clean_text(str(r["content"])) for r in rows]


def _top_file_topics(conn: sqlite3.Connection, chunk_ids: List[int], topn: int = 3) -> List[str]:
    """
    Use file name stems as topic candidates (often more 'human-topic' than TF-IDF keywords).
    """
    if not chunk_ids:
        return []
    qmarks = ",".join(["?"] * len(chunk_ids))
    rows = conn.execute(
        f"SELECT file_path FROM chunks WHERE id IN ({qmarks})",
        chunk_ids,
    ).fetchall()

    names: List[str] = []
    for r in rows:
        fp = str(r["file_path"])
        stem = Path(fp).stem  # keep original language
        stem = re.sub(r"\s+", " ", stem).strip().lower()

        # remove very common suffix/prefix noise
        stem = stem.replace(" - ", " ")
        stem = stem.replace("_", " ")

        if _is_noise_topic(stem):
            continue

        # avoid stems that are basically one generic token
        if stem in {"note", "notes", "temp", "tmp"}:
            continue

        names.append(stem)

    if not names:
        return []

    ctr = Counter(names)
    return [t for t, _ in ctr.most_common(topn)]


def label_clusters_tfidf(
    conn: sqlite3.Connection,
    members: Dict[int, List[int]],  # cluster_idx -> [chunk_id...]
    top_terms: int = 10,
) -> Dict[int, Tuple[str, str]]:
    """
    Returns mapping:
      cluster_idx -> (name, summary)

    Naming strategy (more human):
      1) take top file stems as topics (votes)
      2) fill remaining slots with TF-IDF keywords (deduped)
      3) normalize label prefixes (LeetCode· / Java· / 计算机网络· ...)
    """
    labels: Dict[int, Tuple[str, str]] = {}

    # Token pattern: keep words >= 2 chars, allow Chinese
    token_pattern = r"(?u)\b[0-9A-Za-z\u4e00-\u9fff]{2,}\b"
    stop_words = sorted(STOPWORDS)

    for cidx, chunk_ids in members.items():
        texts = _fetch_texts_for_cluster(conn, chunk_ids, max_docs=40)
        if not texts:
            labels[cidx] = (f"Cluster {cidx}", "No texts available")
            continue

        vec = TfidfVectorizer(
            max_features=4000,
            token_pattern=token_pattern,
            ngram_range=(1, 2),
            stop_words=stop_words,
            min_df=2,  # ignore one-off tokens
        )

        try:
            X = vec.fit_transform(texts)
        except ValueError:
            labels[cidx] = (f"Cluster {cidx}", "Top keywords: (empty after filtering)")
            continue

        terms = vec.get_feature_names_out()
        scores = X.sum(axis=0).A1
        top_idx = scores.argsort()[::-1]

        picked: List[str] = []
        for i in top_idx:
            t = str(terms[i]).strip().lower()
            if scores[i] <= 0:
                break
            if _is_noise_topic(t):
                continue
            # filter duplicates / near-duplicates
            if any(t == p or t in p or p in t for p in picked):
                continue
            picked.append(t)
            if len(picked) >= top_terms:
                break

        # file-topic voting
        topics = _top_file_topics(conn, chunk_ids, topn=3)

        # build final name: topics first, then keywords
        parts: List[str] = []
        for t in topics:
            if t and all(t != p and t not in p and p not in t for p in parts):
                parts.append(t)
            if len(parts) >= 3:
                break

        for t in picked:
            if len(parts) >= 3:
                break
            if t and all(t != p and t not in p and p not in t for p in parts):
                parts.append(t)

        if not parts:
            name = f"Cluster {cidx}"
        else:
            name = " / ".join(_normalize_topic(x) for x in parts[:3])

        if picked:
            summary = "Top keywords: " + ", ".join(picked[:12])
        else:
            summary = "Top keywords: (none)"

        labels[cidx] = (name, summary)

    return labels
