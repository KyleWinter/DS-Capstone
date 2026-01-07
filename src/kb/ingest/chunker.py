# src/kb/ingest/chunker.py
from __future__ import annotations

from typing import Dict, List, Optional, TypedDict
import re

from .parser import parse_markdown_sections

# -------------------------
# Tunables
# -------------------------

# 目标：减少碎片，chunk 更像“一个知识点”
MIN_LEN_TEXT = 200
MAX_LEN = 1500

# 代码块允许更短；但我们尽量把短代码块与解释合并
MIN_LEN_CODE = 60

# “短解释”阈值：代码块后如果是短解释，强制合并
SHORT_EXPLAIN_LEN = int(MIN_LEN_TEXT * 0.8)

# 合并策略目标长度（越接近 max_len，碎片越少）
TARGET_RATIO = 0.75


# -------------------------
# Regex: fenced code + noise + topic boundary
# -------------------------

# 更严谨：只把 “整行的 ``` 或 ```lang” 当 fence
_FENCE_OPEN_RE = re.compile(r"^\s*```[\w+-]*\s*$")  # ``` 或 ```java / ```python
_FENCE_CLOSE_RE = re.compile(r"^\s*```\s*$")

# 噪声过滤：常见 Obsidian / 笔记仓库里的装饰块
_HTML_IMG_RE = re.compile(r"<img\s+[^>]*>", re.IGNORECASE)
_HTML_DIV_RE = re.compile(r"<div\s+[^>]*>|</div>", re.IGNORECASE)
_HTML_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_ONLY_PUNCT_RE = re.compile(r"^[\W_]+$", re.UNICODE)
_HRULE_RE = re.compile(r"^\s*([-*_]\s*){3,}\s*$")  # --- *** ___
_GFM_TOC_HINT_RE = re.compile(r"^\s*<!--\s*GFM-TOC\s*-->\s*$", re.IGNORECASE)

# “新知识点”启发式：遇到这些开头，宁可断开也别粘连
_NEW_TOPIC_RE = re.compile(
    r"^\s*(#{3,6}\s+|[-*]\s+|\d+\.\s+|注意[:：]|结论[:：]|定义[:：]|例子[:：]|步骤[:：]|总结[:：])"
)


class Block(TypedDict):
    text: str
    start_line: int  # 1-based
    end_line: int    # 1-based
    is_code: bool


class ChunkOut(TypedDict):
    file_path: str
    heading: str
    start_line: int
    end_line: int
    ordinal: int
    content: str


def _is_noise_block(block: str) -> bool:
    """
    Filter obviously non-informative blocks:
    - pure HTML wrappers for layout
    - image-only blocks
    - horizontal rules
    - GFM TOC markers
    - blocks that are basically only punctuation
    """
    s = (block or "").strip()
    if not s:
        return True

    if _GFM_TOC_HINT_RE.match(s):
        return True
    if _HRULE_RE.match(s):
        return True

    # HTML layout / images
    if _HTML_IMG_RE.search(s):
        # 仅当“图片-only”时才视作噪声；否则保留图注/说明
        s2 = _HTML_IMG_RE.sub("", s).strip()
        if not s2:
            return True

    if _HTML_DIV_RE.search(s) and len(s) < 200:
        return True
    if _HTML_BR_RE.search(s) and len(s) < 120:
        return True

    # 纯符号/装饰
    if _ONLY_PUNCT_RE.match(s):
        return True

    return False


def _is_fenced_code_block_text(block_text: str) -> bool:
    """
    稳健判定一个 block 是否是 fenced code block：
    - 首行必须是 open fence（``` 或 ```lang）
    - 尾部最后一个非空行必须是 close fence（```）
    """
    lines = (block_text or "").splitlines()
    if not lines:
        return False
    if not _FENCE_OPEN_RE.match(lines[0]):
        return False

    j = len(lines) - 1
    while j >= 0 and lines[j].strip() == "":
        j -= 1
    return j >= 1 and _FENCE_CLOSE_RE.match(lines[j])


# -------------------------
# Block splitting: code-fence aware + line spans
# -------------------------

