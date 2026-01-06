# pip install -U openai
# python scripts/build_embeddings.py --batch 64

from __future__ import annotations

from typing import List
import os

from openai import OpenAI


DEFAULT_MODEL = "text-embedding-3-small"


def embed_texts(texts: List[str], model: str = DEFAULT_MODEL) -> List[List[float]]:
    """
    Returns list of embeddings (float lists), one per input text.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in environment.")

    client = OpenAI(api_key=api_key)
    resp = client.embeddings.create(model=model, input=texts)
    # resp.data is in same order as inputs
    return [d.embedding for d in resp.data]
