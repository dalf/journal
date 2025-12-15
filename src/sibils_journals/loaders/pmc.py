"""PMC (PubMed Central) journal list loader.

Loads the official PMC journal list from NCBI, which contains journals
with formal deposit agreements with PubMed Central.

Source: https://pmc.ncbi.nlm.nih.gov/journals/
Data: https://cdn.ncbi.nlm.nih.gov/pmc/home/jlist.csv

This is a lightweight alternative to the EuropePMC bulk metadata dump:
- jlist.csv: ~1.1 MB, ~4,400 journals with deposit agreements
- PMCLiteMetadata.tgz: ~1.5 GB, ~20,000 journals with any PMC content

The CSV provides richer metadata including publisher, embargo period,
and agreement status.

Agreement Status values:
- "Active": Currently depositing to PMC
- "No longer participating": Was participating, stopped
- "No longer published": Journal ceased publication
- "Predecessor title": Superseded by another journal
"""

import csv
import logging
import re
from pathlib import Path

from ..models import DataSource, JournalDict
from ..normalizers import normalize_issn, normalize_title
from .utils import deduplicate_journals

logger = logging.getLogger(__name__)

# Valid agreement status values
VALID_AGREEMENT_STATUSES = {
    "Active",
    "No longer participating",
    "No longer published",
    "Predecessor title",
}

# Pattern to extract year from "Most Recent" column (e.g., "v.16(1) 2026" -> 2026)
YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")

# Pattern to extract months from embargo (e.g., "12 months" -> 12)
EMBARGO_PATTERN = re.compile(r"^(\d+)\s*months?", re.IGNORECASE)


def _extract_year(value: str) -> int | None:
    """Extract a 4-digit year from a string like 'v.16(1) 2026'."""
    if not value:
        return None
    match = YEAR_PATTERN.search(value)
    if match:
        return int(match.group(0))
    return None


def _extract_embargo_months(value: str) -> int | None:
    """Extract embargo months from a string like '12 months' or '0 months (Immediate release)'."""
    if not value:
        return None
    match = EMBARGO_PATTERN.match(value.strip())
    if match:
        return int(match.group(1))
    return None


def process_pmc_record(row: dict) -> JournalDict | None:
    """
    Transform a PMC CSV row into a JournalDict.

    Args:
        row: Dictionary from CSV reader with PMC fields

    Returns:
        JournalDict with source metadata, or None if invalid
    """
    # Extract and normalize ISSNs
    issn_print = normalize_issn(row.get("ISSN (print)", "").strip(), validate_checksum=False)
    issn_electronic = normalize_issn(row.get("ISSN (online)", "").strip(), validate_checksum=False)

    # Skip records without any ISSN
    if not issn_print and not issn_electronic:
        return None

    # Extract and normalize title
    title = row.get("Journal Title", "").strip()
    title = normalize_title(title) if title else None

    # Extract publisher
    publisher = row.get("Publisher", "").strip() or None

    # Extract NLM ID
    nlm_id = row.get("NLM Unique ID", "").strip() or None

    # Extract agreement status
    agreement_status = row.get("Agreement Status", "").strip()
    pmc_agreement_status = agreement_status if agreement_status in VALID_AGREEMENT_STATUSES else None

    # Extract last deposit year from "Most Recent" column
    most_recent = row.get("Most Recent", "").strip()
    pmc_last_deposit_year = _extract_year(most_recent)

    # Extract embargo/release delay
    # Format: "12 months", "0 months (Immediate release)", etc.
    release_delay = row.get("Release Delay (Embargo)", "").strip()
    pmc_embargo_months = _extract_embargo_months(release_delay)
    is_immediate = pmc_embargo_months == 0

    return JournalDict(
        title=title,
        publisher=publisher,
        issn_print=issn_print,
        issn_electronic=issn_electronic,
        nlm_id=nlm_id,
        country=None,
        source=DataSource.PMC,
        is_pmc_indexed=True,
        pmc_agreement_status=pmc_agreement_status,
        pmc_last_deposit_year=pmc_last_deposit_year,
        pmc_embargo_months=pmc_embargo_months,
        # Store immediate release status in is_oa as a proxy
        # (journals with no embargo are effectively open access in PMC)
        is_oa=True if is_immediate else None,
    )


def load_pmc_data(input_dir: Path) -> list[JournalDict]:
    """
    Load PMC journal list from CSV file.

    The CSV contains journals with formal PMC deposit agreements,
    providing authoritative PMC indexing status.

    See: https://pmc.ncbi.nlm.nih.gov/journals/

    Args:
        input_dir: Directory containing pmc/jlist.csv

    Returns:
        List of JournalDict records
    """
    pmc_dir = input_dir / "pmc"
    csv_path = pmc_dir / "jlist.csv"

    if not csv_path.exists():
        logger.warning(f"PMC data not found at {csv_path}, skipping...")
        return []

    logger.info(f"Loading PMC data from: {csv_path}")

    journals = []
    skipped = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            journal = process_pmc_record(row)
            if journal:
                journals.append(journal)
            else:
                skipped += 1

    logger.info(f"  Loaded {len(journals):,} journals from PMC ({skipped} skipped without ISSN)")

    # Deduplicate within source
    journals = deduplicate_journals(journals, "PMC")

    return journals
