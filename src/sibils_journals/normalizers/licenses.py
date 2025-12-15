"""License name normalization to SPDX identifiers."""

from functools import cache
from typing import Optional

from license_expression import get_spdx_licensing

# Initialize SPDX licensing for license normalization
_spdx_licensing = get_spdx_licensing()

# Common license name mappings to SPDX identifiers
_LICENSE_MAPPINGS = {
    # Creative Commons licenses (with and without version)
    "cc by": "CC-BY-4.0",
    "cc-by": "CC-BY-4.0",
    "cc by 4.0": "CC-BY-4.0",
    "cc by 3.0": "CC-BY-3.0",
    "cc by 2.0": "CC-BY-2.0",
    "cc by 2.5": "CC-BY-2.5",
    "cc by 1.0": "CC-BY-1.0",
    "creative commons attribution": "CC-BY-4.0",
    "creative commons attribution 4.0": "CC-BY-4.0",
    "creative commons attribution 3.0": "CC-BY-3.0",
    "cc by-sa": "CC-BY-SA-4.0",
    "cc-by-sa": "CC-BY-SA-4.0",
    "cc by sa": "CC-BY-SA-4.0",
    "cc by-sa 4.0": "CC-BY-SA-4.0",
    "cc by-sa 3.0": "CC-BY-SA-3.0",
    "creative commons attribution-sharealike": "CC-BY-SA-4.0",
    "creative commons attribution sharealike": "CC-BY-SA-4.0",
    "cc by-nc": "CC-BY-NC-4.0",
    "cc-by-nc": "CC-BY-NC-4.0",
    "cc by nc": "CC-BY-NC-4.0",
    "cc by-nc 4.0": "CC-BY-NC-4.0",
    "cc by-nc 3.0": "CC-BY-NC-4.0",
    "creative commons attribution-noncommercial": "CC-BY-NC-4.0",
    "creative commons attribution noncommercial": "CC-BY-NC-4.0",
    "cc by-nd": "CC-BY-ND-4.0",
    "cc-by-nd": "CC-BY-ND-4.0",
    "cc by nd": "CC-BY-ND-4.0",
    "cc by-nd 4.0": "CC-BY-ND-4.0",
    "cc by-nd 3.0": "CC-BY-ND-3.0",
    "creative commons attribution-noderivatives": "CC-BY-ND-4.0",
    "creative commons attribution noderivatives": "CC-BY-ND-4.0",
    "cc by-nc-sa": "CC-BY-NC-SA-4.0",
    "cc-by-nc-sa": "CC-BY-NC-SA-4.0",
    "cc by nc sa": "CC-BY-NC-SA-4.0",
    "cc by-nc-sa 4.0": "CC-BY-NC-SA-4.0",
    "cc by-nc-sa 3.0": "CC-BY-NC-SA-4.0",
    "creative commons attribution-noncommercial-sharealike": "CC-BY-NC-SA-4.0",
    "cc by-nc-nd": "CC-BY-NC-ND-4.0",
    "cc-by-nc-nd": "CC-BY-NC-ND-4.0",
    "cc by nc nd": "CC-BY-NC-ND-4.0",
    "cc by-nc-nd 4.0": "CC-BY-NC-ND-4.0",
    "cc by-nc-nd 3.0": "CC-BY-NC-ND-3.0",
    "creative commons attribution-noncommercial-noderivatives": "CC-BY-NC-ND-4.0",
    "cc0": "CC0-1.0",
    "cc0 1.0": "CC0-1.0",
    "cc zero": "CC0-1.0",
    "public domain": "CC0-1.0",
    "pd": "CC0-1.0",
    # Other common licenses
    "mit": "MIT",
    "mit license": "MIT",
    "apache": "Apache-2.0",
    "apache 2": "Apache-2.0",
    "apache 2.0": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "gpl": "GPL-3.0-only",
    "gpl 3": "GPL-3.0-only",
    "gpl 3.0": "GPL-3.0-only",
    "gpl v3": "GPL-3.0-only",
    "gplv3": "GPL-3.0-only",
    "gpl 2": "GPL-2.0-only",
    "gpl 2.0": "GPL-2.0-only",
    "gpl v2": "GPL-2.0-only",
    "gplv2": "GPL-2.0-only",
    "lgpl": "LGPL-3.0-only",
    "lgpl 3": "LGPL-3.0-only",
    "lgpl 3.0": "LGPL-3.0-only",
    "bsd": "BSD-3-Clause",
    "bsd 3": "BSD-3-Clause",
    "bsd 3 clause": "BSD-3-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "bsd 2": "BSD-2-Clause",
    "bsd 2 clause": "BSD-2-Clause",
    "bsd-2-clause": "BSD-2-Clause",
    "isc": "ISC",
    "unlicense": "Unlicense",
    "unlicensed": "Unlicense",
}


def normalize_license(license_str: Optional[str]) -> Optional[str]:
    """
    Normalize license name to SPDX identifier.

    Handles:
    - SPDX identifiers: "CC-BY-4.0" -> "CC-BY-4.0"
    - Common names: "CC BY" -> "CC-BY-4.0"
    - Full names: "Creative Commons Attribution" -> "CC-BY-4.0"
    - Case-insensitive matching

    Args:
        license_str: License name or identifier

    Returns:
        SPDX license identifier or original string if not recognized
    """
    if not license_str:
        return None

    license_str = str(license_str).strip()
    if not license_str:
        return None

    # Normalize to lowercase before cached lookup
    return _lookup_license(license_str.lower())


@cache
def _lookup_license(license_str: str) -> Optional[str]:
    """
    Look up SPDX identifier for a license string.

    Args:
        license_str: License name or identifier (lowercase, stripped)

    Returns:
        SPDX license identifier or original string if not recognized
    """
    if not license_str:
        return None

    # Remove common prefixes/suffixes
    license_clean = license_str
    for prefix in ["license:", "licence:", "license", "licence"]:
        if license_clean.startswith(prefix):
            license_clean = license_clean[len(prefix) :].strip()

    # Check manual mappings first (most common case)
    if license_clean in _LICENSE_MAPPINGS:
        return _LICENSE_MAPPINGS[license_clean]

    # Try to parse as SPDX expression
    try:
        parsed = _spdx_licensing.parse(license_str, validate=True)
        if parsed:
            # Return the normalized/canonical form
            return str(parsed)
    except Exception:
        pass

    # Try case-insensitive SPDX lookup
    try:
        # Try to find by key (case-insensitive)
        for lic in _spdx_licensing.known_licenses:
            if lic.key.lower() == license_str or license_str in lic.key.lower():
                return lic.key
    except Exception:
        pass

    # If nothing found, return the original (preserves data)
    return license_str if license_str else None
