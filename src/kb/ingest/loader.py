from __future__ import annotations

from pathlib import Path
from typing import Iterator, Tuple


def iter_markdown_files(root: Path) -> Iterator[Path]:
    """
    Recursively iterate all .md files under root.

    Skips:
    - hidden directories (starting with '.')
    - hidden files (starting with '.')
    """
    root = root.resolve()
    for p in root.rglob("*.md"):
        if not p.is_file():
            continue
        # Skip hidden files/dirs
        parts = p.relative_to(root).parts
        if any(part.startswith(".") for part in parts):
            continue
        yield p


def load_markdown(path: Path) -> Tuple[str, int]:
    """
    Load markdown file content as text.
    Returns (text, line_count).
    """
    text = path.read_text(encoding="utf-8", errors="ignore")
    line_count = text.count("\n") + 1 if text else 0
    return text, line_count
