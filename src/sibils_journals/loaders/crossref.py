"""Crossref title list loader."""

import logging
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from ..models import DataSource, JournalDict
from ..normalizers import normalize_issn_series, normalize_language, normalize_text_series
from .utils import deduplicate_journals, find_column, normalize_subjects

logger = logging.getLogger(__name__)


# --- Normalizer helpers ---


def _normalize_type(val) -> Optional[str]:
    """Normalize source type to lowercase."""
    if pd.isna(val) or not str(val).strip():
        return None
    return str(val).strip().lower()


# --- Field mapping: JournalDict field → (raw column candidates, normalizer) ---
# Column names are lowercase (Crossref CSV headers are normalized to lowercase)

_CROSSREF_FIELDS: dict[str, tuple[list[str], Optional[Callable]]] = {
    "title": (
        ["journaltitle", "title", "journal title", "publication name"],
        None,
    ),  # uses normalize_text_series
    "publisher": (["publisher", "publisher name"], None),  # uses normalize_text_series
    "issn_print": (
        ["print issn", "print issn/isbn", "pissn", "p-issn"],
        None,  # ISSN normalization handled specially
    ),
    "issn_electronic": (
        ["electronic issn", "electronic issn/isbn", "eissn", "e-issn", "online issn"],
        None,  # ISSN normalization handled specially
    ),
    "source_type": (["type", "publication type", "content type"], _normalize_type),
    "language": (
        ["language", "primary language"],
        None,
    ),  # special: text + language normalizer
    "subjects": (["subjects", "subject", "categories", "category"], normalize_subjects),
}


def normalize_crossref_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize a raw Crossref DataFrame.

    Applies column mapping, ISSN validation, and all normalizations.
    Output DataFrame uses JournalDict field names directly.

    Args:
        df: Raw DataFrame from CSV read

    Returns:
        Normalized DataFrame with valid ISSNs only, columns named per JournalDict
    """
    # Normalize column names to lowercase
    df.columns = df.columns.str.strip().str.lower()
    col_list = df.columns.tolist()

    # Get raw ISSN columns
    issn_print_col = find_column(col_list, _CROSSREF_FIELDS["issn_print"][0])
    issn_electronic_col = find_column(col_list, _CROSSREF_FIELDS["issn_electronic"][0])

    # Compute normalized ISSNs (without modifying input df)
    issn_print = normalize_issn_series(df[issn_print_col]) if issn_print_col else pd.Series([None] * len(df), index=df.index)
    issn_electronic = normalize_issn_series(df[issn_electronic_col]) if issn_electronic_col else pd.Series([None] * len(df), index=df.index)

    # Filter rows with at least one valid ISSN
    has_issn = issn_print.notna() | issn_electronic.notna()
    df_valid = df[has_issn].copy()

    # Add normalized ISSNs with JournalDict field names
    df_valid["issn_print"] = issn_print[has_issn].values
    df_valid["issn_electronic"] = issn_electronic[has_issn].values

    # Get raw column references for special handling
    title_col = find_column(col_list, _CROSSREF_FIELDS["title"][0])
    publisher_col = find_column(col_list, _CROSSREF_FIELDS["publisher"][0])
    language_col = find_column(col_list, _CROSSREF_FIELDS["language"][0])

    # Title and publisher - use vectorized text normalization
    df_valid["title"] = normalize_text_series(df_valid[title_col]) if title_col else None
    df_valid["publisher"] = normalize_text_series(df_valid[publisher_col]) if publisher_col else None

    # Language - normalize text then apply language normalizer
    if language_col:
        lang_text = normalize_text_series(df_valid[language_col])
        df_valid["language"] = lang_text.apply(lambda x: normalize_language(x) if pd.notna(x) else [])
    else:
        df_valid["language"] = None

    # Apply normalizers for remaining fields
    for field, (candidates, normalizer) in _CROSSREF_FIELDS.items():
        if field in ("issn_print", "issn_electronic", "title", "publisher", "language"):
            continue  # Already handled above

        raw_col = find_column(col_list, candidates)
        if not raw_col:
            df_valid[field] = None
            continue

        if normalizer:
            df_valid[field] = df_valid[raw_col].apply(normalizer)
        else:
            df_valid[field] = df_valid[raw_col]

    return df_valid


# Fields to copy directly from row to JournalDict
_CROSSREF_DIRECT_FIELDS = [
    "issn_print",
    "issn_electronic",
    "title",
    "publisher",
    "source_type",
    "language",
    "subjects",
]


def process_crossref_record(row: dict) -> JournalDict:
    """
    Transform a normalized Crossref row dict into a JournalDict.

    Args:
        row: Dictionary with JournalDict field names (from normalize_crossref_dataframe)

    Returns:
        JournalDict with source metadata
    """
    journal: JournalDict = {
        "source": DataSource.CROSSREF,
        "country": None,
    }

    # Copy all prepared fields
    for field in _CROSSREF_DIRECT_FIELDS:
        val = row.get(field)
        if val is not None and not (isinstance(val, float) and pd.isna(val)):
            journal[field] = val

    return journal


def load_crossref_data(input_dir: Path) -> list[JournalDict]:
    """Load Crossref title list CSV."""
    journals = []
    csv_path = input_dir / "crossref" / "titleFile.csv"

    if not csv_path.exists():
        logger.warning("Crossref CSV not found, skipping...")
        return journals

    logger.info(f"Loading Crossref data from: {csv_path}")

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
        df_valid = normalize_crossref_dataframe(df)

        logger.info(f"  {len(df_valid):,} rows have valid ISSNs")

        # Build journal records
        journals = [process_crossref_record(row) for row in df_valid.to_dict("records")]

        logger.info(f"Loaded {len(journals):,} journals from Crossref")
    except Exception as e:
        logger.error(f"Error loading Crossref data: {e}")
        import traceback

        logger.debug(traceback.format_exc())

    # Deduplicate within source
    journals = deduplicate_journals(journals, "Crossref")
    return journals
