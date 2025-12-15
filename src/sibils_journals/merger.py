"""Journal data merger - unifies records from multiple sources.

Merge Algorithm Overview
========================

This module implements a 4-phase deduplication and merge strategy to unify
journal records from multiple data sources (Crossref, OpenAlex, DOAJ, PMC, NLM).

Phases:
    1. Key Resolution: Build ISSN → canonical key mapping (see KeyResolver class)
       - Detects ISSN reuse: when the same ISSN appears with different NLM IDs,
         records are kept separate (different journals reusing the same ISSN)
       - Exports ISSN reuse conflicts to CSV for auditing
    2. ISSN-based merge: Group records by resolved canonical key
    3. Title-based merge: Match records without ISSN to existing records by title
    4. Synthetic IDs: Assign NLM-xxx, ISBN-xxx, OPENALEX-xxx, or TITLE-xxx
       identifiers to records that couldn't be matched

Key Functions:
    - unify_journals(): Main entry point, orchestrates all phases
    - merge_journal_records(): Field-level merge with priority rules
    - KeyResolver: Handles ISSN-L resolution, collision detection, and ISSN reuse

Source Priority:
    See DEFAULT_SOURCE_PRIORITY in models.py (higher value = preferred)

Field Merge Rules (see merge_journal_records):
    - Scalar fields: higher priority source wins, or fills empty values
    - Boolean fields: True takes priority over False/None
    - List fields: merge unique values from all sources
    - Identifiers (ISSN, NLM ID, OpenAlex ID): always fill if missing
"""

import csv
import hashlib
import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd
from tqdm import tqdm

from .models import (
    DEFAULT_SOURCE_PRIORITY,
    DataSource,
    JournalDict,
    is_isbn,
    make_isbn_identifier,
    make_nlm_identifier,
    make_openalex_identifier,
    serialize_journal,
)
from .normalizers import normalize_title

logger = logging.getLogger(__name__)


