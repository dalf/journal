"""DOAJ (Directory of Open Access Journals) CSV data loader."""

import logging
import re
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from ..models import DataSource, JournalDict
from ..normalizers import (
    map_lcc_to_domain,
    map_lcc_to_field,
    normalize_country,
    normalize_deposit_policy,
    normalize_issn_series,
    normalize_language,
    normalize_license,
    normalize_preservation_service,
    normalize_publisher,
    normalize_review_process,
    normalize_title,
)
from .utils import deduplicate_journals, find_column, normalize_subjects

logger = logging.getLogger(__name__)


# --- Normalizer helpers ---


def _normalize_bool(val) -> Optional[bool]:
    """Convert yes/no/true/false to boolean."""
    if pd.isna(val):
        return None
    return str(val).strip().lower() in ("yes", "true", "y", "1")


def _normalize_currency(val) -> Optional[str]:
    """Normalize currency code to uppercase."""
    if pd.isna(val) or not str(val).strip():
        return None
    return str(val).strip().upper()


def _normalize_review_processes(val) -> Optional[list[str]]:
    """Split comma-separated review processes and normalize each."""
    if pd.isna(val) or not val:
        return None
    parts = [p.strip() for p in str(val).split(",")]
    normalized = []
    for part in parts:
        if part:
            norm = normalize_review_process(part)
            if norm and norm not in normalized:
                normalized.append(norm)
    return normalized if normalized else None


def _strip(val) -> Optional[str]:
    """Strip whitespace, return None if empty."""
    if pd.isna(val) or not str(val).strip():
        return None
    return str(val).strip()


def _wrap_list(normalizer: Callable) -> Callable:
    """Wrap a normalizer to return a single-item list."""

    def wrapper(val) -> Optional[list]:
        if pd.isna(val) or not val:
            return None
        result = normalizer(val)
        return [result] if result else None

    return wrapper


def _extract_subject_domain(val) -> Optional[str]:
    """Extract domain from first LCC subject."""
    if pd.isna(val) or not val:
        return None
    subj_list = re.split(r"[,|;]", str(val))
    if not subj_list:
        return None
    first = subj_list[0].strip()
    parts = first.split(":")
    lcc_category = parts[0].strip()
    lcc_subcategory = parts[1].strip() if len(parts) > 1 else None
    return map_lcc_to_domain(lcc_category, lcc_subcategory)


def _extract_subject_field(val) -> Optional[str]:
    """Extract field from first LCC subject."""
    if pd.isna(val) or not val:
        return None
    subj_list = re.split(r"[,|;]", str(val))
    if not subj_list:
        return None
    first = subj_list[0].strip()
    parts = first.split(":")
    lcc_category = parts[0].strip()
    lcc_subcategory = parts[1].strip() if len(parts) > 1 else None
    return map_lcc_to_field(lcc_category, lcc_subcategory)


def _extract_subject_subfield(val) -> Optional[str]:
    """Extract subfield (subcategory) from first LCC subject."""
    if pd.isna(val) or not val:
        return None
    subj_list = re.split(r"[,|;]", str(val))
    if not subj_list:
        return None
    first = subj_list[0].strip()
    parts = first.split(":")
    return parts[1].strip() if len(parts) > 1 else None


def _normalize_preservation_services(val) -> Optional[list[str]]:
    """Split and normalize preservation services."""
    if pd.isna(val) or not val:
        return None
    services = re.split(r"[,;]", str(val))
    normalized = [normalize_preservation_service(s) for s in services]
    result = [s for s in normalized if s]
    return result if result else None


def _normalize_deposit_policy_field(val) -> Optional[list[str]]:
    """Normalize deposit policy (returns list)."""
    if pd.isna(val) or not val:
        return None
    result = normalize_deposit_policy(str(val))
    return result if result else None


# --- Field mapping: JournalDict field → (raw column candidates, normalizer) ---

_DOAJ_FIELDS: dict[str, tuple[list[str], Optional[Callable]]] = {
    # Core fields
    "title": (["Journal title", "Title"], normalize_title),
    "issn_print": (
        ["Journal ISSN (print version)", "ISSN (print)", "Print ISSN"],
        None,  # ISSN normalization handled specially
    ),
    "issn_electronic": (
        ["Journal EISSN (online version)", "EISSN (online)", "Online ISSN", "E-ISSN"],
        None,  # ISSN normalization handled specially
    ),
    "publisher": (["Publisher", "Publisher name"], normalize_publisher),
    "country": (["Country of publisher", "Country"], normalize_country),
    "language": (
        ["Languages in which the journal accepts manuscripts", "Language", "Languages"],
        normalize_language,
    ),
    "license": (["Journal license", "License"], normalize_license),
    "review_process": (["Review process", "Peer review"], _normalize_review_processes),
    # Boolean fields
    "copyright_author": (
        ["Author holds copyright without restrictions"],
        _normalize_bool,
    ),
    "plagiarism_screening": (
        ["Journal plagiarism screening policy"],
        _normalize_bool,
    ),
    # APC fields
    "apc_amount": (["APC amount", "APC Amount"], None),  # numeric, handled specially
    "apc_currency": (["APC currency", "APC Currency"], _normalize_currency),
    # URL fields
    "journal_url": (["Journal URL", "URL"], _strip),
    "license_url": (["URL for license terms"], _strip),
    "review_process_url": (["Review process information URL"], _strip),
    "copyright_url": (["Copyright information URL"], _strip),
    # List fields
    "alternative_titles": (
        ["Alternative title", "Alternative Title"],
        _wrap_list(normalize_title),
    ),
    "other_organisations": (
        ["Other organisation", "Other organization", "Other Organisation"],
        _wrap_list(normalize_publisher),
    ),
    "subjects": (["Subjects", "Keywords", "Subject"], normalize_subjects),
    "subject_domain": (["Subjects", "Keywords", "Subject"], _extract_subject_domain),
    "subject_field": (["Subjects", "Keywords", "Subject"], _extract_subject_field),
    "subject_subfield": (
        ["Subjects", "Keywords", "Subject"],
        _extract_subject_subfield,
    ),
    "preservation_services": (
        ["Preservation Services"],
        _normalize_preservation_services,
    ),
    "deposit_policy": (["Deposit policy directory"], _normalize_deposit_policy_field),
}


