# src/kb/embed/openai_embed.py
from __future__ import annotations

from typing import List, Dict, Any
import os
import time

from openai import OpenAI, OpenAIError

DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_BATCH_SIZE = 64
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0  # seconds

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in environment.")
        _client = OpenAI(api_key=api_key)
    return _client


def _batched(items: List[str], batch_size: int):
    for i in range(0, len(items), batch_size):
        yield i, items[i : i + batch_size]


def embed_texts(
    texts: List[str],
    model: str = DEFAULT_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> Dict[str, Any]:
    """
    Embed texts safely.

    Returns:
        {
            "model": str,
            "dims": int,
            "embeddings": List[List[float]]
        }
    """
    if not texts:
        return {"model": model, "dims": 0, "embeddings": []}

    client = _get_client()
    all_embeddings: List[List[float]] = []

    for start_idx, batch in _batched(texts, batch_size):
        attempt = 0
        while True:
            try:
                resp = client.embeddings.create(model=model, input=batch)
                batch_embeddings = [d.embedding for d in resp.data]
                all_embeddings.extend(batch_embeddings)
                break
            except OpenAIError as e:
                attempt += 1
                if attempt > MAX_RETRIES:
                    raise RuntimeError(
                        f"Embedding failed after {MAX_RETRIES} retries "
                        f"(batch starting at index {start_idx})"
                    ) from e
                time.sleep(RETRY_BACKOFF * attempt)

    dims = len(all_embeddings[0]) if all_embeddings else 0
    return {"model": model, "dims": dims, "embeddings": all_embeddings}

def name_cluster(examples: list[dict], model="gpt-5.2") -> dict:
    """
    examples: [{"title": "...", "headings": [...]}...]
    return: {"folder_name": "...", "description": "..."}
    """