class KeyResolver:
    """
    Resolves journal records to canonical keys, ensuring ISSN uniqueness.

    Handles:
    - ISSN-L linking (multiple ISSNs → same ISSN-L)
    - ISSN collisions (same ISSN in different records → same key)
    - NLM ID conflicts: when same ISSN has different NLM IDs, creates separate
      records using NLM-{id} as the key (preserves journal identity)
    - Conflict detection and logging

    Usage:
        resolver = KeyResolver(issn_l_map)
        for journal in journals:
            resolver.register(journal)
        resolver.log_stats()

        for journal in journals:
            key = resolver.get_canonical_key(journal)
            # use key for merging
    """

    def __init__(self, issn_l_map: dict[str, str]):
        self.issn_l_map = issn_l_map
        # Maps any ISSN to its canonical key
        self._issn_to_key: dict[str, str] = {}
        # Tracks which ISSNs belong to each key (for debugging)
        self._key_to_issns: dict[str, set[str]] = {}
        # Logs conflicts for auditing
        self._conflicts: list[dict] = []
        # Track NLM ID per canonical key (for ISSN reuse detection)
        self._key_to_nlm_id: dict[str, str] = {}
        # Maps NLM ID to its unique key (for journals with ISSN conflicts)
        self._nlm_id_to_key: dict[str, str] = {}
        # Track ISSN reuse conflicts where different NLM IDs prevented merge
        self._issn_reuse_conflicts: list[dict] = []

    def register(self, journal: JournalDict) -> None:
        """Register a journal's ISSNs, building the canonical key mapping."""
        issns = self._get_all_issns(journal)
        nlm_id = journal.get("nlm_id")

        # If journal has no ISSNs but has NLM ID, use NLM-based key
        if not issns:
            if nlm_id:
                nlm_key = make_nlm_identifier(nlm_id)
                self._nlm_id_to_key[nlm_id] = nlm_key
                self._key_to_nlm_id[nlm_key] = nlm_id
            return

        # Determine the canonical key for this journal
        canonical_key = self._determine_canonical_key(journal)
        if not canonical_key:
            return

        # Check if any ISSN already maps to a different key
        existing_key = None
        conflicting_issn = None
        for issn in issns:
            if issn in self._issn_to_key:
                existing_key = self._issn_to_key[issn]
                conflicting_issn = issn
                break

        # Use existing key if found (ensures consistency)
        # BUT check for NLM ID conflict first - different NLM IDs mean different journals
        if existing_key:
            existing_nlm = self._key_to_nlm_id.get(existing_key)

            # If both have different NLM IDs, don't merge - keep them separate
            if existing_nlm and nlm_id and existing_nlm != nlm_id:
                self._issn_reuse_conflicts.append(
                    {
                        "issn": conflicting_issn,
                        "existing_key": existing_key,
                        "existing_nlm_id": existing_nlm,
                        "new_nlm_id": nlm_id,
                        "new_title": journal.get("title"),
                    }
                )
                # Use NLM ID as the key for this separate journal record
                final_key = make_nlm_identifier(nlm_id)
                self._nlm_id_to_key[nlm_id] = final_key
            else:
                final_key = existing_key
                if existing_key != canonical_key:
                    self._conflicts.append(
                        {
                            "issns": issns,
                            "canonical_key": canonical_key,
                            "resolved_to": existing_key,
                            "title": journal.get("title"),
                        }
                    )
        else:
            final_key = canonical_key

        # Track NLM ID for this key
        if nlm_id:
            if final_key not in self._key_to_nlm_id:
                self._key_to_nlm_id[final_key] = nlm_id
            # Also track NLM ID → key mapping for lookup
            if nlm_id not in self._nlm_id_to_key:
                self._nlm_id_to_key[nlm_id] = final_key

        # Register ISSNs to this key, but don't overwrite mappings to keys with different NLM IDs
        for issn in issns:
            if issn in self._issn_to_key:
                existing_issn_key = self._issn_to_key[issn]
                if existing_issn_key != final_key:
                    # Check if overwriting would cause NLM ID conflict
                    existing_issn_nlm = self._key_to_nlm_id.get(existing_issn_key)
                    final_nlm = self._key_to_nlm_id.get(final_key) or nlm_id
                    if existing_issn_nlm and final_nlm and existing_issn_nlm != final_nlm:
                        # Don't overwrite - this ISSN belongs to a different journal
                        # But DO register this ISSN to the NLM-based key for the new journal
                        if nlm_id:
                            nlm_key = self._nlm_id_to_key.get(nlm_id)
                            if nlm_key:
                                # Track this ISSN as belonging to this NLM-based key too
                                self._key_to_issns.setdefault(nlm_key, set()).add(issn)
                        continue
            self._issn_to_key[issn] = final_key
        self._key_to_issns.setdefault(final_key, set()).update(issn for issn in issns if self._issn_to_key.get(issn) == final_key)

    def get_canonical_key(self, journal: JournalDict) -> str | None:
        """Get the canonical key for a journal (must call register() first).

        For journals with NLM ID conflicts (same ISSN, different NLM IDs),
        returns the NLM-based key to keep them separate.
        """
        nlm_id = journal.get("nlm_id")

        # If this NLM ID has a dedicated key (due to ISSN conflict), use it
        if nlm_id and nlm_id in self._nlm_id_to_key:
            nlm_key = self._nlm_id_to_key[nlm_id]
            # Verify this is indeed a separate key (not just an NLM-based key for a normal record)
            # A separate key would be in format NLM-{id}
            if nlm_key.startswith("NLM-"):
                return nlm_key

        # Standard lookup by ISSN
        issns = self._get_all_issns(journal)
        for issn in issns:
            if issn in self._issn_to_key:
                return self._issn_to_key[issn]

        # Fallback: compute key directly
        return self._determine_canonical_key(journal)

    def _get_all_issns(self, journal: JournalDict) -> list[str]:
        """Extract all ISSNs from a journal record."""
        issns = []
        for field in ["issn_l", "issn_print", "issn_electronic"]:
            issn = journal.get(field)
            if issn:
                issns.append(issn)
        return issns

    def _determine_canonical_key(self, journal: JournalDict) -> str | None:
        """Determine the canonical key for a journal."""
        pissn = journal.get("issn_print")
        eissn = journal.get("issn_electronic")
        issn_l = journal.get("issn_l")

        # Try to resolve ISSN-L from mapping
        if not issn_l:
            if pissn and pissn in self.issn_l_map:
                issn_l = self.issn_l_map[pissn]
            elif eissn and eissn in self.issn_l_map:
                issn_l = self.issn_l_map[eissn]

        # Priority: ISSN-L > print > electronic
        return issn_l or pissn or eissn

    def get_conflicts(self) -> list[dict]:
        """Return list of detected conflicts for auditing."""
        return self._conflicts

    def get_issn_reuse_conflicts(self) -> list[dict]:
        """Return ISSN reuse conflicts where different NLM IDs prevented merge."""
        return self._issn_reuse_conflicts

    def log_stats(self) -> None:
        """Log resolution statistics."""
        logger.info(f"  KeyResolver: {len(self._issn_to_key):,} ISSNs → {len(self._key_to_issns):,} keys")
        if self._conflicts:
            logger.warning(f"  KeyResolver: {len(self._conflicts)} conflicts detected")
        if self._issn_reuse_conflicts:
            logger.warning(f"  KeyResolver: {len(self._issn_reuse_conflicts)} ISSN reuse conflicts (different NLM IDs)")
            for conflict in self._issn_reuse_conflicts[:5]:  # Show first 5
                logger.warning(f"    ISSN {conflict['issn']}: NLM {conflict['existing_nlm_id']} vs {conflict['new_nlm_id']}")


