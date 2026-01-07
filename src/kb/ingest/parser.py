from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


# ATX heading: allow up to 3 leading spaces; allow trailing hashes.
# Examples:
#   "## Title"
#   "  ### Title ###   "
_ATX_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*(?:#+\s*)?$")

# Setext heading underline:
#   "Title"
#   "====="  -> level 1
#   "-----"  -> level 2
_SETEXT_H1_RE = re.compile(r"^\s{0,3}=+\s*$")
_SETEXT_H2_RE = re.compile(r"^\s{0,3}-+\s*$")

# Fenced code blocks (``` or ~~~). We should ignore headings inside.
_FENCE_RE = re.compile(r"^\s{0,3}(```|~~~)")


@dataclass(frozen=True)
class MdSection:
    """
    A markdown section defined by a heading and its body text.

    If a file has no headings, we return a single section:
    heading=None, body=full text.
    """
    heading: Optional[str]
    level: Optional[int]
    start_line: int  # 1-based inclusive (heading line)
    end_line: int    # 1-based inclusive (last line of body; could equal start_line if empty body)
    body: str


def parse_markdown_sections(text: str) -> List[MdSection]:
    """
    Parse markdown into heading-based sections with line numbers.

    Supports:
    - ATX headings: '#', '##', ... '######' (ignores trailing hashes)
    - Setext headings: 'Title' + '====' / '----'
    - Ignores headings inside fenced code blocks.
    """
    lines = text.splitlines()
    if not lines:
        return []

    # Collect headings as tuples: (line_no, level, title, is_setext)
    headings: List[tuple[int, int, str, bool]] = []

    in_fence = False
    fence_token: Optional[str] = None

    def toggle_fence(line: str) -> None:
        nonlocal in_fence, fence_token
        m = _FENCE_RE.match(line)
        if not m:
            return
        token = m.group(1)
        if not in_fence:
            in_fence = True
            fence_token = token
        else:
            # Close fence only if same token family is used (``` closes ```; ~~~ closes ~~~)
            if fence_token == token:
                in_fence = False
                fence_token = None

    # Pass 1: identify headings
    i = 1
    while i <= len(lines):
        line = lines[i - 1]

        # Fence handling first
        toggle_fence(line)
        if in_fence:
            i += 1
            continue

        # ATX
        m = _ATX_HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            if title:
                headings.append((i, level, title, False))
            i += 1
            continue

        # Setext: needs a next line underline
        if i < len(lines):
            underline = lines[i]
            if _SETEXT_H1_RE.match(underline):
                title = line.strip()
                if title:
                    headings.append((i, 1, title, True))  # heading is the title line
                i += 2
                continue
            if _SETEXT_H2_RE.match(underline):
                title = line.strip()
                if title:
                    headings.append((i, 2, title, True))
                i += 2
                continue

        i += 1

    # No headings: single section
    if not headings:
        body = "\n".join(lines).strip()
        return [
            MdSection(
                heading=None,
                level=None,
                start_line=1,
                end_line=len(lines),
                body=body,
            )
        ]

    # Pass 2: build sections using heading boundaries
    sections: List[MdSection] = []
    for idx, (h_line, h_level, h_title, is_setext) in enumerate(headings):
        # Body starts after the heading line.
        # For setext headings, the underline line is part of the heading syntax,
        # but the "heading line" we store is the title line. Body starts after underline.
        body_start = h_line + (2 if is_setext else 1)

        next_heading_line = headings[idx + 1][0] if idx + 1 < len(headings) else (len(lines) + 1)
        body_end = next_heading_line - 1

        # Clamp
        if body_start > len(lines):
            body_start = len(lines) + 1
        if body_end > len(lines):
            body_end = len(lines)

        body = ""
        if body_start <= body_end:
            body = "\n".join(lines[body_start - 1 : body_end]).strip()

        # end_line should be the last line included in this section (heading + body)
        section_end_line = max(h_line, body_end)

        sections.append(
            MdSection(
                heading=h_title,
                level=h_level,
                start_line=h_line,
                end_line=section_end_line,
                body=body,
            )
        )

    return sections
