#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import sqlite3
import time
import os
from typing import Dict, List, Tuple, Optional

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from openai import OpenAI

from src.kb.config import DB_PATH
from src.kb.store.db import get_conn, init_db
from src.kb.embed.openai_embed import embed_texts, DEFAULT_MODEL


# -------------------------
# DB helpers
# -------------------------

def ensure_module_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS modules (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          description TEXT,
          created_at REAL DEFAULT (strftime('%s','now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS file_modules (
          file_path TEXT PRIMARY KEY,
          module_id INTEGER NOT NULL,
          score REAL DEFAULT 1.0,
          updated_at REAL DEFAULT (strftime('%s','now')),
          FOREIGN KEY(module_id) REFERENCES modules(id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_file_modules_module_id ON file_modules(module_id)")


def fetch_file_reprs(
    conn: sqlite3.Connection,
    limit: Optional[int] = None,
    preview_max: int = 900,
) -> List[Tuple[str, str]]:
    """
    Return [(file_path, doc_repr), ...]
    doc_repr = Title + top headings + a richer preview (first + longest chunks).
    """
    q = "SELECT path FROM files ORDER BY path"
    if limit:
        q += f" LIMIT {int(limit)}"
    files = [str(r["path"]) for r in conn.execute(q).fetchall()]

    out: List[Tuple[str, str]] = []
    for fp in files:
        title = Path(fp).stem

        # headings: take top 8 distinct headings (non-empty)
        hrows = conn.execute(
            """
            SELECT COALESCE(heading,'') AS heading
            FROM chunks
            WHERE file_path=?
            ORDER BY ordinal
            LIMIT 80
            """,
            (fp,),
        ).fetchall()
        headings: List[str] = []
        seen = set()
        for r in hrows:
            h = str(r["heading"]).strip()
            if h and h not in seen:
                seen.add(h)
                headings.append(h)
            if len(headings) >= 8:
                break

        # preview: combine first 2 chunks + longest 2 chunks (dedup), then truncate
        first_rows = conn.execute(
            """
            SELECT id, content
            FROM chunks
            WHERE file_path=?
            ORDER BY ordinal
            LIMIT 2
            """,
            (fp,),
        ).fetchall()

        long_rows = conn.execute(
            """
            SELECT id, content
            FROM chunks
            WHERE file_path=?
            ORDER BY LENGTH(content) DESC
            LIMIT 2
            """,
            (fp,),
        ).fetchall()

        picked: List[str] = []
        seen_ids = set()
        for r in list(first_rows) + list(long_rows):
            cid = int(r["id"])
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            picked.append(str(r["content"]).strip())

        preview = "\n\n".join([p for p in picked if p]).replace("\n", " ").strip()
        if len(preview) > preview_max:
            preview = preview[:preview_max] + "…"

        doc_repr = f"Title: {title}\nHeadings: " + "; ".join(headings) + f"\nPreview: {preview}"
        out.append((fp, doc_repr))

    return out


# -------------------------
# Clustering
# -------------------------

def l2_normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12
    return mat / norms


def cluster_docs(embeddings: np.ndarray, distance_threshold: float) -> np.ndarray:
    """
    Agglomerative clustering with cosine distance.
    """
    model = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=float(distance_threshold),
        metric="cosine",
        linkage="average",
    )
    return model.fit_predict(embeddings)


def _cluster_indices(labels: np.ndarray) -> Dict[int, List[int]]:
    out: Dict[int, List[int]] = {}
    for i, lab in enumerate(labels.tolist()):
        out.setdefault(int(lab), []).append(i)
    return out


def _centroid(mat: np.ndarray, idxs: List[int]) -> np.ndarray:
    c = mat[idxs].mean(axis=0)
    n = np.linalg.norm(c) + 1e-12
    return c / n


def _pick_examples_center_and_boundary(
    mat: np.ndarray,
    idxs: List[int],
    titles: List[str],
    headings_lines: List[str],
    max_examples: int,
) -> List[Dict[str, str]]:
    """
    Pick representative examples:
      - top ~80% closest to centroid
      - bottom ~20% farthest (boundary)
    """
    if not idxs:
        return []

    max_examples = max(1, int(max_examples))
    c = _centroid(mat, idxs)
    sims = [(i, float(mat[i] @ c)) for i in idxs]
    sims.sort(key=lambda x: x[1], reverse=True)

    # center: most representative
    n_center = max(1, int(round(max_examples * 0.8)))
    n_boundary = max_examples - n_center

    picked = [i for i, _ in sims[:n_center]]
    if n_boundary > 0 and len(sims) > n_center:
        picked += [i for i, _ in sims[-n_boundary:]]

    # dedup while preserving order
    seen = set()
    uniq = []
    for i in picked:
        if i not in seen:
            seen.add(i)
            uniq.append(i)

    return [{"title": titles[i], "headings": headings_lines[i]} for i in uniq]


def merge_small_clusters(
    mat: np.ndarray,
    labels: np.ndarray,
    min_size: int = 3,
    sim_threshold: float = 0.80,
) -> np.ndarray:
    """
    Merge clusters with size < min_size into nearest big cluster by centroid similarity.
    If no centroid similarity >= sim_threshold, keep as-is.
    """
    labels = labels.astype(int).copy()
    groups = _cluster_indices(labels)

    big = {cid: idxs for cid, idxs in groups.items() if len(idxs) >= min_size}
    small = {cid: idxs for cid, idxs in groups.items() if len(idxs) < min_size}

    if not big or not small:
        return labels

    big_centroids = {cid: _centroid(mat, idxs) for cid, idxs in big.items()}

    for scid, idxs in small.items():
        c_small = _centroid(mat, idxs)
        best_cid = None
        best_sim = -1.0
        for bcid, c_big in big_centroids.items():
            sim = float(c_small @ c_big)
            if sim > best_sim:
                best_sim = sim
                best_cid = bcid

        if best_cid is not None and best_sim >= sim_threshold:
            for i in idxs:
                labels[i] = int(best_cid)

    # re-label to 0..K-1 for nicer output
    unique = sorted(set(labels.tolist()))
    remap = {old: new for new, old in enumerate(unique)}
    labels = np.array([remap[int(x)] for x in labels.tolist()], dtype=int)
    return labels


# -------------------------
# Naming clusters with OpenAI (Structured Outputs)
# -------------------------

def name_cluster_with_llm(
    client: OpenAI,
    examples: List[Dict[str, str]],
    model: str,
) -> Dict[str, str]:
    schema = {
        "type": "object",
        "properties": {
            "folder_name": {"type": "string", "minLength": 1},
            "description": {"type": "string", "minLength": 1},
        },
        "required": ["folder_name", "description"],
        "additionalProperties": False,
    }

    prompt = (
        "你是一个知识库整理助手。给定一组相似笔记（标题/小纲要），"
        "请为它们命名一个简短的模块/文件夹名（folder_name，适合做目录名，尽量短，中文为主，允许包含少量英文术语），"
        "并给出一句话描述（description）。\n\n"
        "示例列表：\n"
        + "\n".join([f"- {e['title']} | {e['headings']}" for e in examples])
    )

    resp = client.responses.create(
        model=model,
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "module_naming",
                "schema": schema,
                "strict": True,
            }
        },
        temperature=0.2,
    )

    import json
    raw = resp.output_text
    return json.loads(raw)


# -------------------------
# Persist results
# -------------------------

def upsert_module(conn: sqlite3.Connection, name: str, description: str) -> int:
    row = conn.execute("SELECT id FROM modules WHERE name=?", (name,)).fetchone()
    if row:
        mid = int(row["id"])
        conn.execute("UPDATE modules SET description=? WHERE id=?", (description, mid))
        return mid
    cur = conn.execute("INSERT INTO modules(name, description) VALUES (?, ?)", (name, description))
    return int(cur.lastrowid)


def write_file_modules(conn: sqlite3.Connection, mapping: Dict[str, int]) -> None:
    now = time.time()
    conn.executemany(
        """
        INSERT INTO file_modules(file_path, module_id, score, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(file_path) DO UPDATE SET
          module_id=excluded.module_id,
          score=excluded.score,
          updated_at=excluded.updated_at
        """,
        [(fp, mid, 1.0, now) for fp, mid in mapping.items()],
    )


# -------------------------
# Main
# -------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--embed-model", default=DEFAULT_MODEL)
    ap.add_argument("--name-model", default="gpt-4.1-mini")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--limit", type=int, default=0, help="limit files for debugging")
    ap.add_argument("--distance-threshold", type=float, default=0.40, help="smaller -> more clusters")

    ap.add_argument("--preview-max", type=int, default=900, help="max chars for preview in doc_repr")

    ap.add_argument("--max-examples", type=int, default=10, help="examples per cluster to name")
    ap.add_argument("--no-name", action="store_true", help="skip LLM naming (cheaper for tuning)")

    ap.add_argument("--merge-small", dest="merge_small", action="store_true", help="merge small clusters into big ones")
    ap.add_argument("--no-merge-small", dest="merge_small", action="store_false", help="do not merge small clusters")
    ap.set_defaults(merge_small=True)
    ap.add_argument("--merge-min-size", type=int, default=3, help="clusters smaller than this are considered small")
    ap.add_argument("--merge-threshold", type=float, default=0.80, help="cosine sim threshold to merge small -> big")

    args = ap.parse_args()

    conn = get_conn(DB_PATH)
    init_db(conn)
    ensure_module_tables(conn)

    files = fetch_file_reprs(conn, limit=(args.limit or None), preview_max=args.preview_max)
    if not files:
        print("No files found in DB. Run build_index.py first.")
        return

    file_paths = [fp for fp, _ in files]
    doc_texts = [t for _, t in files]

    # For naming examples we also keep parsed title/headings line per file
    titles = [Path(fp).stem for fp in file_paths]
    headings_lines: List[str] = []
    for doc in doc_texts:
        hl = ""
        for line in doc.splitlines():
            if line.startswith("Headings:"):
                hl = line.replace("Headings:", "").strip()
                break
        headings_lines.append(hl)

    # 1) embeddings
    res = embed_texts(doc_texts, model=args.embed_model, batch_size=args.batch)
    embs = res["embeddings"]
    dims = int(res["dims"])
    if not embs or len(embs) != len(doc_texts):
        raise RuntimeError(f"Bad embeddings: got={len(embs) if embs else 0}, expected={len(doc_texts)}")

    mat = np.asarray(embs, dtype=np.float32)
    mat = l2_normalize(mat)

    # 2) clustering
    labels = cluster_docs(mat, distance_threshold=args.distance_threshold)

    # 2.5) merge small clusters (optional)
    if args.merge_small:
        labels = merge_small_clusters(
            mat,
            labels,
            min_size=args.merge_min_size,
            sim_threshold=args.merge_threshold,
        )

    n_clusters = int(labels.max()) + 1 if labels.size else 0
    print(f"Clusters: {n_clusters} (distance_threshold={args.distance_threshold}, dims={dims}, merge_small={args.merge_small})")

    groups = _cluster_indices(labels)

    # 3) name clusters via LLM (optional)
    client = None if args.no_name else OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    file_to_module_id: Dict[str, int] = {}

    for cid in sorted(groups.keys()):
        idxs = groups[cid]
        size = len(idxs)

        if args.no_name:
            folder_name = f"cluster_{cid:03d}"
            description = f"Auto cluster {cid} (size={size})"
        else:
            examples = _pick_examples_center_and_boundary(
                mat=mat,
                idxs=idxs,
                titles=titles,
                headings_lines=headings_lines,
                max_examples=args.max_examples,
            )
            named = name_cluster_with_llm(client, examples=examples, model=args.name_model)
            folder_name = named["folder_name"].strip()
            description = named["description"].strip()

        mid = upsert_module(conn, folder_name, description)
        for i in idxs:
            file_to_module_id[file_paths[i]] = mid

        print(f"[cluster {cid}] -> {folder_name} ({size} files)")

    with conn:
        write_file_modules(conn, file_to_module_id)

    conn.close()
    print("✅ build_modules finished.")


if __name__ == "__main__":
    main()