def create_unified_record(journal: JournalDict, source: DataSource) -> JournalDict:
    """
    Create a new unified record from a journal dictionary.

    Ensures list fields are properly initialized.

    Args:
        journal: Dictionary containing journal data
        source: DataSource enum value

    Returns:
        New JournalDict with sources initialized
    """
    # Build initial all_issns list from available ISSNs
    all_issns = []
    for issn_field in ["issn_l", "issn_print", "issn_electronic"]:
        issn = journal.get(issn_field)
        if issn and issn not in all_issns:
            all_issns.append(issn)

    return JournalDict(
        # Core identifiers
        issn_l=journal.get("issn_l"),
        issn_print=journal.get("issn_print"),
        issn_electronic=journal.get("issn_electronic"),
        nlm_id=journal.get("nlm_id"),
        openalex_id=journal.get("openalex_id"),
        wikidata_id=journal.get("wikidata_id"),
        title=journal.get("title"),
        publisher=journal.get("publisher"),
        country=journal.get("country"),
        sources=[source],
        # ISSN lookup
        all_issns=all_issns,
        # Journal relationships
        predecessor_nlm_ids=list(journal.get("predecessor_nlm_ids") or []),
        successor_nlm_ids=list(journal.get("successor_nlm_ids") or []),
        # Basic metadata
        medline_abbreviation=journal.get("medline_abbreviation"),
        is_medline_indexed=journal.get("is_medline_indexed"),
        is_pmc_indexed=journal.get("is_pmc_indexed"),
        # PMC agreement details
        pmc_agreement_status=journal.get("pmc_agreement_status"),
        pmc_last_deposit_year=journal.get("pmc_last_deposit_year"),
        pmc_embargo_months=journal.get("pmc_embargo_months"),
        alternative_titles=list(journal.get("alternative_titles") or []),
        other_organisations=list(journal.get("other_organisations") or []),
        source_type=journal.get("source_type"),
        is_oa=journal.get("is_oa"),
        subjects=list(journal.get("subjects") or []),
        subject_domain=journal.get("subject_domain"),
        subject_field=journal.get("subject_field"),
        subject_subfield=journal.get("subject_subfield"),
        apc_amount=journal.get("apc_amount"),
        apc_currency=journal.get("apc_currency"),
        language=list(journal.get("language") or []),
        # URLs
        journal_url=journal.get("journal_url"),
        # Licensing
        license=journal.get("license"),
        license_url=journal.get("license_url"),
        # Editorial
        review_process=list(journal.get("review_process") or []),
        review_process_url=journal.get("review_process_url"),
        # Preservation
        preservation_services=list(journal.get("preservation_services") or []),
        # Copyright
        copyright_author=journal.get("copyright_author"),
        copyright_url=journal.get("copyright_url"),
        # Quality
        plagiarism_screening=journal.get("plagiarism_screening"),
        deposit_policy=list(journal.get("deposit_policy") or []),
        # Metrics
        works_count=journal.get("works_count"),
        cited_by_count=journal.get("cited_by_count"),
        h_index=journal.get("h_index"),
    )


