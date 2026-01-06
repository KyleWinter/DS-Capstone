"""Text utilities for FTS preprocessing."""
import re


def is_cjk_char(char: str) -> bool:
    """Check if a character is CJK (Chinese, Japanese, Korean)."""
    code = ord(char)
    return (
        0x4E00 <= code <= 0x9FFF or  # CJK Unified Ideographs
        0x3400 <= code <= 0x4DBF or  # CJK Extension A
        0x20000 <= code <= 0x2A6DF or  # CJK Extension B
        0x2A700 <= code <= 0x2B73F or  # CJK Extension C
        0x2B740 <= code <= 0x2B81F or  # CJK Extension D
        0x2B820 <= code <= 0x2CEAF or  # CJK Extension E
        0x3000 <= code <= 0x303F or  # CJK Symbols and Punctuation
        0xFF00 <= code <= 0xFFEF  # Halfwidth and Fullwidth Forms
    )


def tokenize_for_fts(text: str) -> str:
    """
    Tokenize text for FTS5 indexing by adding spaces around CJK characters.
    This allows unicode61 tokenizer to work with Chinese text.

    Example:
        "链表是空节点" -> "链 表 是 空 节 点"
        "Hello世界" -> "Hello 世 界"
    """
    if not text:
        return text

    result = []
    prev_is_cjk = False

    for char in text:
        curr_is_cjk = is_cjk_char(char)

        # Add space before CJK char if previous was not CJK
        if curr_is_cjk and result and not prev_is_cjk and result[-1] != ' ':
            result.append(' ')

        result.append(char)

        # Add space after CJK char if it's not followed by another CJK
        if curr_is_cjk:
            result.append(' ')

        prev_is_cjk = curr_is_cjk

    # Clean up multiple spaces
    return re.sub(r'\s+', ' ', ''.join(result)).strip()
