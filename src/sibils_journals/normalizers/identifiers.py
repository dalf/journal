"""ISSN validation and normalization."""

import logging
from typing import Optional

import pandas as pd

from .. import config
from ..metrics import get_metrics
from ..models import ISBN_ID_PATTERN, ISSN_PATTERN, NLM_ID_PATTERN, OPENALEX_ID_PATTERN, TITLE_ID_PATTERN

logger = logging.getLogger(__name__)


def is_valid_identifier(identifier: str) -> bool:
    """
    Check if identifier is a valid ISSN or synthetic ID.

    Valid formats:
    - ISSN: NNNN-NNNX (where X is digit or 'X')
    - NLM synthetic: NLM-{numeric_id}
    - ISBN synthetic: ISBN-{isbn13}
    - OpenAlex synthetic: OPENALEX-S{numeric_id}
    - Title synthetic: TITLE-{hash}

    Args:
        identifier: The identifier to validate

    Returns:
        True if valid ISSN or synthetic ID, False otherwise
    """
    if not identifier:
        return False
    return bool(
        ISSN_PATTERN.match(identifier)
        or NLM_ID_PATTERN.match(identifier)
        or ISBN_ID_PATTERN.match(identifier)
        or OPENALEX_ID_PATTERN.match(identifier)
        or TITLE_ID_PATTERN.match(identifier)
    )


def validate_issn_checksum(issn: str) -> bool:
    """
    Validate ISSN check digit (last character).

    The check digit is calculated as:
    (11 - (sum of (digit * weight) mod 11)) mod 11
    where weights are 8,7,6,5,4,3,2 for positions 1-7
    and 10 is represented as 'X'.
    """
    # Remove hyphen for calculation
    digits = issn.replace("-", "")
    if len(digits) != 8:
        return False

    # Calculate checksum
    weights = [8, 7, 6, 5, 4, 3, 2]
    total = 0

    for i, weight in enumerate(weights):
        if not digits[i].isdigit():
            return False
        total += int(digits[i]) * weight

    remainder = total % 11
    check = (11 - remainder) % 11

    # Validate check digit
    last_char = digits[7].upper()
    if check == 10:
        return last_char == "X"
    return last_char == str(check)


def normalize_issn(issn: Optional[str], validate_checksum: bool = True, track_metrics: bool = True) -> Optional[str]:
    """
    Normalize ISSN to standard format (NNNN-NNNN).

    Args:
        issn: Raw ISSN string
        validate_checksum: If True, validate the check digit (unless SKIP_CHECKSUM_VALIDATION is set)
        track_metrics: If True, record validation metrics

    Returns:
        Normalized ISSN or None if invalid
    """
    if not issn:
        return None

    # Remove whitespace and convert to uppercase
    issn = str(issn).strip().upper()

    # Handle ISSNs without hyphen
    if len(issn) == 8 and "-" not in issn:
        issn = f"{issn[:4]}-{issn[4:]}"

    # Validate format
    if not ISSN_PATTERN.match(issn):
        if track_metrics:
            get_metrics().record_issn_validation(valid=False, invalid_format=True, issn_value=issn)
        return None

    # Validate checksum if requested (and not globally disabled)
    if validate_checksum and not config.SKIP_CHECKSUM_VALIDATION and not validate_issn_checksum(issn):
        logger.debug(f"Invalid ISSN checksum: {issn}")
        if track_metrics:
            get_metrics().record_issn_validation(valid=False, invalid_checksum=True, issn_value=issn)
        return None

    if track_metrics:
        get_metrics().record_issn_validation(valid=True)
    return issn


def normalize_issn_series(series: pd.Series) -> pd.Series:
    """
    Normalize a pandas Series of ISSNs using vectorized operations.

    Args:
        series: Pandas Series containing ISSN strings

    Returns:
        Series with normalized ISSNs (None for invalid)
    """
    # Handle NaN and convert to string
    result = series.fillna("").astype(str).str.strip().str.upper()
    # Add hyphen if missing (8 chars without hyphen)
    mask_no_hyphen = (result.str.len() == 8) & (~result.str.contains("-", regex=False))
    result = result.where(~mask_no_hyphen, result.str[:4] + "-" + result.str[4:])
    # Validate format
    valid_mask = result.str.match(r"^\d{4}-\d{3}[\dX]$")
    result = result.where(valid_mask, "")
    # Replace empty strings with None
    return result.replace("", None)
