"""Shared utilities for normalizers."""

import re
from typing import Optional, TypeVar

_T = TypeVar("_T")


def partial_match(text: str, mappings: dict[str, _T]) -> Optional[_T]:
    """
    Find best partial match using word boundaries, preferring longer matches.

    Args:
        text: Input text to match (should be lowercase)
        mappings: Dictionary of patterns (lowercase) to values

    Returns:
        Matched value or None if no match found
    """
    # Sort by key length (longest first) to prefer more specific matches
    sorted_keys = sorted(mappings.keys(), key=len, reverse=True)

    for key in sorted_keys:
        # Use word boundary regex: \b matches word boundaries
        # This prevents "ia" from matching inside "Cariniana"
        pattern = r"\b" + re.escape(key) + r"\b"
        if re.search(pattern, text):
            return mappings[key]

    return None
