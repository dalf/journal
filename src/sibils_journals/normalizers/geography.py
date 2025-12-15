"""Country name normalization to ISO 3166-1 alpha-2 codes."""

from functools import cache
from typing import Optional

import pycountry


def normalize_country(country: Optional[str]) -> Optional[str]:
    """
    Normalize country name to ISO 3166-1 alpha-2 code.

    Handles:
    - ISO 2-letter codes: "US", "us", "Us" -> "US"
    - ISO 3-letter codes: "USA", "usa" -> "US"
    - Full names: "United States", "France" -> "US", "FR"
    - Official names: "Russian Federation" -> "RU"
    - Fuzzy matching via pycountry

    Args:
        country: Country name or code

    Returns:
        ISO 3166-1 alpha-2 code (uppercase) or None if not recognized
    """
    if not country:
        return None

    country = str(country).strip()
    if not country:
        return None

    # Normalize to lowercase before cached lookup
    return _lookup_country_code(country.lower())


@cache
def _lookup_country_code(country: str) -> Optional[str]:
    """
    Look up ISO 3166-1 alpha-2 code for a country.

    Args:
        country: Country name or code (lowercase, stripped)

    Returns:
        Two-letter ISO 3166-1 alpha-2 code or None
    """
    if not country:
        return None

    # If already a 2-letter code, validate it (OpenAlex uses alpha-2)
    if len(country) == 2:
        try:
            found = pycountry.countries.get(alpha_2=country.upper())
            if found:
                return found.alpha_2
        except (KeyError, LookupError):
            pass

    # If 3-letter code, convert to 2-letter (not currently used by any source, safety belt)
    if len(country) == 3:
        try:
            found = pycountry.countries.get(alpha_3=country.upper())
            if found:
                return found.alpha_2
        except (KeyError, LookupError):
            pass

    # Case-insensitive search through all countries (DOAJ uses full country names)
    try:
        for c in pycountry.countries:
            if c.name.lower() == country:
                return c.alpha_2
            if hasattr(c, "official_name") and c.official_name.lower() == country:
                return c.alpha_2
            if hasattr(c, "common_name") and c.common_name.lower() == country:
                return c.alpha_2
    except Exception:
        pass

    # Try fuzzy search
    try:
        results = pycountry.countries.search_fuzzy(country)
        if results:
            return results[0].alpha_2
    except (LookupError, Exception):
        pass

    return None