def merge_journal_records(
    existing: JournalDict,
    new_journal: JournalDict,
    source: DataSource,
    new_priority: int,
    source_priority: dict[DataSource, int],
) -> None:
    """
    Merge a new journal dictionary into an existing unified record.

    Updates the existing record in-place based on source priority and field availability.

    Args:
        existing: Existing unified record to update
        new_journal: New journal data dictionary to merge
        source: DataSource enum value of new journal data
        new_priority: Priority value of the new source
        source_priority: Dictionary mapping DataSource to priority values
    """
    # Add source if not already present
    sources = existing.get("sources", [])
    if source not in sources:
        sources.append(source)
        existing["sources"] = sources

    # Calculate priority of existing sources (excluding current)
    existing_priorities = [source_priority.get(s, 0) for s in sources if s != source]
    current_max_priority = max(existing_priorities) if existing_priorities else -1

    # Update fields if new source has higher priority or field is empty
    should_update = new_priority > current_max_priority

    # Scalar text fields: update if empty or higher priority source
    scalar_text_fields = [
        "title",
        "publisher",
        "country",
        "source_type",
        "medline_abbreviation",
        "pmc_agreement_status",
        "subject_domain",
        "subject_field",
        "subject_subfield",
        "apc_currency",
        "journal_url",
        "license",
        "license_url",
        "review_process_url",
        "copyright_url",
    ]
    for field in scalar_text_fields:
        new_value = new_journal.get(field)
        if new_value:
            existing_value = existing.get(field)
            if not existing_value or should_update:
                existing[field] = new_value

    # Boolean fields: True takes priority
    for field in [
        "is_oa",
        "is_medline_indexed",
        "is_pmc_indexed",
        "copyright_author",
        "plagiarism_screening",
    ]:
        new_value = new_journal.get(field)
        if new_value is True:
            existing[field] = True
        elif new_value is not None and existing.get(field) is None:
            existing[field] = new_value

    # Numeric fields: update if empty or higher priority
    for field in ["apc_amount", "works_count", "cited_by_count", "h_index", "pmc_last_deposit_year", "pmc_embargo_months"]:
        new_value = new_journal.get(field)
        if new_value is not None:
            existing_value = existing.get(field)
            if existing_value is None or should_update:
                existing[field] = new_value

    # List fields: merge unique values
    for field in [
        "alternative_titles",
        "other_organisations",
        "subjects",
        "review_process",
        "preservation_services",
        "deposit_policy",
        "language",
        "predecessor_nlm_ids",
        "successor_nlm_ids",
    ]:
        new_values = new_journal.get(field) or []
        if new_values:
            existing_list = existing.get(field, [])
            for val in new_values:
                if val and val not in existing_list:
                    existing_list.append(val)
            existing[field] = existing_list

    # Always add ISSNs and source IDs if missing
    pissn = new_journal.get("issn_print")
    eissn = new_journal.get("issn_electronic")
    issn_l = new_journal.get("issn_l")
    nlm_id = new_journal.get("nlm_id")
    openalex_id = new_journal.get("openalex_id")

    if pissn and not existing.get("issn_print"):
        existing["issn_print"] = pissn
    if eissn and not existing.get("issn_electronic"):
        existing["issn_electronic"] = eissn
    if issn_l and not existing.get("issn_l"):
        existing["issn_l"] = issn_l
    if nlm_id and not existing.get("nlm_id"):
        existing["nlm_id"] = nlm_id
    if openalex_id and not existing.get("openalex_id"):
        existing["openalex_id"] = openalex_id

    # Wikidata ID (from OpenAlex)
    wikidata_id = new_journal.get("wikidata_id")
    if wikidata_id and not existing.get("wikidata_id"):
        existing["wikidata_id"] = wikidata_id

    # Collect all ISSNs into all_issns for comprehensive lookup
    all_issns_list = existing.get("all_issns", [])
    for issn_field in ["issn_l", "issn_print", "issn_electronic"]:
        issn = new_journal.get(issn_field)
        if issn and issn not in all_issns_list:
            all_issns_list.append(issn)
    existing["all_issns"] = all_issns_list


