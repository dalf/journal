"""Crossref REST API journal loader."""

import json
import logging
from pathlib import Path
from typing import Optional

from ..models import DataSource, JournalDict
from ..normalizers import normalize_issn, normalize_publisher, normalize_title
from .utils import deduplicate_journals

logger = logging.getLogger(__name__)


def _extract_issns(item: dict) -> tuple[Optional[str], Optional[str]]:
    """
    Extract print and electronic ISSNs from Crossref API response.

    The API provides:
    - ISSN: list of all ISSNs
    - issn-type: list of {type: "print"|"electronic", value: "XXXX-XXXX"}
    """
    issn_print = None
    issn_electronic = None

    issn_types = item.get("issn-type", [])
    for issn_info in issn_types:
        issn_type = issn_info.get("type")
        issn_value = issn_info.get("value")
        if not issn_value:
            continue

        normalized = normalize_issn(issn_value)
        if not normalized:
            continue

        if issn_type == "print" and not issn_print:
            issn_print = normalized
        elif issn_type == "electronic" and not issn_electronic:
            issn_electronic = normalized

    # Fallback: if no issn-type info, try to use ISSN list
    if not issn_print and not issn_electronic:
        issns = item.get("ISSN", [])
        for issn_value in issns:
            normalized = normalize_issn(issn_value)
            if normalized:
                if not issn_print:
                    issn_print = normalized
                elif not issn_electronic:
                    issn_electronic = normalized
                    break

    return issn_print, issn_electronic


def process_crossref_item(item: dict) -> Optional[JournalDict]:
    """
    Transform a Crossref API journal item into a JournalDict.

    Args:
        item: Journal object from Crossref REST API

    Returns:
        JournalDict or None if no valid ISSN
    """
    # Extract ISSNs
    issn_print, issn_electronic = _extract_issns(item)

    # Skip journals without any ISSN
    if not issn_print and not issn_electronic:
        return None

    journal: JournalDict = {
        "source": DataSource.CROSSREF,
    }

    # ISSNs
    if issn_print:
        journal["issn_print"] = issn_print
    if issn_electronic:
        journal["issn_electronic"] = issn_electronic

    # Title
    title = item.get("title")
    if title:
        journal["title"] = normalize_title(title)

    # Publisher
    publisher = item.get("publisher")
    if publisher:
        journal["publisher"] = normalize_publisher(publisher)

    # Subjects (often empty in Crossref)
    subjects = item.get("subjects", [])
    if subjects:
        # Subjects come as list of {name: ..., ASJC: ...} objects
        subject_names = []
        for subj in subjects:
            if isinstance(subj, dict):
                name = subj.get("name")
                if name:
                    subject_names.append(name)
            elif isinstance(subj, str):
                subject_names.append(subj)
        if subject_names:
            journal["subjects"] = subject_names

    return journal


def load_crossref_data(input_dir: Path) -> list[JournalDict]:
    """
    Load Crossref journal data from REST API JSON.

    See: https://api.crossref.org/
    License: Public Domain (metadata is factual, not copyrightable)
    """
    journals = []
    json_path = input_dir / "crossref" / "journals.json"

    if not json_path.exists():
        logger.warning("Crossref data not found, skipping...")
        return journals

    logger.info(f"Loading Crossref data from: {json_path}")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            items = json.load(f)

        logger.info(f"  Read {len(items):,} journals from JSON")

        # Process each item
        valid_count = 0
        for item in items:
            journal = process_crossref_item(item)
            if journal:
                journals.append(journal)
                valid_count += 1

        logger.info(f"  {valid_count:,} journals have valid ISSNs")
        logger.info(f"Loaded {len(journals):,} journals from Crossref")

    except Exception as e:
        logger.error(f"Error loading Crossref data: {e}")
        import traceback

        logger.debug(traceback.format_exc())

    # Deduplicate within source
    journals = deduplicate_journals(journals, "Crossref")
    return journals