def _split_blocks_code_aware(text: str, base_line_1based: int) -> List[Block]:
    """
    Split into blocks separated by blank lines, but do NOT split inside fenced code blocks.
    Return blocks with 1-based line spans (approx. within section body),
    where base_line_1based should be the 1-based line number of the first line of `text`
    in the original document.
    """
    lines = (text or "").splitlines()
    blocks: List[Block] = []

    buf: List[str] = []
    in_fence = False
    buf_start_idx0: Optional[int] = None  # 0-based line index in `lines`

    def flush(end_idx0: int):
        nonlocal buf, buf_start_idx0
        s = "\n".join(buf).strip()
        if s and not _is_noise_block(s):
            start0 = buf_start_idx0 if buf_start_idx0 is not None else 0
            start_line = base_line_1based + start0
            end_line = base_line_1based + max(end_idx0, start0)
            blocks.append(
                {
                    "text": s,
                    "start_line": start_line,
                    "end_line": end_line,
                    "is_code": _is_fenced_code_block_text(s),
                }
            )
        buf = []
        buf_start_idx0 = None

    for i0, line in enumerate(lines):
        if buf_start_idx0 is None and line.strip() != "":
            buf_start_idx0 = i0

        # fence open/close
        if not in_fence and _FENCE_OPEN_RE.match(line):
            in_fence = True
            buf.append(line)
            continue
        if in_fence and _FENCE_CLOSE_RE.match(line):
            buf.append(line)
            in_fence = False
            continue

        if not in_fence and line.strip() == "":
            # blank line as delimiter
            if buf:
                flush(i0 - 1)
        else:
            buf.append(line)

    if buf:
        flush(len(lines) - 1)

    return blocks


# -------------------------
# Long block splitting (line-based, keeps spans)
# -------------------------

def _split_long_block_linewise(block: Block, max_len: int) -> List[Block]:
    """
    Split an oversized non-code block into multiple blocks <= max_len.
    Line-based splitting so we can keep start/end line spans reasonably correct.
    """
    text = (block["text"] or "").strip()
    if not text:
        return []
    if len(text) <= max_len:
        return [block]

    lines = text.splitlines()
    out: List[Block] = []

    cur_lines: List[str] = []
    cur_start_line = block["start_line"]
    cur_end_line = cur_start_line - 1

    def push():
        nonlocal cur_lines, cur_start_line, cur_end_line
        s = "\n".join(cur_lines).strip()
        if s:
            out.append(
                {
                    "text": s,
                    "start_line": cur_start_line,
                    "end_line": cur_end_line,
                    "is_code": False,
                }
            )
        cur_lines = []

    # Map each line to its original line number (1-based)
    for idx0, ln in enumerate(lines):
        ln_no = block["start_line"] + idx0
        if not cur_lines:
            cur_start_line = ln_no
            cur_end_line = ln_no

        candidate = ("\n".join(cur_lines) + ("\n" if cur_lines else "") + ln).strip()
        if len(candidate) <= max_len:
            cur_lines.append(ln)
            cur_end_line = ln_no
            continue

        # If current buffer has something, push it first
        if cur_lines:
            push()
            # start new with this line
            cur_start_line = ln_no
            cur_end_line = ln_no

        # Single line itself is still too long -> hard cut it
        if len(ln) > max_len:
            start = 0
            while start < len(ln):
                piece = ln[start : start + max_len].strip()
                if piece:
                    out.append(
                        {
                            "text": piece,
                            "start_line": ln_no,
                            "end_line": ln_no,
                            "is_code": False,
                        }
                    )
                start += max_len
            cur_lines = []
        else:
            cur_lines = [ln]
            cur_end_line = ln_no

    if cur_lines:
        push()

    return out


# -------------------------
# Merge strategy: reduce fragmentation (but respect topic boundaries)
# -------------------------

