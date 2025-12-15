"""J-STAGE journal list loader.

J-STAGE (Japan Science and Technology Information Aggregator, Electronic)
is Japan's largest platform for academic e-journals, operated by the
Japan Science and Technology Agency (JST).

Source: https://www.jstage.jst.go.jp/
Data: https://www.jstage.jst.go.jp/pub/jnllist/journals_list_en.zip
Format: https://www.jstage.jst.go.jp/static/files/en/J-STAGE_Journal-List-Formats.pdf

The data file is tab-separated with the following key columns:
- CDJOURNAL: Journal code (unique identifier)
- JOURNALTITLE: English journal title
- PRINTISSN, ONLINEISSN, ISSN-L: ISSN identifiers
- ORGANIZATION: Publisher/society name
- URL: Journal website
- LANGUAGE: Publication language(s)
- PUBLICATION TYPE: Journal, Proceedings, etc.
- FREE: Open access status (FREE = open access)
"""

import csv
import logging
from pathlib import Path

from ..models import DataSource, JournalDict
from ..normalizers import normalize_issn, normalize_publisher, normalize_title
from .utils import deduplicate_journals

logger = logging.getLogger(__name__)


def _normalize_language(lang_str: str | None) -> list[str]:
    """
    Normalize J-STAGE language field to ISO 639-1 codes.

    J-STAGE uses formats like:
    - "Japanese"
    - "English"
    - "Japanese and English"
    - "English / Japanese etc."

    Returns:
        List of ISO 639-1 language codes
    """
    if not lang_str or not lang_str.strip():
        return []

    lang_str = lang_str.lower().strip()
    codes = []

    # Check for Japanese
    if "japanese" in lang_str:
        codes.append("ja")

    # Check for English
    if "english" in lang_str:
        codes.append("en")

    # If no recognized language, return empty
    return codes


def _normalize_source_type(pub_type: str | None) -> str | None:
    """
    Normalize J-STAGE publication type to lowercase.

    Types include: Journal, Proceedings, Research Report / Technical Report, Magazine
    """
    if not pub_type or not pub_type.strip():
        return None

    pub_type = pub_type.strip().lower()

    # Map to standardized types
    type_map = {
        "journal": "journal",
        "proceedings": "proceedings",
        "research report / technical report": "report",
        "magazine": "magazine",
        "other": "other",
    }

    return type_map.get(pub_type, pub_type)


def process_jstage_record(row: dict) -> JournalDict | None:
    """
    Transform a J-STAGE record into a JournalDict.

    Args:
        row: Dictionary from CSV reader with J-STAGE fields

    Returns:
        JournalDict with source metadata, or None if invalid
    """
    # Extract and normalize ISSNs
    issn_print = normalize_issn(row.get("PRINTISSN", "").strip(), validate_checksum=False)
    issn_electronic = normalize_issn(row.get("ONLINEISSN", "").strip(), validate_checksum=False)
    issn_l = normalize_issn(row.get("ISSN-L", "").strip(), validate_checksum=False)

    # Skip records without any ISSN
    if not issn_print and not issn_electronic and not issn_l:
        return None

    # Extract and normalize title
    title = row.get("JOURNALTITLE", "").strip()
    title = normalize_title(title) if title else None

    # Extract publisher (ORGANIZATION field)
    publisher = row.get("ORGANIZATION", "").strip()
    publisher = normalize_publisher(publisher) if publisher else None

    # Extract journal URL
    journal_url = row.get("URL", "").strip() or None

    # Normalize language
    language = _normalize_language(row.get("LANGUAGE"))

    # Normalize source type
    source_type = _normalize_source_type(row.get("PUBLICATION TYPE"))

    # Check if open access (FREE field)
    free_status = row.get("FREE", "").strip().upper()
    is_oa = free_status == "FREE"

    return JournalDict(
        title=title,
        publisher=publisher,
        issn_print=issn_print,
        issn_electronic=issn_electronic,
        issn_l=issn_l,
        country="JP",  # All J-STAGE journals are from Japan
        source=DataSource.JSTAGE,
        journal_url=journal_url,
        language=language if language else None,
        source_type=source_type,
        is_oa=is_oa if is_oa else None,  # Only set if True
    )


def load_jstage_data(input_dir: Path) -> list[JournalDict]:
    """
    Load J-STAGE journal list from TSV file.

    The file is a tab-separated values file with a header row.
    First line contains an UPDATE timestamp that should be skipped.

    Args:
        input_dir: Directory containing jstage/journals_list_en.txt

    Returns:
        List of JournalDict records
    """
    jstage_dir = input_dir / "jstage"
    tsv_path = jstage_dir / "journals_list_en.txt"

    if not tsv_path.exists():
        logger.warning(f"J-STAGE data not found at {tsv_path}, skipping...")
        return []

    logger.info(f"Loading J-STAGE data from: {tsv_path}")

    journals = []
    skipped = 0

    with open(tsv_path, "r", encoding="utf-8") as f:
        # Skip first line (UPDATE timestamp)
        first_line = f.readline()
        if not first_line.startswith("UPDATE:"):
            # If first line is not UPDATE, seek back to start
            f.seek(0)

        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            journal = process_jstage_record(row)
            if journal:
                journals.append(journal)
            else:
                skipped += 1

    logger.info(f"  Loaded {len(journals):,} journals from J-STAGE ({skipped} skipped without ISSN)")

    # Deduplicate within source
    journals = deduplicate_journals(journals, "J-STAGE")

    return journals
