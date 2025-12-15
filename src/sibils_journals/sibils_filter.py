"""SIBiLS journal filtering and enrichment module.

This module handles matching unified journal records against SIBiLS
(Swiss Institute of Bioinformatics Literature Services) journal references.

SIBiLS Data (via sibils_fetch.py):
    Extracted from SIBiLS Elasticsearch indices (MEDLINE + PMC).
    Contains (journal, medline_ta, nlm_id) tuples where:
    - journal: Full journal name
    - medline_ta: MEDLINE abbreviation (text)
    - nlm_id: Numeric NLM ID (from PMC, for journals not in MEDLINE)

Matching Strategy (apply_sibils_filter, in priority order):
    1. Phase 1a: Match by medline_abbreviation against SIBiLS medline_ta
    2. Phase 1b: Match by nlm_id against SIBiLS nlm_id
    3. Phase 2: Match by normalized title against SIBiLS journal names
    4. Phase 3: Match by alternative_titles against SIBiLS journal names

Matching Enhancements:
    - Abbreviation expansion (build_abbreviation_lookup): Expands SIBiLS medline_ta
      to full titles using the unified data's medline_abbreviation → title mapping
    - "Journal of X" ↔ "X" variants (generate_title_variants): Generates title
      variants with safety measures (3+ words, generic terms blacklisted)

Processing Steps (apply_sibils_filter):
    1. Filter: Keep only journals that match SIBiLS entries
    2. Annotate: Add 'sibils' to sources field of matched records
    3. Soft merge: Add SIBiLS journal names to alternative_titles
    4. Add unmatched: Include SIBiLS-only entries as new records

Data Loading:
    - get_sibils_path: Resolve SIBiLS CSV path with version support (numeric sorting)
    - load_sibils_journals: Load data with bidirectional mappings
    - load_sibils_raw_data: Load raw tuples for unmatched reporting
"""

import csv
import logging
import re
from pathlib import Path

import pandas as pd

from .config import DEFAULT_SIBILS_DIR
from .merger import make_title_identifier, normalize_title_key
from .models import is_isbn, make_isbn_identifier, make_nlm_identifier

logger = logging.getLogger(__name__)

# Pattern for "Journal of X" / "The Journal of X" prefixes
JOURNAL_OF_PATTERN = re.compile(r"^(the\s+)?journal\s+of\s+", re.IGNORECASE)

# Generic terms that should not generate variants (too many false positives)
GENERIC_TERMS = {
    # Major scientific fields
    "medicine",
    "surgery",
    "biology",
    "chemistry",
    "physics",
    "immunology",
    "neurology",
    "cardiology",
    "urology",
    "genetics",
    "psychiatry",
    "pharmacology",
    "pathology",
    "radiology",
    "oncology",
    "dermatology",
    "nephrology",
    "gastroenterology",
    "endocrinology",
    "rheumatology",
    "hematology",
    "pulmonology",
    "ophthalmology",
    # Generic academic terms
    "science",
    "research",
    "studies",
    "review",
    "reports",
    "health",
    "care",
    "therapy",
    "education",
    "business",
    "management",
    "engineering",
    "technology",
    "development",
    # Broad social sciences
    "psychology",
    "sociology",
    "anthropology",
    "economics",
    "history",
    "philosophy",
    "literature",
    "art",
    "music",
    "law",
    "politics",
    "communication",
    "linguistics",
    # Generic qualifiers (can combine to create false positives)
    "clinical",
    "applied",
    "theoretical",
    "experimental",
    "international",
    "american",
    "european",
    "asian",
    "african",
    "medical",
    "scientific",
    "academic",
    "professional",
    "general",
    "modern",
    "contemporary",
    "current",
    "basic",
    "advanced",
    "practical",
    "critical",
    "comparative",
}