def normalize_title_key(title: str | None) -> str | None:
    """
    Create a normalized title key for deduplication.

    More aggressive normalization than normalize_title() - removes all
    punctuation and converts to lowercase for matching.

    Also strips trailing parenthetical suffixes like "(En ligne)", "(Online)",
    "(Print)", etc. which indicate format variants of the same journal.
    """
    if not title:
        return None

    # First apply standard normalization
    title = normalize_title(title)
    if not title:
        return None

    # Strip trailing parenthetical suffixes (format indicators)
    # Common patterns: (En ligne), (Online), (Print), (Electronic), (CD-ROM)
    title = re.sub(r"\s*\([^)]*\)\s*$", "", title)

    # Further normalize for matching: lowercase, remove punctuation
    key = title.lower()
    # Remove common punctuation and extra spaces
    for char in ".,;:!?'\"()-&/":
        key = key.replace(char, " ")
    # Collapse multiple spaces
    key = " ".join(key.split())

    return key if key else None


def make_title_identifier(title: str) -> str:
    """
    Create a synthetic identifier from a title using a hash.

    Args:
        title: Journal title (should be normalized)

    Returns:
        Synthetic identifier like 'TITLE-a1b2c3d4'
    """
    # Use first 8 chars of MD5 hash for brevity while maintaining uniqueness
    title_hash = hashlib.md5(title.encode("utf-8")).hexdigest()[:8]
    return f"TITLE-{title_hash}"


