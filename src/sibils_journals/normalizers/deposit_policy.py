"""Normalization for deposit/self-archiving policies."""

import re
from typing import Optional

# Canonical names for self-archiving policy registries
_DEPOSIT_POLICY_MAPPINGS = {
    # Major registries
    "open policy finder": "Open Policy Finder",
    "sherpa/romeo": "Open Policy Finder",  # Old name
    "sherpa romeo": "Open Policy Finder",
    "sherpa": "Open Policy Finder",
    "romeo": "Open Policy Finder",
    # Regional registries
    "diadorim": "Diadorim",
    "dulcinea": "Dulcinea",
    "mir@bel": "Mir@bel",
    "mirabel": "Mir@bel",
    "malena": "Malena",
    "most wiedzy": "Most Wiedzy",
    "aura": "Aura",
    "edinburgh diamond": "Edinburgh Diamond",
    # Country-specific
    "scindeks": "SCIndeks",
    "scindeks - the serbian citation index": "SCIndeks",
    "iran national library and archives": "Iran National Library and Archives",
    "vjol": "VJOL",
    "vcgate": "VCgate",
    # Indonesian
    "garuda": "Garuda",
    "portal garuda": "Garuda",
    "garba rujukan digital": "Garuda",
    # Turkish
    "dergipark": "DergiPark",
    "dergi park": "DergiPark",
    # Preprint servers
    "arxiv": "arXiv",
    # Latin American
    "scielo": "SciELO",
    # Generic descriptions (consolidate variations)
    "publisher's site": "Publisher's website",
    "publisher's own site": "Publisher's website",
    "publisher's own website": "Publisher's website",
    "publisher site": "Publisher's website",
    "publisher website": "Publisher's website",
    "publishers site": "Publisher's website",
    "pulisher's own site": "Publisher's website",  # typo in data
    "publisher own site": "Publisher's website",
    "journal website": "Journal website",
    "journal's website": "Journal website",
    "journal's own website": "Journal website",
    "journal's own site": "Journal website",
    "journal site": "Journal website",
    "journals website": "Journal website",
    "the journal website": "Journal website",
    "journal's site": "Journal website",
    "journal own website": "Journal website",
    "copyright notice": "Copyright notice",
    "copyright": "Copyright notice",
    "preprint and postprint policy": "Preprint and postprint policy",
    "self-archiving policy": "Self-archiving policy",
    "author self-archiving": "Self-archiving policy",
    "archiving": "Archiving policy",
}

# Cache for deposit policy lookups
_deposit_policy_cache: dict[str, str] = {}


def normalize_deposit_policy(policy: Optional[str]) -> list[str]:
    """
    Normalize deposit policy/registry name(s) to canonical forms.

    Handles:
    - Registry names: "open policy finder" -> "Open Policy Finder"
    - Generic descriptions: "Publisher's site" -> "Publisher's website"
    - Multiple values: "Dulcinea, Open Policy Finder" -> ["Dulcinea", "Open Policy Finder"]
    - Case variations and typos
    - Unrecognized values are filtered out

    Args:
        policy: Deposit policy description, possibly comma/semicolon separated

    Returns:
        List of normalized policy names (only canonical forms), empty list if no matches
    """
    if not policy:
        return []

    policy = str(policy).strip()
    if not policy:
        return []

    # Split by comma or semicolon to handle multiple registries
    parts = re.split(r"[,;]", policy)
    normalized = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Check cache first
        cache_key = part.lower()
        if cache_key in _deposit_policy_cache:
            result = _deposit_policy_cache[cache_key]
        else:
            result = _lookup_deposit_policy(part)
            _deposit_policy_cache[cache_key] = result

        if result:
            normalized.append(result)

    return normalized


def _normalize_apostrophes(text: str) -> str:
    """Normalize Unicode apostrophes to ASCII."""
    # Replace common Unicode apostrophe variants with ASCII
    # U+2019 = RIGHT SINGLE QUOTATION MARK (')
    # U+2018 = LEFT SINGLE QUOTATION MARK (')
    # U+0060 = GRAVE ACCENT (`)
    return text.replace("\u2019", "'").replace("\u2018", "'").replace("\u0060", "'")


def _lookup_deposit_policy(policy: str) -> Optional[str]:
    """
    Look up canonical name for a deposit policy registry.

    Args:
        policy: Deposit policy/registry name

    Returns:
        Canonical name or None if not recognized
    """
    # Normalize Unicode apostrophes before lookup
    policy_lower = _normalize_apostrophes(policy.lower().strip())

    # Check exact mapping
    if policy_lower in _DEPOSIT_POLICY_MAPPINGS:
        return _DEPOSIT_POLICY_MAPPINGS[policy_lower]

    # Check for partial matches (for longer descriptions)
    for key, canonical in _DEPOSIT_POLICY_MAPPINGS.items():
        if key in policy_lower or policy_lower in key:
            return canonical

    # If not recognized, return None to enable faceted search on canonical values
    return None