def generate_title_variants(title_key: str, existing_titles: set[str] | None = None) -> set[str]:
    """Generate normalized title variants for "Journal of X" ↔ "X" matching.

    This handles cases where:
    - SIBiLS has "Journal of Crohn s and Colitis" but unified has "Crohn s and Colitis"
    - SIBiLS has "Abdominal Wall Reconstruction" but unified has "Journal of Abdominal Wall Reconstruction"

    Safety measures to avoid false positives:
    - Requires 3+ words (e.g., "Neurology" and "Clinical Medicine" are skipped)
    - Blacklists generic terms (e.g., "chemistry", "biology", "clinical")
    - Skips if both forms exist in SIBiLS (conflict detection)

    Args:
        title_key: Normalized title key
        existing_titles: Optional set of existing SIBiLS titles for conflict detection

    Returns:
        Set of variant title keys (may be empty if safety conditions not met)
    """
    variants: set[str] = set()

    # Check if title starts with "journal of" pattern
    if JOURNAL_OF_PATTERN.match(title_key):
        # Strip "journal of" / "the journal of" prefix
        stripped = JOURNAL_OF_PATTERN.sub("", title_key).strip()
        if not stripped:
            return variants

        core_words = stripped.split()

        # Require 3+ words to avoid false positives
        if len(core_words) < 3:
            return variants

        # Check for generic terms that commonly have distinct journals
        if any(word in GENERIC_TERMS for word in core_words):
            return variants

        # Conflict detection: if "X" already exists in SIBiLS, don't create
        # a variant that would incorrectly match "Journal of X" with "X"
        if existing_titles and stripped in existing_titles:
            return variants

        variants.add(stripped)
    else:
        core_words = title_key.split()

        # Require 3+ words to avoid false positives
        if len(core_words) < 3:
            return variants

        # Check for generic terms
        if any(word in GENERIC_TERMS for word in core_words):
            return variants

        # Add "journal of X" variant
        prefixed = f"journal of {title_key}"

        # Conflict detection: if "Journal of X" already exists in SIBiLS,
        # don't create a variant that would incorrectly match "X" with it
        if existing_titles and prefixed in existing_titles:
            return variants

        variants.add(prefixed)

    return variants


def build_abbreviation_lookup(df: pd.DataFrame) -> dict[str, str]:
    """Build medline_abbreviation → normalized_title lookup from unified data.

    This allows expanding SIBiLS medline_ta abbreviations to full titles
    for better matching coverage.

    Args:
        df: Unified DataFrame with medline_abbreviation and title columns

    Returns:
        Dict mapping normalized abbreviation keys to normalized title keys
    """
    lookup: dict[str, str] = {}
    for abbr, title in zip(df["medline_abbreviation"], df["title"]):
        if pd.notna(abbr) and pd.notna(title):
            abbr_key = normalize_title_key(abbr)
            title_key = normalize_title_key(title)
            if abbr_key and title_key:
                lookup[abbr_key] = title_key
    return lookup


def _parse_sibils_version(path: Path) -> tuple[int, ...]:
    """Extract version tuple from path like journal_fields_v5.0.5.8.csv."""
    match = re.search(r"journal_fields_v([\d.]+)\.csv$", path.name)
    if match:
        return tuple(int(x) for x in match.group(1).split("."))
    return (0,)


def get_sibils_path(version: str | None = None) -> Path:
    """Get path to SIBiLS journal_fields CSV.

    Args:
        version: Optional version string (e.g., "5.0.5.8"). If None, uses most recent.

    Returns:
        Path to the CSV file.

    Raises:
        FileNotFoundError: If no matching file found.
    """
    if version:
        sibils_path = DEFAULT_SIBILS_DIR / f"journal_fields_v{version}.csv"
        if not sibils_path.exists():
            raise FileNotFoundError(f"SIBiLS file not found: {sibils_path}. Run 'sibils-journals fetch-sibils' first.")
        return sibils_path

    sibils_files = sorted(DEFAULT_SIBILS_DIR.glob("journal_fields_v*.csv"), key=_parse_sibils_version)
    if not sibils_files:
        raise FileNotFoundError(f"No SIBiLS journal_fields CSV found in {DEFAULT_SIBILS_DIR}. Run 'sibils-journals fetch-sibils' first.")
    return sibils_files[-1]  # Most recent version


