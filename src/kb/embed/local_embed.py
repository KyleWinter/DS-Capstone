# src/kb/embed/local_embed.py
from __future__ import annotations

from functools import lru_cache
from typing import Iterable, List, Optional, Union

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "Missing dependency. Install with: pip install sentence-transformers torch"
    ) from e


DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_model(model_name: str = DEFAULT_MODEL) -> SentenceTransformer:
    """
    Load the local embedding model once per process.
    Cached to avoid re-loading on every request/script call.
    """
    return SentenceTransformer(model_name)


def embed_texts(
    texts: List[str],
    model_name: str = DEFAULT_MODEL,
    normalize: bool = True,
    batch_size: int = 64,
) -> np.ndarray:
    """
    Encode a list of texts into embeddings.

    Returns:
        np.ndarray of shape (n, dim), dtype float32
    """
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)

    model = _get_model(model_name)
    vecs = model.encode(
        texts,
        normalize_embeddings=normalize,
        batch_size=batch_size,
        show_progress_bar=False,
    )
    # sentence-transformers may return list/np.ndarray; normalize to float32 ndarray
    vecs = np.asarray(vecs, dtype=np.float32)
    return vecs


def embed_text(
    text: str,
    model_name: str = DEFAULT_MODEL,
    normalize: bool = True,
) -> np.ndarray:
    """
    Encode a single text into a 1D embedding vector.
    """
    vecs = embed_texts([text], model_name=model_name, normalize=normalize, batch_size=1)
    return vecs[0]


def to_blob(vec: np.ndarray) -> bytes:
    """
    Store embeddings in SQLite as BLOB.
    Always store float32 for compactness and consistency.
    """
    v = np.asarray(vec, dtype=np.float32)
    return v.tobytes()


def from_blob(blob: bytes, dtype: np.dtype = np.float32) -> np.ndarray:
    """
    Load embeddings from SQLite BLOB into 1D vector.
    """
    return np.frombuffer(blob, dtype=dtype)


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """
    Cosine similarity between 1D vectors.
    If you stored normalized embeddings, cosine is just dot(a, b).
    """
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)

    # If already normalized, dot is enough; still safe for general case.
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-12
    return float(np.dot(a, b) / denom)