def _merge_blocks(blocks: List[Block], min_len: int, max_len: int) -> List[Block]:
    """
    Merge small blocks into readable chunks.

    Key behaviors:
    1) Code blocks are atomic BUT:
       - short code blocks prefer to merge with adjacent explanation text
       - explanation after a code block is forced to merge (if short)
    2) Text blocks merge until reaching ~target, not min_len, to reduce fragmentation.
    3) Respect heuristic topic boundaries: when blk looks like a new sub-topic, flush first.
    4) Never drop short-but-informative text; prefer merging instead.
    """
    out: List[Block] = []
    target = int(max_len * TARGET_RATIO)

    buf_text = ""
    buf_start = 0
    buf_end = 0
    buf_is_code = False

    def buf_empty() -> bool:
        return not buf_text.strip()

    def buf_set_from_block(b: Block):
        nonlocal buf_text, buf_start, buf_end, buf_is_code
        buf_text = b["text"].strip()
        buf_start = b["start_line"]
        buf_end = b["end_line"]
        buf_is_code = b["is_code"]

    def buf_append_text(text: str, start_line: int, end_line: int):
        nonlocal buf_text, buf_start, buf_end
        if buf_empty():
            buf_text = text.strip()
            buf_start = start_line
            buf_end = end_line
        else:
            buf_text = (buf_text.strip() + "\n\n" + text.strip()).strip()
            buf_start = min(buf_start, start_line)
            buf_end = max(buf_end, end_line)

    def flush(force: bool = False):
        nonlocal buf_text, buf_start, buf_end, buf_is_code
        if buf_empty():
            buf_text = ""
            return
        if force or len(buf_text) >= min_len or buf_is_code:
            out.append(
                {
                    "text": buf_text.strip(),
                    "start_line": buf_start,
                    "end_line": buf_end,
                    "is_code": buf_is_code,
                }
            )
            buf_text = ""
            buf_is_code = False
            buf_start = 0
            buf_end = 0

    for blk in blocks:
        text = (blk["text"] or "").strip()
        if not text or _is_noise_block(text):
            continue

        is_code = blk["is_code"]

        # Heuristic: new topic start -> flush existing buffer first
        if not is_code and not buf_empty() and not buf_is_code and _NEW_TOPIC_RE.match(text):
            flush(force=True)

        # -------------------------
        # Case A: fenced code block
        # -------------------------
        if is_code:
            # If current buf is explanation text and can fit, merge code into it
            if not buf_empty() and not buf_is_code and (len(buf_text) + 2 + len(text)) <= max_len:
                buf_append_text(text, blk["start_line"], blk["end_line"])
                # buffer now contains code + text => treat as non-code chunk (but semantically mixed)
                buf_is_code = False
                continue

            # else: flush existing buf, start buf as code
            flush(force=True)
            buf_set_from_block(blk)
            # keep as code for now; allow short explanation right after to merge
            buf_is_code = True
            continue

        # -------------------------
        # Case B: normal text block
        # -------------------------

        # If buf is a code block and this is a short explanation, force merge
        if not buf_empty() and buf_is_code and len(text) < SHORT_EXPLAIN_LEN:
            candidate_len = len(buf_text) + 2 + len(text)
            if candidate_len <= max_len:
                buf_append_text(text, blk["start_line"], blk["end_line"])
                buf_is_code = False  # now it's code+explain chunk
                # don't flush immediately; let it grow toward target
                if len(buf_text) >= target:
                    flush(force=True)
                continue
            # can't fit -> flush code as its own chunk, then continue as text
            flush(force=True)

        # Normal merge attempt
        if buf_empty():
            buf_set_from_block(blk)
            buf_is_code = False
            if len(buf_text) >= target:
                flush(force=True)
            continue

        candidate_len = len(buf_text) + 2 + len(text)
        if candidate_len <= max_len:
            buf_append_text(text, blk["start_line"], blk["end_line"])
            buf_is_code = False
            if len(buf_text) >= target:
                flush(force=True)
        else:
            # buf can't fit blk -> flush buf first
            flush(force=True)

            # if blk itself is too long -> split it linewise
            if len(text) > max_len:
                pieces = _split_long_block_linewise(blk, max_len=max_len)
                for p in pieces:
                    # Keep short pieces; later cleanup may merge
                    out.append(p)
                continue

            # else start new buffer with blk
            buf_set_from_block(blk)
            buf_is_code = False
            if len(buf_text) >= target:
                flush(force=True)

    # Tail flush: keep whatever remains (do not drop short informative text)
    if not buf_empty():
        flush(force=True)

    # -------------------------
    # Final cleanup: avoid tiny text-only fragments (merge backward when safe)
    # -------------------------
    cleaned: List[Block] = []
    for b in out:
        t = (b["text"] or "").strip()
        if not t:
            continue
        if b["is_code"]:
            cleaned.append(b)
            continue

        if len(t) < int(min_len * 0.6):
            # Prefer merging into previous chunk if it fits
            if cleaned and (len(cleaned[-1]["text"]) + 2 + len(t)) <= max_len:
                prev = cleaned[-1]
                prev["text"] = (prev["text"].strip() + "\n\n" + t).strip()
                prev["start_line"] = min(prev["start_line"], b["start_line"])
                prev["end_line"] = max(prev["end_line"], b["end_line"])
                prev["is_code"] = prev["is_code"]  # unchanged
                cleaned[-1] = prev
            else:
                cleaned.append(b)
            continue

        cleaned.append(b)

    # Recompute is_code robustly (in case of merges)
    for b in cleaned:
        b["is_code"] = _is_fenced_code_block_text(b["text"])

    return cleaned