def unify_journals(
    all_journals: list[JournalDict],
    issn_l_map: dict[str, str],
    source_priority: Optional[dict[DataSource, int]] = None,
    output_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Unify journal data from all sources.

    Deduplication strategy:
    1. Phase 1 (Key Resolution): Build ISSN → canonical key mapping to ensure
       no duplicate ISSNs in the output
    2. Phase 2 (ISSN-based merge): Use resolved canonical keys to merge records
    3. Phase 3 (Title-based merge): For records without ISSN, merge by normalized title
    4. Phase 4 (Synthetic IDs): Assign synthetic identifiers (NLM-xxx, ISBN-xxx,
       OPENALEX-xxx, or TITLE-xxx) to records without ISSN-L

    Args:
        all_journals: List of journal dicts from all sources
        issn_l_map: Mapping from ISSN to ISSN-L
        source_priority: Optional dict mapping DataSource to priority (higher = preferred)
        output_dir: Optional directory for writing conflict reports

    Returns:
        DataFrame with unified journal records
    """
    logger.info("Unifying journal data...")

    if source_priority is None:
        source_priority = DEFAULT_SOURCE_PRIORITY

    # Separate journals with and without ISSN
    journals_with_issn = []
    journals_without_issn = []

    for journal in all_journals:
        has_issn = journal.get("issn_l") or journal.get("issn_print") or journal.get("issn_electronic")
        if has_issn:
            journals_with_issn.append(journal)
        else:
            journals_without_issn.append(journal)

    logger.info(f"  {len(journals_with_issn):,} journals with ISSN, {len(journals_without_issn):,} without")

    # ========== Phase 1: Key Resolution ==========
    # Build ISSN → canonical key mapping to ensure no duplicate ISSNs
    resolver = KeyResolver(issn_l_map)
    for journal in journals_with_issn:
        resolver.register(journal)
    resolver.log_stats()

    # Export ISSN reuse conflicts if output_dir provided
    issn_reuse_conflicts = resolver.get_issn_reuse_conflicts()
    if issn_reuse_conflicts and output_dir:
        conflicts_file = output_dir / "issn_reuse_conflicts.csv"
        with open(conflicts_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "issn",
                    "existing_key",
                    "existing_nlm_id",
                    "new_nlm_id",
                    "new_title",
                ],
            )
            writer.writeheader()
            writer.writerows(issn_reuse_conflicts)
        logger.info(f"  Wrote {len(issn_reuse_conflicts)} ISSN reuse conflicts to: {conflicts_file}")

    # ========== Phase 2: ISSN-based merging ==========
    unified: dict[str, JournalDict] = {}

    for journal in tqdm(journals_with_issn, desc="Merging (ISSN)"):
        # Use resolver to get consistent canonical key
        primary_key = resolver.get_canonical_key(journal)
        if not primary_key:
            continue

        source = journal.get("source", "unknown")
        new_priority = source_priority.get(source, 0)

        if primary_key in unified:
            # Merge with existing record
            existing = unified[primary_key]
            merge_journal_records(existing, journal, source, new_priority, source_priority)
        else:
            # Create new record and set unified_id to the canonical key
            record = create_unified_record(journal, source)
            record["unified_id"] = primary_key
            unified[primary_key] = record

    logger.info(f"  Phase 2: {len(unified):,} records from ISSN-based merge")

    # ========== Phase 3: Title-based merging for records without ISSN ==========
    # Build title index from existing unified records for matching
    title_to_key: dict[str, str] = {}
    for key, record in unified.items():
        title_key = normalize_title_key(record.get("title"))
        if title_key:
            title_to_key[title_key] = key

        # Also index alternative titles
        for alt_title in record.get("alternative_titles") or []:
            alt_key = normalize_title_key(alt_title)
            if alt_key and alt_key not in title_to_key:
                title_to_key[alt_key] = key

    # Process journals without ISSN
    merged_by_title = 0
    new_no_issn = 0
    title_unified: dict[str, JournalDict] = {}  # For new records without ISSN

    for journal in tqdm(journals_without_issn, desc="Merging (title)"):
        title = journal.get("title")
        title_key = normalize_title_key(title)

        if not title_key:
            continue  # Skip records without title

        source = journal.get("source", "unknown")
        new_priority = source_priority.get(source, 0)

        # Try to match with existing ISSN-based record
        if title_key in title_to_key:
            issn_key = title_to_key[title_key]
            existing = unified[issn_key]
            merge_journal_records(existing, journal, source, new_priority, source_priority)
            merged_by_title += 1
        elif title_key in title_unified:
            # Merge with existing title-based record
            existing = title_unified[title_key]
            merge_journal_records(existing, journal, source, new_priority, source_priority)
        else:
            # Create new title-based record
            title_unified[title_key] = create_unified_record(journal, source)
            new_no_issn += 1

    logger.info(f"  Phase 3: {merged_by_title:,} merged by title, {new_no_issn:,} new records without ISSN")

    # ========== Phase 4: Assign synthetic IDs to records without ISSN-L ==========
    synthetic_nlm = 0
    synthetic_isbn = 0
    synthetic_openalex = 0
    synthetic_title = 0

    for title_key, record in title_unified.items():
        # Skip if already has ISSN-L (shouldn't happen but be safe)
        if record.get("issn_l"):
            record["unified_id"] = record["issn_l"]
            continue

        # Prefer NLM ID > ISBN (from medline_abbreviation) > OpenAlex ID > title hash
        nlm_id = record.get("nlm_id")
        medline_ta = record.get("medline_abbreviation")
        openalex_id = record.get("openalex_id")
        title = record.get("title")

        if nlm_id:
            synthetic_id = make_nlm_identifier(nlm_id)
            record["unified_id"] = synthetic_id
            synthetic_nlm += 1
        elif medline_ta and is_isbn(medline_ta):
            synthetic_id = make_isbn_identifier(medline_ta)
            record["unified_id"] = synthetic_id
            synthetic_isbn += 1
        elif openalex_id:
            synthetic_id = make_openalex_identifier(openalex_id)
            record["unified_id"] = synthetic_id
            synthetic_openalex += 1
        elif title:
            # Generate title-based identifier
            synthetic_id = make_title_identifier(title)
            record["unified_id"] = synthetic_id
            synthetic_title += 1

    logger.info(
        f"  Phase 4: Assigned {synthetic_nlm:,} NLM, {synthetic_isbn:,} ISBN, {synthetic_openalex:,} OpenAlex, {synthetic_title:,} title-based synthetic IDs"
    )

    # Merge title-based records into unified (keyed by unified_id)
    for record in title_unified.values():
        key = record.get("unified_id") or record.get("issn_l")
        if key:
            unified[key] = record

    total_records = len(unified)
    logger.info(f"Unified into {total_records:,} unique journal records")

    # Convert to DataFrame using serialize_journal
    records = [serialize_journal(record) for record in unified.values()]
    df = pd.DataFrame(records)

    # Sort by ISSN-L, then print ISSN
    df = df.sort_values(
        by=["issn_l", "issn_print", "issn_electronic"],
        na_position="last",
    )

    return df
