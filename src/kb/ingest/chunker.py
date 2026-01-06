from __future__ import annotations

from typing import Dict, List, Optional

from .parser import parse_markdown_sections


MIN_LEN = 200
MAX_LEN = 1500


def _split_paragraphs(text: str) -> List[str]:
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    return parts


def _force_split_long(text: str, max_len: int) -> List[str]:
    out: List[str] = []
    start = 0
    while start < len(text):
        out.append(text[start : start + max_len])
        start += max_len
    return out


def chunk_markdown(
    text: str,
    file_path: str,
    min_len: int = MIN_LEN,
    max_len: int = MAX_LEN,
) -> List[Dict]:
    """
    Convert a markdown document into chunks suitable for indexing.
    Uses heading-based sections; each chunk carries section heading.

    Returns list of dict:
      {
        "file_path": str,
        "heading": Optional[str],
        "start_line": Optional[int],
        "end_line": Optional[int],
        "ordinal": int,
        "content": str,
      }
    """
    sections = parse_markdown_sections(text)
    chunks: List[Dict] = []
    ordinal = 0

    for sec in sections:
        # If section body is empty, skip
        if not sec.body:
            continue

        paragraphs = _split_paragraphs(sec.body)

        for para in paragraphs:
            if len(para) < min_len:
                # Too small; we can either drop or try to merge.
                # v1: drop tiny fragments to reduce noise.
                continue

            if len(para) <= max_len:
                chunks.append(
                    {
                        "file_path": file_path,
                        "heading": sec.heading,
                        "start_line": sec.start_line,
                        "end_line": sec.end_line,
                        "ordinal": ordinal,
                        "content": para,
                    }
                )
                ordinal += 1
            else:
                # Split very long paragraph
                for sub in _force_split_long(para, max_len):
                    sub = sub.strip()
                    if len(sub) < min_len:
                        continue
                    chunks.append(
                        {
                            "file_path": file_path,
                            "heading": sec.heading,
                            "start_line": sec.start_line,
                            "end_line": sec.end_line,
                            "ordinal": ordinal,
                            "content": sub,
                        }
                    )
                    ordinal += 1

    return chunks


# Backward compatible alias (if you previously used chunk_text)
def chunk_text(text: str, file_path: str) -> List[Dict]:
    return chunk_markdown(text=text, file_path=file_path)
