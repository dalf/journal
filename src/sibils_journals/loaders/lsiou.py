"""LSIOU (List of Serials Indexed for Online Users) loader.

LSIOU is NLM's comprehensive list of all journals ever indexed for MEDLINE,
including currently indexed, historical, and ceased titles.

Key advantages over J_Entrez.txt:
- Native ISSN-L (ISSNLinking) field
- Structured XML format with rich metadata
- Includes indexing status and dates
- 15,473 titles (2024 edition) curated specifically for MEDLINE

XML Structure (based on NLMCatalogRecordSet DTD):
- NlmUniqueID: Unique NLM identifier
- TitleMain: Primary journal title
- MedlineTA: Official MEDLINE title abbreviation
- ISSN: Print/Electronic ISSNs with IssnType attribute
- ISSNLinking: Linking ISSN
- Language: Publication language(s)
- Country: Country of publication
- IndexingSourceList: Indexing status information

See: https://www.nlm.nih.gov/tsd/serials/lsiou.html
See: https://www.nlm.nih.gov/bsd/licensee/catrecordxml_element_desc2.html
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from ..config import LSIOU_FILENAME
from ..models import DataSource, JournalDict
from ..normalizers import normalize_country, normalize_issn, normalize_language, normalize_title
from .utils import deduplicate_journals

logger = logging.getLogger(__name__)


def parse_lsiou_record(record: ET.Element) -> Optional[JournalDict]:
    """
    Parse a single Serial element from LSIOU XML.

    LSIOU uses the NLM Serials DTD with <Serial> elements containing:
    - NlmUniqueID: Unique identifier
    - Title: Full journal title
    - MedlineTA: MEDLINE title abbreviation
    - ISSN: With IssnType attribute (Print/Electronic)
    - ISSNLinking: Linking ISSN
    - CurrentlyIndexedYN: Y/N for current MEDLINE indexing
    - PublicationInfo/Country: Country of publication
    - Language: Publication language(s)
    - CrossReferenceList: Alternative titles

    Args:
        record: XML Element representing a single Serial record

    Returns:
        JournalDict or None if record is invalid
    """
    # Get NLM unique identifier
    nlm_id_elem = record.find("NlmUniqueID")
    nlm_id = nlm_id_elem.text.strip() if nlm_id_elem is not None and nlm_id_elem.text else None

    # Get title (direct child, not nested under TitleMain)
    title_elem = record.find("Title")
    title = normalize_title(title_elem.text) if title_elem is not None and title_elem.text else None

    if not title:
        return None

    # Get ISSNs
    issn_print = None
    issn_electronic = None

    for issn_elem in record.findall("ISSN"):
        issn_type = issn_elem.get("IssnType", "").lower()
        issn_value = normalize_issn(issn_elem.text, validate_checksum=False) if issn_elem.text else None

        if issn_value:
            if issn_type == "print":
                issn_print = issn_value
            elif issn_type == "electronic":
                issn_electronic = issn_value
            elif issn_type == "undetermined" and not issn_print:
                # Default to print if undetermined
                issn_print = issn_value

    # Get ISSN-L (ISSNLinking)
    issn_l_elem = record.find("ISSNLinking")
    issn_l = normalize_issn(issn_l_elem.text, validate_checksum=False) if issn_l_elem is not None and issn_l_elem.text else None

    # Must have at least one identifier (ISSN or NLM ID)
    has_issn = issn_print or issn_electronic or issn_l
    if not has_issn and not nlm_id:
        return None

    # Get MEDLINE abbreviation (MedlineTA)
    medline_ta_elem = record.find("MedlineTA")
    medline_abbreviation = medline_ta_elem.text.strip() if medline_ta_elem is not None and medline_ta_elem.text else None

    # Get alternative titles from CrossReferenceList
    alternative_titles = []

    for cross_ref in record.findall(".//CrossReference/XrTitle"):
        if cross_ref.text:
            alt_text = cross_ref.text.strip()
            # Skip if same as main title or MEDLINE abbreviation
            if alt_text and alt_text != title and alt_text != medline_abbreviation:
                # Clean up trailing periods
                if alt_text.endswith("."):
                    alt_text = alt_text[:-1]
                if alt_text and alt_text not in alternative_titles:
                    alternative_titles.append(alt_text)

    # Get country from PublicationInfo
    country = None
    pub_info = record.find("PublicationInfo")
    if pub_info is not None:
        country_elem = pub_info.find("Country")
        if country_elem is not None and country_elem.text:
            country = normalize_country(country_elem.text.strip())

    # Get languages
    languages = []
    for lang_elem in record.findall("Language"):
        if lang_elem.text:
            # NLM uses 3-letter language codes (e.g., "eng"), normalize to ISO 639-1
            lang_codes = normalize_language(lang_elem.text.strip())
            for lang in lang_codes:
                if lang and lang not in languages:
                    languages.append(lang)

    # Determine MEDLINE indexing status from CurrentlyIndexedYN element
    is_medline_indexed = False
    currently_indexed_elem = record.find("CurrentlyIndexedYN")
    if currently_indexed_elem is not None and currently_indexed_elem.text:
        is_medline_indexed = currently_indexed_elem.text.strip().upper() == "Y"

    # Extract journal relationships from TitleRelated elements
    # Types: Preceding, Succeeding, MergerOf, SupersedesInPart, etc.
    predecessor_nlm_ids = []
    successor_nlm_ids = []

    for title_related in record.findall("TitleRelated"):
        title_type = title_related.get("TitleType", "")

        # Find NLM ID in RecordID elements
        related_nlm_id = None
        for record_id in title_related.findall("RecordID"):
            if record_id.get("Source") == "NLM" and record_id.text:
                related_nlm_id = record_id.text.strip()
                break

        if related_nlm_id:
            if title_type == "Preceding":
                # This journal continues from the related journal
                if related_nlm_id not in predecessor_nlm_ids:
                    predecessor_nlm_ids.append(related_nlm_id)
            elif title_type == "Succeeding":
                # This journal is continued by the related journal
                if related_nlm_id not in successor_nlm_ids:
                    successor_nlm_ids.append(related_nlm_id)
            # MergerOf, SupersedesInPart, etc. - treat as predecessors
            elif title_type in ("MergerOf", "SupersedesInPart", "Supersedes"):
                if related_nlm_id not in predecessor_nlm_ids:
                    predecessor_nlm_ids.append(related_nlm_id)
            elif title_type in ("SupersededBy", "AbsorbedBy", "MergedWith"):
                if related_nlm_id not in successor_nlm_ids:
                    successor_nlm_ids.append(related_nlm_id)

    # Build journal dict
    journal: JournalDict = {
        "title": title,
        "issn_print": issn_print,
        "issn_electronic": issn_electronic,
        "source": DataSource.LSIOU,
    }

    if issn_l:
        journal["issn_l"] = issn_l

    if nlm_id:
        journal["nlm_id"] = nlm_id

    if medline_abbreviation:
        journal["medline_abbreviation"] = medline_abbreviation

    if alternative_titles:
        journal["alternative_titles"] = alternative_titles

    if country:
        journal["country"] = country

    if languages:
        journal["language"] = languages

    journal["is_medline_indexed"] = is_medline_indexed

    # Add journal relationships
    if predecessor_nlm_ids:
        journal["predecessor_nlm_ids"] = predecessor_nlm_ids

    if successor_nlm_ids:
        journal["successor_nlm_ids"] = successor_nlm_ids

    return journal


def load_lsiou_data(input_dir: Path, include_no_issn: bool = True) -> list[JournalDict]:
    """
    Load LSIOU (List of Serials Indexed for Online Users) XML data.

    LSIOU contains all journals ever indexed for MEDLINE, including:
    - Currently indexed journals (~5,294)
    - Historical/ceased titles (~10,000)
    - Title changes and renamed journals

    This is the most authoritative source for MEDLINE journal metadata,
    with native ISSN-L support and comprehensive historical coverage.

    Args:
        input_dir: Directory containing LSIOU data (expects lsiou/lsi2025.xml)
        include_no_issn: Include journals without ISSN (using NLM ID as identifier)

    Returns:
        List of normalized journal dictionaries
    """
    journals = []
    lsiou_path = input_dir / "lsiou" / LSIOU_FILENAME

    if not lsiou_path.exists():
        logger.warning(f"LSIOU data not found at {lsiou_path}, skipping...")
        logger.info("  Download with: sibils-journals download --sources lsiou")
        return journals

    logger.info(f"Loading LSIOU data from: {lsiou_path}")

    if include_no_issn:
        logger.info("  Including journals without ISSN (using NLM ID as identifier)")

    try:
        # Parse XML
        tree = ET.parse(lsiou_path)
        root = tree.getroot()

        # LSIOU uses <SerialsSet> as root with <Serial> child elements
        records = root.findall("Serial")
        if not records:
            # Fallback: try to find Serial elements anywhere
            records = root.findall(".//Serial")
        if not records:
            # Last resort: try direct children
            records = list(root)

        parsed = 0
        parsed_no_issn = 0
        parsed_indexed = 0
        skipped = 0

        for record in records:
            journal = parse_lsiou_record(record)

            if journal:
                has_issn = journal.get("issn_print") or journal.get("issn_electronic") or journal.get("issn_l")

                # Skip records without ISSN if not including them
                if not has_issn and not include_no_issn:
                    skipped += 1
                    continue

                journals.append(journal)
                parsed += 1

                if not has_issn:
                    parsed_no_issn += 1

                if journal.get("is_medline_indexed"):
                    parsed_indexed += 1
            else:
                skipped += 1

        logger.info(f"  Parsed {parsed:,} records ({parsed_no_issn:,} without ISSN, {parsed_indexed:,} currently indexed), skipped {skipped:,}")

    except ET.ParseError as e:
        logger.error(f"XML parsing error: {e}")
        import traceback

        logger.debug(traceback.format_exc())
    except Exception as e:
        logger.error(f"Error loading LSIOU data: {e}")
        import traceback

        logger.debug(traceback.format_exc())

    # Deduplicate within source
    journals = deduplicate_journals(journals, "LSIOU")

    logger.info(f"Loaded {len(journals):,} journals from LSIOU")
    return journals
