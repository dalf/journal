"""Normalization for peer review process types."""

from typing import Optional

from ..models import ReviewProcess
from .utils import partial_match

# Controlled vocabulary for peer review process types
_REVIEW_PROCESS_MAPPINGS: dict[str, ReviewProcess] = {
    # Double-blind
    "double blind": ReviewProcess.DOUBLE_BLIND,
    "double-blind": ReviewProcess.DOUBLE_BLIND,
    "double blind peer review": ReviewProcess.DOUBLE_BLIND,
    "double-blind peer review": ReviewProcess.DOUBLE_BLIND,
    "double anonymous": ReviewProcess.DOUBLE_BLIND,
    "double-anonymous": ReviewProcess.DOUBLE_BLIND,
    "double anonymised": ReviewProcess.DOUBLE_BLIND,
    "double anonymized": ReviewProcess.DOUBLE_BLIND,
    "blind peer review": ReviewProcess.DOUBLE_BLIND,
    # Single-blind
    "single blind": ReviewProcess.SINGLE_BLIND,
    "single-blind": ReviewProcess.SINGLE_BLIND,
    "single blind peer review": ReviewProcess.SINGLE_BLIND,
    "single-blind peer review": ReviewProcess.SINGLE_BLIND,
    "single anonymous": ReviewProcess.SINGLE_BLIND,
    "single-anonymous": ReviewProcess.SINGLE_BLIND,
    "blind": ReviewProcess.SINGLE_BLIND,
    "anonymous": ReviewProcess.SINGLE_BLIND,
    "anonymised": ReviewProcess.SINGLE_BLIND,
    "anonymized": ReviewProcess.SINGLE_BLIND,
    # Open peer review
    "open": ReviewProcess.OPEN,
    "open peer review": ReviewProcess.OPEN,
    "open review": ReviewProcess.OPEN,
    "transparent": ReviewProcess.OPEN,
    "transparent peer review": ReviewProcess.OPEN,
    "non-anonymous": ReviewProcess.OPEN,
    "non-blind": ReviewProcess.OPEN,
    # Editorial review
    "editorial": ReviewProcess.EDITORIAL,
    "editorial review": ReviewProcess.EDITORIAL,
    "editorial board": ReviewProcess.EDITORIAL,
    "editorial board review": ReviewProcess.EDITORIAL,
    "editor review": ReviewProcess.EDITORIAL,
    "editor": ReviewProcess.EDITORIAL,
    # Post-publication
    "post-publication": ReviewProcess.POST_PUBLICATION,
    "post publication": ReviewProcess.POST_PUBLICATION,
    "post-publication review": ReviewProcess.POST_PUBLICATION,
    "post publication review": ReviewProcess.POST_PUBLICATION,
    "post-publication peer review": ReviewProcess.POST_PUBLICATION,
    # Triple-blind (author, reviewer, AND editor identities hidden)
    "triple-blind": ReviewProcess.TRIPLE_BLIND,
    "triple blind": ReviewProcess.TRIPLE_BLIND,
    "triple-anonymous": ReviewProcess.TRIPLE_BLIND,
    "triple anonymous": ReviewProcess.TRIPLE_BLIND,
    "triple-anonymous peer review": ReviewProcess.TRIPLE_BLIND,
    "triple anonymous peer review": ReviewProcess.TRIPLE_BLIND,
    # Committee review
    "committee": ReviewProcess.COMMITTEE,
    "committee review": ReviewProcess.COMMITTEE,
    "committee peer review": ReviewProcess.COMMITTEE,
    # No peer review
    "none": ReviewProcess.NONE,
    "no peer review": ReviewProcess.NONE,
    "not peer reviewed": ReviewProcess.NONE,
    "no review": ReviewProcess.NONE,
    # Other types
    "peer review": ReviewProcess.PEER_REVIEW,
    "peer reviewed": ReviewProcess.PEER_REVIEW,
    "peer-reviewed": ReviewProcess.PEER_REVIEW,
}

# Cache for review process lookups
_review_process_cache: dict[str, Optional[ReviewProcess]] = {}


def normalize_review_process(review_process: Optional[str]) -> Optional[ReviewProcess]:
    """
    Normalize peer review process type to ReviewProcess enum.

    Handles:
    - Common variations: "Double Blind" -> ReviewProcess.DOUBLE_BLIND
    - Multiple terms: case-insensitive matching
    - Unknown values: returns None (only mapped values are returned)

    Args:
        review_process: Review process description

    Returns:
        ReviewProcess enum value or None if not recognized
    """
    if not review_process:
        return None

    review_process = str(review_process).strip()
    if not review_process:
        return None

    # Check cache first
    cache_key = review_process.lower()
    if cache_key in _review_process_cache:
        return _review_process_cache[cache_key]

    result = _lookup_review_process(review_process)
    _review_process_cache[cache_key] = result
    return result


def _lookup_review_process(review_process: str) -> Optional[ReviewProcess]:
    """
    Look up normalized review process type.

    Args:
        review_process: Review process description

    Returns:
        ReviewProcess enum value or None if not recognized
    """
    rp_lower = review_process.lower().strip()

    # Remove common prefixes/suffixes
    rp_clean = rp_lower
    for suffix in [" review process", " process"]:
        if rp_clean.endswith(suffix):
            rp_clean = rp_clean[: -len(suffix)].strip()

    # Check exact mappings
    if rp_clean in _REVIEW_PROCESS_MAPPINGS:
        return _REVIEW_PROCESS_MAPPINGS[rp_clean]

    # Check if original (before cleaning) matches
    if rp_lower in _REVIEW_PROCESS_MAPPINGS:
        return _REVIEW_PROCESS_MAPPINGS[rp_lower]

    # Check for partial matches using word boundaries, preferring longer matches
    return partial_match(rp_lower, _REVIEW_PROCESS_MAPPINGS)