def normalize_doaj_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize a raw DOAJ DataFrame.

    Applies column mapping, ISSN validation, and all normalizations.
    Output DataFrame uses JournalDict field names directly.

    Args:
        df: Raw DataFrame from CSV read

    Returns:
        Normalized DataFrame with valid ISSNs only, columns named per JournalDict
    """
    # Normalize column names for easier matching
    df.columns = df.columns.str.strip()
    col_list = df.columns.tolist()

    # Get raw ISSN columns
    issn_print_col = find_column(col_list, _DOAJ_FIELDS["issn_print"][0])
    issn_electronic_col = find_column(col_list, _DOAJ_FIELDS["issn_electronic"][0])

    # Compute normalized ISSNs (without modifying input df)
    issn_print = normalize_issn_series(df[issn_print_col]) if issn_print_col else pd.Series([None] * len(df), index=df.index)
    issn_electronic = normalize_issn_series(df[issn_electronic_col]) if issn_electronic_col else pd.Series([None] * len(df), index=df.index)

    # Filter rows with at least one valid ISSN
    has_issn = issn_print.notna() | issn_electronic.notna()
    df_valid = df[has_issn].copy()

    # Add normalized ISSNs with JournalDict field names
    df_valid["issn_print"] = issn_print[has_issn].values
    df_valid["issn_electronic"] = issn_electronic[has_issn].values

    # Apply normalizers for each field
    for field, (candidates, normalizer) in _DOAJ_FIELDS.items():
        if field in ("issn_print", "issn_electronic"):
            continue  # Already handled above

        raw_col = find_column(col_list, candidates)
        if not raw_col:
            df_valid[field] = None
            continue

        if normalizer:
            # Apply normalizer function
            df_valid[field] = df_valid[raw_col].apply(normalizer)
        elif field == "apc_amount":
            # Numeric field
            df_valid[field] = pd.to_numeric(df_valid[raw_col], errors="coerce")
        else:
            # Copy raw value
            df_valid[field] = df_valid[raw_col]

    return df_valid


# Fields to copy directly from row to JournalDict
_DOAJ_DIRECT_FIELDS = [
    "issn_print",
    "issn_electronic",
    "title",
    "publisher",
    "country",
    "language",
    "license",
    "review_process",
    "copyright_author",
    "plagiarism_screening",
    "apc_amount",
    "apc_currency",
    "journal_url",
    "license_url",
    "review_process_url",
    "copyright_url",
    "alternative_titles",
    "other_organisations",
    "subjects",
    "subject_domain",
    "subject_field",
    "subject_subfield",
    "preservation_services",
    "deposit_policy",
]


def process_doaj_record(row: dict) -> JournalDict:
    """
    Transform a normalized DOAJ row dict into a JournalDict.

    Args:
        row: Dictionary with JournalDict field names (from normalize_doaj_dataframe)

    Returns:
        JournalDict with source metadata
    """
    journal: JournalDict = {
        "source": DataSource.DOAJ,
        "is_oa": True,
        "source_type": "journal",
    }

    # Copy all prepared fields
    for field in _DOAJ_DIRECT_FIELDS:
        val = row.get(field)
        if val is not None and not (isinstance(val, float) and pd.isna(val)):
            journal[field] = val

    return journal


def load_doaj_data(input_dir: Path) -> list[JournalDict]:
    """
    Load DOAJ (Directory of Open Access Journals) CSV data.

    See: https://doaj.org/docs/public-data-dump/
    License: CC0 (journal and article metadata)
    """
    journals = []
    csv_path = input_dir / "doaj" / "journals.csv"

    if not csv_path.exists():
        logger.warning(f"DOAJ data not found at {csv_path}, skipping...")
        return journals

    logger.info(f"Loading DOAJ data from: {csv_path}")

    try:
        # Read CSV with pandas (I/O only)
        df = pd.read_csv(
            csv_path,
            dtype=str,
            on_bad_lines="skip",
            low_memory=False,
        )

        logger.info(f"  Read {len(df):,} rows from CSV")

        # Normalize DataFrame (all transformations)
        df_valid = normalize_doaj_dataframe(df)

        logger.info(f"  {len(df_valid):,} rows have valid ISSNs")

        # Build journal records
        journals = [process_doaj_record(row) for row in df_valid.to_dict("records")]

        logger.info(f"Loaded {len(journals):,} journals from DOAJ")

    except Exception as e:
        logger.error(f"Error loading DOAJ data: {e}")
        import traceback

        logger.debug(traceback.format_exc())

    # Deduplicate within source
    journals = deduplicate_journals(journals, "DOAJ")
    return journals
