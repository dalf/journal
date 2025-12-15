"""Text normalization functions (titles, publishers, control characters)."""

from typing import Optional

import pandas as pd

# Pre-build translation table for performance (module-level constant)
_CONTROL_CHAR_MAP = {}

# C0 controls (0x00-0x1F) - replace with space
for _i in range(0x00, 0x20):
    _CONTROL_CHAR_MAP[_i] = " "

# C1 controls (0x80-0x9F) - replace with space
for _i in range(0x80, 0xA0):
    _CONTROL_CHAR_MAP[_i] = " "

# Zero-width chars - remove entirely
for _i in (0x200B, 0x200C, 0x200D, 0xFEFF, 0xFFFD):
    _CONTROL_CHAR_MAP[_i] = None

_CONTROL_CHAR_TABLE = str.maketrans(_CONTROL_CHAR_MAP)

# Unicode normalization table (typography variants -> ASCII)
_UNICODE_NORM_MAP = {
    # Single quotes / apostrophes -> ASCII apostrophe
    0x2019: "'",  # RIGHT SINGLE QUOTATION MARK (')
    0x2018: "'",  # LEFT SINGLE QUOTATION MARK (')
    0x0060: "'",  # GRAVE ACCENT (`)
    0x00B4: "'",  # ACUTE ACCENT (´)
    0x2032: "'",  # PRIME (′)
    # Double quotes -> ASCII double quote
    0x201C: '"',  # LEFT DOUBLE QUOTATION MARK (")
    0x201D: '"',  # RIGHT DOUBLE QUOTATION MARK (")
    0x201E: '"',  # DOUBLE LOW-9 QUOTATION MARK („)
    # Dashes -> ASCII hyphen
    0x2013: "-",  # EN DASH (–)
    # Spaces -> ASCII space
    0x00A0: " ",  # NO-BREAK SPACE
    # Remove entirely
    0x00AD: None,  # SOFT HYPHEN (invisible)
}
_UNICODE_NORM_TABLE = str.maketrans(_UNICODE_NORM_MAP)


def normalize_unicode_punctuation(text: str) -> str:
    """Normalize Unicode punctuation variants to ASCII equivalents."""
    if not text:
        return text
    return text.translate(_UNICODE_NORM_TABLE)


# Keep old name as alias for backwards compatibility
normalize_apostrophes = normalize_unicode_punctuation


def remove_control_chars(text: str) -> str:
    """
    Remove ALL control characters from text, replacing with spaces.

    Replaces with space:
    - C0 control chars (U+0000-U+001F) including tab, newline, carriage return
    - C1 control chars (U+0080-U+009F)

    Removes entirely:
    - Zero-width chars (U+200B, U+200C, U+200D, U+FEFF)
    - Replacement character (U+FFFD)
    """
    if not text:
        return text

    return text.translate(_CONTROL_CHAR_TABLE)


def normalize_title(title: Optional[str]) -> Optional[str]:
    """Normalize journal title."""
    if not title:
        return None
    title = str(title).strip()
    # Remove wrapping quotes (CSV artifacts)
    if title.startswith('"') and title.endswith('"'):
        title = title[1:-1].strip()
    # Remove control characters
    title = remove_control_chars(title)
    # Normalize apostrophes
    title = normalize_apostrophes(title)
    # Remove excessive whitespace
    title = " ".join(title.split())
    return title if title else None


def normalize_publisher(publisher: Optional[str]) -> Optional[str]:
    """Normalize publisher name."""
    if not publisher:
        return None
    publisher = str(publisher).strip()
    # Remove wrapping quotes (CSV artifacts)
    if publisher.startswith('"') and publisher.endswith('"'):
        publisher = publisher[1:-1].strip()
    # Remove control characters
    publisher = remove_control_chars(publisher)
    # Normalize apostrophes
    publisher = normalize_apostrophes(publisher)
    # Remove excessive whitespace
    publisher = " ".join(publisher.split())
    return publisher if publisher else None


def normalize_text_series(series: pd.Series) -> pd.Series:
    """
    Normalize a pandas Series of text (titles, publishers) using vectorized operations.

    Args:
        series: Pandas Series containing text strings

    Returns:
        Series with normalized text (None for empty)
    """
    # Handle NaN and convert to string, strip whitespace
    result = series.fillna("").astype(str).str.strip()
    # Replace ALL C0 and C1 control chars with space (including tab/newline/cr)
    result = result.str.replace(r"[\x00-\x1f\x80-\x9f]", " ", regex=True)
    # Remove zero-width chars and replacement char
    result = result.str.replace(r"[\u200b\u200c\u200d\ufeff\ufffd]", "", regex=True)
    # Normalize Unicode punctuation to ASCII
    result = result.str.replace(r"[\u2018\u2019\u0060\u00b4\u2032]", "'", regex=True)  # apostrophes
    result = result.str.replace(r"[\u201c\u201d\u201e]", '"', regex=True)  # double quotes
    result = result.str.replace(r"\u2013", "-", regex=True)  # en dash
    result = result.str.replace(r"\u00a0", " ", regex=True)  # no-break space
    result = result.str.replace(r"\u00ad", "", regex=True)  # soft hyphen (remove)
    # Collapse multiple whitespace to single space
    result = result.str.replace(r"\s+", " ", regex=True)
    # Strip again after replacements
    result = result.str.strip()
    # Replace empty strings with None
    return result.replace("", None)