def load_sibils_journals(
    version: str | None = None,
) -> tuple[
    set[str],
    set[str],
    set[str],
    dict[str, set[str]],
    dict[str, set[str]],
    dict[str, set[str]],
]:
    """
    Load SIBiLS journal data for filtering.

    Args:
        version: Optional version string (e.g., "5.0.5.8"). If None, uses most recent.

    Returns:
        Tuple of:
        - set of normalized title keys
        - set of medline_ta values (text abbreviations only)
        - set of nlm_id values (numeric IDs from PMC)
        - dict mapping title_key -> associated medline_tas
        - dict mapping medline_ta -> associated title_keys
        - dict mapping nlm_id -> associated title_keys
    """
    sibils_path = get_sibils_path(version)
    logger.info(f"Loading SIBiLS file: {sibils_path}")

    title_keys: set[str] = set()
    medline_tas: set[str] = set()
    nlm_ids: set[str] = set()
    title_to_medline: dict[str, set[str]] = {}
    medline_to_title: dict[str, set[str]] = {}
    nlm_id_to_title: dict[str, set[str]] = {}

    with open(sibils_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            journal = row.get("journal", "").strip()
            medline_ta = row.get("medline_ta", "").strip()
            nlm_id_raw = row.get("nlm_id", "").strip()
            # Normalize NLM ID by stripping leading zeros for consistent matching
            nlm_id = nlm_id_raw.lstrip("0") if nlm_id_raw else ""

            title_key = normalize_title_key(journal) if journal else None

            if title_key:
                title_keys.add(title_key)
            if medline_ta:
                medline_tas.add(medline_ta)
            if nlm_id:
                nlm_ids.add(nlm_id)

            # Build bidirectional mappings
            if title_key and medline_ta:
                title_to_medline.setdefault(title_key, set()).add(medline_ta)
                medline_to_title.setdefault(medline_ta, set()).add(title_key)
            if title_key and nlm_id:
                nlm_id_to_title.setdefault(nlm_id, set()).add(title_key)

    logger.info(f"Loaded {len(title_keys):,} unique titles, {len(medline_tas):,} medline_ta, {len(nlm_ids):,} nlm_id from SIBiLS")
    return (
        title_keys,
        medline_tas,
        nlm_ids,
        title_to_medline,
        medline_to_title,
        nlm_id_to_title,
    )


def load_sibils_raw_data(
    version: str | None = None,
) -> list[tuple[str, str, str, str | None]]:
    """
    Load raw SIBiLS journal data with original titles preserved.

    Args:
        version: Optional version string (e.g., "5.0.5.8"). If None, uses most recent.

    Returns:
        List of tuples: (original_journal, medline_ta, nlm_id, title_key)
    """
    sibils_path = get_sibils_path(version)

    rows = []
    with open(sibils_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            journal = row.get("journal", "").strip()
            medline_ta = row.get("medline_ta", "").strip()
            nlm_id = row.get("nlm_id", "").strip()
            title_key = normalize_title_key(journal) if journal else None
            rows.append((journal, medline_ta, nlm_id, title_key))

    return rows


def apply_sibils_filter(
    df: pd.DataFrame,
    output_dir: Path | None = None,
    version: str | None = None,
) -> pd.DataFrame:
    """
    Filter and enrich unified DataFrame with SIBiLS journal data.

    Purpose:
        - Provide journal information for SIBiLS users
        - Enable autocompletion with only SIBiLS-referenced journals
        - Allow notification when SIBiLS has no articles for a journal

    Matching Strategy (in priority order):
        1. Match by medline_abbreviation against SIBiLS medline_ta
        2. Match by normalized title against SIBiLS journal names
        3. Match by alternative_titles against SIBiLS journal names

    Processing Steps:
        1. Filter: Keep only journals that match SIBiLS entries
        2. Annotate: Add 'sibils' to sources field of matched records
        3. Soft merge: Add SIBiLS journal names to alternative_titles
        4. Add unmatched: Include SIBiLS-only entries as new records

    Data Loading:
        - load_sibils_journals(): Used for matching (steps 1-3) - returns
          normalized sets and bidirectional mappings for O(1) lookups
        - load_sibils_raw_data(): Used for adding unmatched entries (step 4) -
          preserves original journal titles for display

    Transitive Matching:
        SIBiLS rows contain (journal, medline_ta) pairs. When a match occurs
        via one identifier, the associated identifier is also marked as matched.

    Args:
        df: Unified DataFrame with journal records
        output_dir: If provided, write unmatched SIBiLS entries to CSV
        version: Optional SIBiLS version string (e.g., "5.0.5.8"). If None, uses most recent.

    Returns:
        DataFrame with:
        - Only matched journals (filtered)
        - 'sibils' added to sources of matched records
        - SIBiLS titles added to alternative_titles
        - Unmatched SIBiLS entries added as new records

    Side effects:
        If output_dir is provided, writes sibils_unmatched.csv for debugging.
    """
    logger.info("=" * 60)
    logger.info("Applying SIBiLS Filter")
    logger.info("=" * 60)

    (
        sibils_titles,
        sibils_medline_tas,
        sibils_nlm_ids,
        title_to_medline,
        medline_to_title,
        nlm_id_to_title,
    ) = load_sibils_journals(version)
    sibils_raw = load_sibils_raw_data(version)

    original_count = len(df)

    # ========== Abbreviation Expansion ==========
    # Build lookup from unified data to expand SIBiLS medline_ta to full titles
    abbr_to_title = build_abbreviation_lookup(df)
    logger.info(f"  Built abbreviation lookup with {len(abbr_to_title):,} entries")

    # Expand SIBiLS medline_ta abbreviations to title keys for better matching
    expanded_titles: set[str] = set()
    for medline_ta in sibils_medline_tas:
        medline_key = normalize_title_key(medline_ta)
        if medline_key and medline_key in abbr_to_title:
            expanded_title = abbr_to_title[medline_key]
            if expanded_title not in sibils_titles:
                expanded_titles.add(expanded_title)
                # Also update the reverse mapping for transitive matching
                medline_to_title.setdefault(medline_ta, set()).add(expanded_title)

    if expanded_titles:
        logger.info(f"  Expanded {len(expanded_titles):,} medline_ta abbreviations to titles")
        sibils_titles = sibils_titles | expanded_titles

    # ========== "Journal of X" ↔ "X" Variant Expansion ==========
    # Generate title variants to match "Journal of Urology" ↔ "Urology"
    # Safety: requires 3+ words, blacklists generic terms, detects conflicts
    # Keep track of original titles (before variants) for unmatched reporting
    original_sibils_titles = sibils_titles.copy()

    title_variants: set[str] = set()
    for title_key in sibils_titles:
        for variant in generate_title_variants(title_key, existing_titles=sibils_titles):
            if variant not in sibils_titles:
                title_variants.add(variant)

    if title_variants:
        logger.info(f"  Generated {len(title_variants):,} 'Journal of X' ↔ 'X' variants (3+ words, no generic terms)")
        sibils_titles = sibils_titles | title_variants

    # Track which SIBiLS entries were matched
    matched_sibils_titles: set[str] = set()
    matched_sibils_medline_tas: set[str] = set()

    # Maps index -> set of SIBiLS title_keys to add to alternative_titles
    index_to_sibils_titles: dict[int, set[str]] = {}

    # ========== Phase 1: Match by medline_abbreviation (vectorized) ==========
    medline_mask = df["medline_abbreviation"].isin(sibils_medline_tas)
    matched_by_medline_ta = int(medline_mask.sum())
    medline_matched_indices = set(df[medline_mask].index)

    # Track matched SIBiLS entries and collect titles to add
    for idx in medline_matched_indices:
        medline_abbr = df.at[idx, "medline_abbreviation"]
        matched_sibils_medline_tas.add(medline_abbr)
        if medline_abbr in medline_to_title:
            matched_sibils_titles.update(medline_to_title[medline_abbr])
            index_to_sibils_titles[idx] = medline_to_title[medline_abbr].copy()

    # ========== Phase 1b: Match by nlm_id ==========
    # SIBiLS NLM IDs are extracted from PMC (numeric values in medline_ta field)
    matched_sibils_nlm_ids: set[str] = set()
    nlm_matched_indices: set[int] = set()
    matched_by_nlm_id = 0

    if sibils_nlm_ids:
        # Normalize unified nlm_id by stripping leading zeros
        # (SIBiLS nlm_ids are already normalized in load_sibils_journals)
        normalized_nlm_ids = df["nlm_id"].apply(lambda x: str(x).lstrip("0") or "0" if pd.notna(x) else None)
        nlm_id_mask = normalized_nlm_ids.isin(sibils_nlm_ids)
        matched_by_nlm_id = int(nlm_id_mask.sum())
        # Only count as "new" matches those not already matched by medline_abbreviation
        nlm_matched_indices = set(df[nlm_id_mask].index) - medline_matched_indices

        # Track ALL matched SIBiLS nlm_ids (including those also matched by medline_ta)
        for idx in df[nlm_id_mask].index:
            nlm_id = normalized_nlm_ids.at[idx]
            matched_sibils_nlm_ids.add(nlm_id)
            # Only add titles for records not already processed by medline matching
            if idx in nlm_matched_indices and nlm_id in nlm_id_to_title:
                matched_sibils_titles.update(nlm_id_to_title[nlm_id])
                index_to_sibils_titles[idx] = nlm_id_to_title[nlm_id].copy()

    # ========== Phase 2: Match by title (vectorized with pre-computed keys) ==========
    # Only process rows not already matched
    unmatched_mask = ~df.index.isin(medline_matched_indices | nlm_matched_indices)
    unmatched_df = df[unmatched_mask]

    # Pre-compute normalized title keys for unmatched rows
    title_keys_series = unmatched_df["title"].apply(lambda t: normalize_title_key(t) if pd.notna(t) else None)
    title_match_mask = title_keys_series.isin(sibils_titles)
    matched_by_title = int(title_match_mask.sum())
    title_matched_indices = set(unmatched_df[title_match_mask].index)

    # Track matched SIBiLS entries
    for idx in title_matched_indices:
        title_key = title_keys_series.at[idx]
        if title_key:
            matched_sibils_titles.add(title_key)
            if title_key in title_to_medline:
                matched_sibils_medline_tas.update(title_to_medline[title_key])

    # ========== Phase 3: Match by alternative_titles (only unmatched rows) ==========
    already_matched = medline_matched_indices | nlm_matched_indices | title_matched_indices
    still_unmatched_mask = ~df.index.isin(already_matched)
    alt_matched_indices = set()
    matched_by_alt_title = 0

    # Only iterate over unmatched rows with alternative_titles
    for idx, alt_titles in df.loc[still_unmatched_mask, "alternative_titles"].items():
        if pd.isna(alt_titles) or not alt_titles:
            continue
        for alt in str(alt_titles).split("|"):
            alt_key = normalize_title_key(alt.strip())
            if alt_key and alt_key in sibils_titles:
                alt_matched_indices.add(idx)
                matched_by_alt_title += 1
                matched_sibils_titles.add(alt_key)
                if alt_key in title_to_medline:
                    matched_sibils_medline_tas.update(title_to_medline[alt_key])
                break

    # Combine all matched indices
    matched_indices = medline_matched_indices | nlm_matched_indices | title_matched_indices | alt_matched_indices

    # Filter DataFrame to matched entries
    df_filtered = df.loc[list(matched_indices)].copy()

    # Add 'sibils' to sources for all matched records (vectorized)
    def add_sibils_source(sources):
        if pd.isna(sources) or sources == "":
            return "sibils"
        sources_list = sorted(set(s.strip() for s in str(sources).split("|")) | {"sibils"})
        return "|".join(sources_list)

    df_filtered["sources"] = df_filtered["sources"].apply(add_sibils_source)

    # Soft merge: Add SIBiLS titles to alternative_titles
    # Pre-build lookup from title_key -> original journal names (avoids O(n*m) iteration)
    title_key_to_originals: dict[str, set[str]] = {}
    for orig_journal, medline_ta, nlm_id, title_key in sibils_raw:
        if title_key and orig_journal:
            title_key_to_originals.setdefault(title_key, set()).add(orig_journal)

    titles_added = 0
    for idx in matched_indices:
        if idx not in index_to_sibils_titles:
            continue

        # Get current alternative_titles
        current_alt = df_filtered.at[idx, "alternative_titles"]
        if pd.isna(current_alt) or current_alt == "":
            current_set = set()
        else:
            current_set = set(t.strip() for t in str(current_alt).split("|"))

        # Add SIBiLS original titles for matched title_keys
        new_titles = set()
        for title_key in index_to_sibils_titles[idx]:
            if title_key in title_key_to_originals:
                new_titles.update(title_key_to_originals[title_key] - current_set)

        if new_titles:
            combined = current_set | new_titles
            df_filtered.at[idx, "alternative_titles"] = "|".join(sorted(combined))
            titles_added += len(new_titles)

    records_enriched = len([idx for idx in matched_indices if idx in index_to_sibils_titles])
    logger.info(f"  Added 'sibils' to sources of {len(matched_indices):,} matched records")
    logger.info(f"  Soft merge: Enriched {records_enriched:,} records with {titles_added:,} SIBiLS titles")

    # Calculate unmatched SIBiLS entries (use original titles, not generated variants)
    unmatched_titles = original_sibils_titles - matched_sibils_titles
    unmatched_medline_tas = sibils_medline_tas - matched_sibils_medline_tas
    unmatched_nlm_ids = sibils_nlm_ids - matched_sibils_nlm_ids

    # Log detailed matching stats
    total_matched = matched_by_medline_ta + matched_by_nlm_id + matched_by_title + matched_by_alt_title
    logger.info("  Matching summary:")
    logger.info(f"    - Total unified records matched: {total_matched:,}")
    logger.info(f"    - By medline_abbreviation: {matched_by_medline_ta:,}")
    logger.info(f"    - By nlm_id: {matched_by_nlm_id:,}")
    logger.info(f"    - By title: {matched_by_title:,}")
    logger.info(f"    - By alternative_titles: {matched_by_alt_title:,}")
    logger.info(f"  Filtered: {original_count:,} → {len(df_filtered):,} journals")
    removed_count = original_count - len(df_filtered)
    logger.info(f"  Removed {removed_count:,} journals not in SIBiLS")

    # Write removed journals to CSV if output_dir provided
    if output_dir and removed_count > 0:
        removed_indices = set(df.index) - matched_indices
        df_removed = df.loc[list(removed_indices)]
        removed_file = output_dir / "sibils_removed.csv"
        df_removed.to_csv(removed_file, index=False)
        logger.info(f"  Wrote {removed_count:,} removed journals to: {removed_file}")

    logger.info("  SIBiLS coverage:")
    logger.info(f"    - Matched SIBiLS titles: {len(matched_sibils_titles):,} / {len(original_sibils_titles):,}")
    logger.info(f"    - Matched SIBiLS medline_ta: {len(matched_sibils_medline_tas):,} / {len(sibils_medline_tas):,}")
    logger.info(f"    - Matched SIBiLS nlm_id: {len(matched_sibils_nlm_ids):,} / {len(sibils_nlm_ids):,}")
    logger.info(f"    - Unmatched SIBiLS titles: {len(unmatched_titles):,}")
    logger.info(f"    - Unmatched SIBiLS medline_ta: {len(unmatched_medline_tas):,}")
    logger.info(f"    - Unmatched SIBiLS nlm_id: {len(unmatched_nlm_ids):,}")

    # Add unmatched SIBiLS entries as new records
    # But first, build a set of all alternative_titles from matched records
    # to avoid adding duplicates for renamed journals
    alt_title_keys = set()
    for idx in matched_indices:
        alt_titles = df_filtered.at[idx, "alternative_titles"]
        if pd.notna(alt_titles) and alt_titles:
            for alt in str(alt_titles).split("|"):
                alt_key = normalize_title_key(alt.strip())
                if alt_key:
                    alt_title_keys.add(alt_key)

    new_records = []
    seen_title_keys = set()  # Avoid duplicates
    skipped_in_alt_titles = 0

    for orig_journal, medline_ta, nlm_id, title_key in sibils_raw:
        # Check if this entry was matched
        if title_key and title_key in matched_sibils_titles:
            continue
        if medline_ta and medline_ta in matched_sibils_medline_tas:
            continue
        if nlm_id and nlm_id in matched_sibils_nlm_ids:
            continue

        # Skip if the title appears in alternative_titles of a matched record
        # (handles renamed journals where old name is in alternative_titles)
        if title_key and title_key in alt_title_keys:
            skipped_in_alt_titles += 1
            continue

        # Skip if we've already added a record for this title_key
        if title_key and title_key in seen_title_keys:
            continue
        if title_key:
            seen_title_keys.add(title_key)

        # Create new record for unmatched SIBiLS entry
        # Priority: NLM ID > ISBN (from medline_ta) > title-based
        if nlm_id:
            unified_id = make_nlm_identifier(nlm_id)
        elif medline_ta and is_isbn(medline_ta):
            unified_id = make_isbn_identifier(medline_ta)
        elif orig_journal:
            unified_id = make_title_identifier(orig_journal)
        else:
            continue

        new_record = {
            "unified_id": unified_id,
            "title": orig_journal,
            "medline_abbreviation": medline_ta if medline_ta else None,
            "nlm_id": nlm_id if nlm_id else None,
            "sources": "sibils",
            # All other fields remain null/empty
        }
        new_records.append(new_record)

    if new_records:
        df_new = pd.DataFrame(new_records)
        df_filtered = pd.concat([df_filtered, df_new], ignore_index=True)
        logger.info(f"  Added {len(new_records):,} unmatched SIBiLS journals as new records")
    if skipped_in_alt_titles:
        logger.info(f"  Skipped {skipped_in_alt_titles:,} SIBiLS entries (title in alternative_titles of matched records)")

    # Write unmatched report if output_dir provided (for debugging)
    if output_dir and (unmatched_titles or unmatched_medline_tas or unmatched_nlm_ids):
        unmatched_file = output_dir / "sibils_unmatched.csv"
        with open(unmatched_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["type", "value"])
            for title in sorted(unmatched_titles):
                writer.writerow(["title", title])
            for medline_ta in sorted(unmatched_medline_tas):
                writer.writerow(["medline_ta", medline_ta])
            for nlm_id in sorted(unmatched_nlm_ids):
                writer.writerow(["nlm_id", nlm_id])
        logger.info(f"  Wrote unmatched SIBiLS debug info to: {unmatched_file}")

    return df_filtered
