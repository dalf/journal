"""Utility functions for loaders."""

import logging
import re
from typing import Optional

import pandas as pd

from ..metrics import get_metrics
from ..models import JournalDict
from ..normalizers import is_valid_identifier

logger = logging.getLogger(__name__)


def find_column(col_list: list[str], candidates: list[str]) -> Optional[str]:
    """
    Find the first matching column name from candidates.

    Args:
        col_list: List of available column names
        candidates: List of candidate column names to search for

    Returns:
        First matching column name, or None if no match
    """
    for col in candidates:
        if col in col_list:
            return col
    return None


def normalize_subjects(val) -> Optional[list[str]]:
    """
    Split subjects by comma, pipe, or semicolon.

    Args:
        val: Raw subject string (may be comma/pipe/semicolon separated)

    Returns:
        List of subject strings, or None if empty
    """
    if pd.isna(val) or not val:
        return None
    subj_list = re.split(r"[,;|]", str(val))
    subjects = [s.strip() for s in subj_list if s.strip()]
    return subjects if subjects else None


def deduplicate_journals(journals: list[JournalDict], source_name: str) -> list[JournalDict]:
    """
    Remove duplicate journals within a single source.

    Deduplication strategy:
    1. Use ISSN-L as primary key (if available)
    2. Fall back to print ISSN, then electronic ISSN
    3. For journals without ISSN, use source-specific ID (nlm_id, openalex_id)
    4. When duplicates found, merge records (prefer non-null values)
    5. Log statistics about duplicates removed

    Args:
        journals: List of journal dicts from a single source
        source_name: Name of the source for logging (e.g., "DOAJ", "Crossref")

    Returns:
        Deduplicated list of journal dicts
    """
    if not journals:
        return journals

    original_count = len(journals)
    seen: dict[str, dict] = {}

    for journal in journals:
        # Determine deduplication key (prefer ISSN-L, fall back to other ISSNs)
        key = journal.get("issn_l") or journal.get("issn_print") or journal.get("issn_electronic")

        # For journals without ISSN, use source-specific identifiers
        if not key:
            nlm_id = journal.get("nlm_id")
            openalex_id = journal.get("openalex_id")

            if nlm_id:
                key = f"NLM:{nlm_id}"
            elif openalex_id:
                key = f"OPENALEX:{openalex_id}"
            else:
                # No identifier at all - skip this record
                logger.debug(f"Skipping journal with no identifier: {journal.get('title', 'Unknown')}")
                continue

        # Validate ISSN keys (skip validation for source-specific keys)
        if not key.startswith(("NLM:", "OPENALEX:")) and not is_valid_identifier(key):
            # Invalid identifier format - skip this record
            logger.debug(f"Skipping journal with invalid identifier '{key}': {journal.get('title', 'Unknown')}")
            continue

        if key not in seen:
            # First occurrence - store it
            seen[key] = journal
        else:
            # Duplicate found - merge non-null values
            existing = seen[key]
            for field, value in journal.items():
                if value is not None and existing.get(field) is None:
                    existing[field] = value

    deduplicated = list(seen.values())
    duplicates_removed = original_count - len(deduplicated)

    if duplicates_removed > 0:
        logger.info(f"  Removed {duplicates_removed:,} duplicate(s) from {source_name} ({original_count:,} → {len(deduplicated):,} journals)")
        # Track in metrics
        get_metrics().record_duplicate_removed(source_name, duplicates_removed)

    return deduplicated
