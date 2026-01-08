"""Text utilities for FTS preprocessing."""
from __future__ import annotations

import re
from typing import Iterable


# 只把“文字类 CJK”当作需要分隔的字符（不含标点/全角符号）
def is_cjk_letter(char: str) -> bool:
    code = ord(char)
    return (
        0x4E00 <= code <= 0x9FFF     # CJK Unified Ideographs (汉字)
        or 0x3400 <= code <= 0x4DBF  # CJK Extension A
        or 0x20000 <= code <= 0x2A6DF  # CJK Extension B
        or 0x2A700 <= code <= 0x2B73F  # CJK Extension C
        or 0x2B740 <= code <= 0x2B81F  # CJK Extension D
        or 0x2B820 <= code <= 0x2CEAF  # CJK Extension E
        or 0x3040 <= code <= 0x309F  # Hiragana
        or 0x30A0 <= code <= 0x30FF  # Katakana
        or 0xAC00 <= code <= 0xD7AF  # Hangul Syllables
    )


# 把常见符号当分隔符（包括全角）
# 注意：不把 '_' 当分隔符，避免把 snake_case 拆太碎；也不强拆 '-'，因为很多术语需要
_SEP_RE = re.compile(r"[^\w\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+", re.UNICODE)


def normalize_query(text: str) -> str:
    """
    Normalize query text:
    - lower for ASCII
    - collapse separators into spaces
    """
    if not text:
        return ""
    # 先把分隔符统一为空格
    s = _SEP_RE.sub(" ", text)
    # ASCII lower（中文不影响）
    s = s.lower()
    # 压缩空格
    return " ".join(s.split()).strip()


def tokenize_for_fts(text: str) -> str:
    """
    Tokenize text for FTS5 (unicode61) by inserting spaces between CJK letters
    while keeping latin/digits sequences intact.

    Examples:
      "链表是空节点" -> "链 表 是 空 节 点"
      "Hello世界"   -> "hello 世 界"
      "EIP-1559升级" -> "eip 1559 升 级"   (符号视为分隔)
      "0xabc123转账" -> "0xabc123 转 账"
    """
    s = normalize_query(text)
    if not s:
        return ""

    out: list[str] = []
    prev_space = True  # treat as boundary at start

    for ch in s:
        if ch == " ":
            if not prev_space:
                out.append(" ")
                prev_space = True
            continue

        if is_cjk_letter(ch):
            # CJK letter becomes its own token boundary
            if not prev_space:
                out.append(" ")
            out.append(ch)
            out.append(" ")
            prev_space = True
        else:
            # latin/digit/_ are kept in sequences
            out.append(ch)
            prev_space = False

    # strip trailing space if any + collapse multiple spaces
    return "".join(out).strip()
