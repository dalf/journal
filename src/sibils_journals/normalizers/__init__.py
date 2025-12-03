"""Normalization functions for journal data."""

from .deposit_policy import normalize_deposit_policy
from .geography import normalize_country
from .identifiers import is_valid_identifier, normalize_issn, normalize_issn_series, validate_issn_checksum
from .languages import normalize_language
from .licenses import normalize_license
from .preservation import normalize_preservation_service
from .review_process import normalize_review_process
from .subjects import map_lcc_to_domain, map_lcc_to_field
from .text import normalize_publisher, normalize_text_series, normalize_title, remove_control_chars

__all__ = [
    # Identifiers
    "is_valid_identifier",
    "validate_issn_checksum",
    "normalize_issn",
    "normalize_issn_series",
    # Text
    "remove_control_chars",
    "normalize_title",
    "normalize_publisher",
    "normalize_text_series",
    # Geography
    "normalize_country",
    # Languages
    "normalize_language",
    # Licenses
    "normalize_license",
    # Policies
    "normalize_review_process",
    "normalize_preservation_service",
    "normalize_deposit_policy",
    # Subjects
    "map_lcc_to_domain",
    "map_lcc_to_field",
]
