from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)\s*$")


@dataclass(frozen=True)
class MdSection:
    """
    A markdown section defined by a heading and its body text.

    If a file has no headings, we will return a single section:
    heading=None, body=full text.
    """
    heading: str | None
    level: int | None
    start_line: int  # 1-based inclusive
    end_line: int    # 1-based inclusive
    body: str


def parse_markdown_sections(text: str) -> List[MdSection]:
    """
    Parse markdown into heading-based sections with line numbers.

    - Detect headings: '#', '##', ... '######'
    - Section body includes all lines until next heading (exclusive).
    """
    lines = text.splitlines()
    if not lines:
        return []

    # Find all heading lines (line_no is 1-based)
    headings: list[tuple[int, int, str]] = []  # (line_no, level, title)
    for i, line in enumerate(lines, start=1):
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            headings.append((i, level, title))

    # No headings: single section
    if not headings:
        return [
            MdSection(
                heading=None,
                level=None,
                start_line=1,
                end_line=len(lines),
                body="\n".join(lines).strip(),
            )
        ]

    sections: List[MdSection] = []
    for idx, (h_line, h_level, h_title) in enumerate(headings):
        body_start = h_line + 1
        body_end = (headings[idx + 1][0] - 1) if idx + 1 < len(headings) else len(lines)

        body = ""
        if body_start <= body_end:
            body = "\n".join(lines[body_start - 1 : body_end]).strip()

        sections.append(
            MdSection(
                heading=h_title,
                level=h_level,
                start_line=h_line,
                end_line=body_end,
                body=body,
            )
        )

    return sections
