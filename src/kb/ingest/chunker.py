from __future__ import annotations

from typing import Dict, List, Optional, Iterable
import re

from .parser import parse_markdown_sections

MIN_LEN = 200
MAX_LEN = 1500


# -------------------------
# Helpers: fenced code detection
# -------------------------

_FENCE_RE = re.compile(r"^\s*```")  # 简单够用：三反引号开/关


def _split_blocks_code_aware(text: str) -> List[str]:
    """
    Split text into "blocks" separated by blank lines, BUT do not split inside fenced code blocks.
    A "block" roughly corresponds to a paragraph / code block / list block.
    """
    lines = (text or "").splitlines()
    blocks: List[str] = []

    buf: List[str] = []
    in_fence = False

    def flush():
        nonlocal buf
        s = "\n".join(buf).strip()
        if s:
            blocks.append(s)
        buf = []

    for line in lines:
        if _FENCE_RE.match(line):
            # Fence toggles; keep the fence line in the same block
            in_fence = not in_fence
            buf.append(line)
            continue

        if not in_fence and line.strip() == "":
            # blank line splits blocks only when NOT inside fenced code
            flush()
        else:
            buf.append(line)

    flush()
    return blocks


def _split_long_text_nice(text: str, max_len: int) -> List[str]:
    """
    Split long non-code text into chunks <= max_len.
    Prefer splitting by:
      1) newline
      2) sentence boundary (Chinese/English punctuation)
      3) fallback hard cut
    """
    s = (text or "").strip()
    if len(s) <= max_len:
        return [s] if s else []

    # 1) Try newline-based split first (keeps code-like lines intact)
    parts: List[str] = []
    cur = ""

    def push_cur():
        nonlocal cur
        if cur.strip():
            parts.append(cur.strip())
        cur = ""

    for line in s.splitlines():
        if not line.strip():
            # treat empty line as soft boundary
            if len(cur) >= max_len:
                push_cur()
            else:
                cur += "\n"
            continue

        # if adding this line exceeds max_len, flush
        if cur and (len(cur) + 1 + len(line)) > max_len:
            push_cur()
        cur = (cur + "\n" + line) if cur else line

        if len(cur) >= max_len:
            push_cur()

    push_cur()

    # 2) If still some part too long (e.g., a single giant line), split by sentence punctuation
    final_parts: List[str] = []
    sent_boundary = re.compile(r"(?<=[。！？.!?])\s+")
    for p in parts:
        if len(p) <= max_len:
            final_parts.append(p)
            continue

        sentences = sent_boundary.split(p)
        cur2 = ""
        for sent in sentences:
            if not sent:
                continue
            if cur2 and (len(cur2) + 1 + len(sent)) > max_len:
                final_parts.append(cur2.strip())
                cur2 = sent
            else:
                cur2 = (cur2 + " " + sent) if cur2 else sent

            if len(cur2) >= max_len:
                final_parts.append(cur2.strip())
                cur2 = ""

        if cur2.strip():
            final_parts.append(cur2.strip())

    # 3) Final fallback: hard cut any remaining oversize segment
    out: List[str] = []
    for p in final_parts:
        if len(p) <= max_len:
            out.append(p)
        else:
            start = 0
            while start < len(p):
                out.append(p[start : start + max_len].strip())
                start += max_len

    return [x for x in out if x]


def _is_fenced_code_block(block: str) -> bool:
    b = (block or "").lstrip()
    return b.startswith("```") and b.rstrip().endswith("```")


def _merge_blocks(
    blocks: List[str],
    min_len: int,
    max_len: int,
) -> List[str]:
    """
    Merge small blocks into readable chunks.
    - Never merge across fenced code blocks in a way that splits them (we keep them intact).
    - Prefer producing chunks with length in [min_len, max_len] when possible.
    """
    out: List[str] = []
    buf = ""

    def flush_buf(force: bool = False):
        nonlocal buf
        if not buf.strip():
            buf = ""
            return
        if force or len(buf) >= min_len:
            out.append(buf.strip())
            buf = ""

    for blk in blocks:
        blk = (blk or "").strip()
        if not blk:
            continue

        # Keep fenced code blocks as atomic units (do not split inside)
        if _is_fenced_code_block(blk):
            # flush current buffer first if it's meaningful
            flush_buf(force=True)

            # If code block itself is too long, keep it as-is (still better than splitting)
            if len(blk) <= max_len:
                out.append(blk)
            else:
                # worst-case: code block too long; we split by lines but keep fence markers in each piece
                lines = blk.splitlines()
                if not lines:
                    continue
                head = lines[0]
                tail = lines[-1] if lines[-1].strip() == "```" else "```"
                body = lines[1:-1] if len(lines) >= 2 else []
                cur_lines: List[str] = []
                cur_len = len(head) + len(tail) + 2
                for ln in body:
                    add_len = len(ln) + 1
                    if cur_lines and (cur_len + add_len) > max_len:
                        piece = "\n".join([head] + cur_lines + [tail]).strip()
                        out.append(piece)
                        cur_lines = []
                        cur_len = len(head) + len(tail) + 2
                    cur_lines.append(ln)
                    cur_len += add_len
                if cur_lines:
                    piece = "\n".join([head] + cur_lines + [tail]).strip()
                    out.append(piece)
            continue

        # Non-code blocks: merge into buffer with blank line separation
        candidate = blk if not buf else (buf + "\n\n" + blk)

        if len(candidate) <= max_len:
            buf = candidate
            # if buffer already "good enough", flush for stability
            if len(buf) >= min_len:
                flush_buf()
        else:
            # buffer can't take this block; flush current then handle blk
            flush_buf(force=True)

            if len(blk) <= max_len:
                buf = blk
                if len(buf) >= min_len:
                    flush_buf()
            else:
                # blk itself too long; split nicely and add as chunks
                for piece in _split_long_text_nice(blk, max_len=max_len):
                    if len(piece) >= min_len:
                        out.append(piece)
                    else:
                        # tiny leftover: attach to previous chunk if possible
                        if out and (len(out[-1]) + 2 + len(piece)) <= max_len:
                            out[-1] = (out[-1] + "\n\n" + piece).strip()
                        else:
                            out.append(piece)

    # flush tail buffer (even if short, keep it; better than dropping content)
    if buf.strip():
        out.append(buf.strip())

    return out


def chunk_markdown(
    text: str,
    file_path: str,
    min_len: int = MIN_LEN,
    max_len: int = MAX_LEN,
) -> List[Dict]:
    """
    Convert a markdown document into chunks suitable for indexing.
    Improvements over v1:
    - code-fence aware splitting (```...```)
    - merge small blocks instead of dropping them
    - nicer splitting for long blocks (newline/sentence boundary first)
    """
    sections = parse_markdown_sections(text)
    chunks: List[Dict] = []
    ordinal = 0

    for sec in sections:
        if not sec.body:
            continue

        # 1) split into blocks but keep fenced code intact
        blocks = _split_blocks_code_aware(sec.body)

        # 2) merge blocks into readable chunks
        merged = _merge_blocks(blocks, min_len=min_len, max_len=max_len)

        for content in merged:
            content = (content or "").strip()
            if not content:
                continue

            chunks.append(
                {
                    "file_path": file_path,
                    "heading": sec.heading,
                    "start_line": sec.start_line,
                    "end_line": sec.end_line,
                    "ordinal": ordinal,
                    "content": content,
                }
            )
            ordinal += 1

    return chunks


# Backward compatible alias (if you previously used chunk_text)
def chunk_text(text: str, file_path: str) -> List[Dict]:
    return chunk_markdown(text=text, file_path=file_path)
