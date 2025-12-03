"""Language name normalization to ISO 639-1 codes."""

import re
from functools import cache
from typing import Optional

import pycountry


def normalize_language(language: Optional[str]) -> list[str]:
    """
    Normalize language name(s) to ISO 639-1 two-letter codes.

    Handles:
    - Full names: "English" -> ["en"], "French" -> ["fr"]
    - Multiple languages: "English, French" -> ["en", "fr"]
    - Already valid codes: "en" -> ["en"]
    - Case-insensitive matching
    - Special cases: "Farsi"/"Persian" -> ["fa"]

    Args:
        language: Language name(s), possibly comma/semicolon separated

    Returns:
        List of ISO 639-1 codes, or empty list if not recognized
    """
    if not language:
        return []

    language = str(language).strip()
    if not language:
        return []

    # Split by common delimiters
    parts = re.split(r"[,;|/]", language)
    codes = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Normalize to lowercase before cached lookup
        code = _lookup_language_code(part.lower())
        if code:
            codes.append(code)

    if not codes:
        return []

    # Remove duplicates while preserving order
    seen = set()
    unique_codes = []
    for c in codes:
        if c not in seen:
            seen.add(c)
            unique_codes.append(c)

    return unique_codes


@cache
def _lookup_language_code(lang: str) -> Optional[str]:
    """
    Look up ISO 639-1 code for a single language name.

    Args:
        lang: Language name or code (lowercase, stripped)

    Returns:
        Two-letter ISO 639-1 code or None
    """
    if not lang:
        return None

    # If already a 2-letter code, validate it (not currently used by any source, safety belt)
    if len(lang) == 2:
        try:
            found = pycountry.languages.get(alpha_2=lang)
            if found:
                return found.alpha_2
        except (KeyError, LookupError):
            pass

    # If 3-letter code, convert to 2-letter (not currently used by any source, safety belt)
    if len(lang) == 3:
        try:
            found = pycountry.languages.get(alpha_3=lang)
            if found and hasattr(found, "alpha_2"):
                return found.alpha_2
        except (KeyError, LookupError):
            pass

    # Try case-insensitive name search (DOAJ uses full language names)
    try:
        for language in pycountry.languages:
            if language.name.lower() == lang:
                if hasattr(language, "alpha_2"):
                    return language.alpha_2
    except Exception:
        pass

    # Try fuzzy search using pycountry's search
    try:
        results = pycountry.languages.search_fuzzy(lang)
        if results:
            found = results[0]
            if hasattr(found, "alpha_2"):
                return found.alpha_2
    except (LookupError, Exception):
        pass

    return None