# -------------------------
# Heading path helper (best-effort, backward compatible)
# -------------------------

def _get_heading_level(sec) -> Optional[int]:
    """
    Best-effort get heading level from section object if parser provides it.
    Common field names: level, heading_level, depth.
    """
    for k in ("level", "heading_level", "depth"):
        v = getattr(sec, k, None)
        if isinstance(v, int) and v > 0:
            return v
    return None


def _build_heading_paths(sections) -> List[str]:
    """
    Build heading paths like "A / B / C" if levels are available.
    If not, fall back to sec.heading.
    """
    stack: List[str] = []
    paths: List[str] = []
    for sec in sections:
        h = (getattr(sec, "heading", "") or "").strip()
        lvl = _get_heading_level(sec)
        if not h:
            paths.append("")
            continue

        if lvl is None:
            paths.append(h)
            continue

        # Ensure stack length = lvl-1, then push this heading
        while len(stack) >= lvl:
            stack.pop()
        stack.append(h)
        paths.append(" / ".join(stack))
    return paths


# -------------------------
# Public API
# -------------------------

def chunk_markdown(
    text: str,
    file_path: str,
    min_len: int = MIN_LEN_TEXT,
    max_len: int = MAX_LEN,
) -> List[Dict]:
    """
    Convert a markdown document into chunks suitable for indexing.

    Features:
    - fence-aware splitting (no split inside code fences)
    - noise filtering (img/div/br/hr/toc markers), but keeps image captions
    - merge strategy targets ~0.75*max_len to reduce fragmentation
    - respects heuristic topic boundaries to reduce topic bleeding
    - short code blocks merge with adjacent explanation when possible
    - keeps short-but-informative explanation (never drop by length)
    - best-effort line spans for each chunk (more accurate than section-level spans)
    """
    sections = parse_markdown_sections(text)
    heading_paths = _build_heading_paths(sections)

    chunks: List[ChunkOut] = []
    ordinal = 0

    for idx, sec in enumerate(sections):
        body = getattr(sec, "body", None)
        if not body:
            continue

        # Best-effort: if parser provides body_start_line, use it; else use sec.start_line
        base_line = getattr(sec, "body_start_line", None)
        if not isinstance(base_line, int) or base_line <= 0:
            base_line = getattr(sec, "start_line", 1)
            if not isinstance(base_line, int) or base_line <= 0:
                base_line = 1

        blocks = _split_blocks_code_aware(body, base_line_1based=base_line)
        merged = _merge_blocks(blocks, min_len=min_len, max_len=max_len)

        heading = heading_paths[idx] if idx < len(heading_paths) and heading_paths[idx] else getattr(sec, "heading", "")

        for b in merged:
            content = (b["text"] or "").strip()
            if not content:
                continue
            if _is_noise_block(content):
                continue

            chunks.append(
                {
                    "file_path": file_path,
                    "heading": heading,
                    "start_line": b["start_line"],
                    "end_line": b["end_line"],
                    "ordinal": ordinal,
                    "content": content,
                }
            )
            ordinal += 1

    return chunks


# Backward compatible alias
def chunk_text(text: str, file_path: str) -> List[Dict]:
    return chunk_markdown(text=text, file_path=file_path)
