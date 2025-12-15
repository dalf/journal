"""Wikidata SPARQL journal loader.

Loads journal metadata from Wikidata using a SPARQL query that specifically
targets journals WITHOUT IDs from major sources. This fills gaps in coverage
from the major aggregated sources.

The SPARQL query filters for:
- Items of type Q5633421 (periodical literature)
- Has ISSN-L (P7363)
- Does NOT have NLM Unique ID (P1055)
- Does NOT have OpenAlex ID (P10283)
- Does NOT have Crossref journal ID (P8375)

This ensures we only add journals that aren't already well-covered by
NLM/MEDLINE, OpenAlex, or Crossref sources.

Source: https://query.wikidata.org/
"""

import json
import logging
from collections import defaultdict
from pathlib import Path

from ..models import DataSource, JournalDict
from ..normalizers import normalize_issn, normalize_publisher, normalize_title
from .utils import deduplicate_journals

logger = logging.getLogger(__name__)


def process_wikidata_results(results: list[dict]) -> list[JournalDict]:
    """
    Process SPARQL query results into JournalDict entries.

    Results are grouped by Wikidata item (QID) since one journal
    can have multiple ISSNs and appear in multiple rows.

    Args:
        results: List of SPARQL result bindings

    Returns:
        List of JournalDict records
    """
    # Group results by Wikidata item
    # Track English title separately to ensure language preference
    items: dict[str, dict] = defaultdict(
        lambda: {
            "issn_l": None,
            "title_en": None,  # English title (preferred)
            "title_other": None,  # Non-English fallback
            "publisher": None,
            "country": None,
            "wikidata_id": None,
        }
    )

    for row in results:
        # Extract Wikidata QID from URI
        item_uri = row.get("item", {}).get("value", "")
        if not item_uri:
            continue

        # Extract QID (e.g., "http://www.wikidata.org/entity/Q635808" -> "Q635808")
        qid = item_uri.split("/")[-1] if "/" in item_uri else None
        if not qid:
            continue

        item = items[qid]
        item["wikidata_id"] = qid

        # ISSN-L (required by query)
        issn_l = row.get("issnl", {}).get("value")
        if issn_l:
            item["issn_l"] = normalize_issn(issn_l, validate_checksum=False)

        # Note: Wikidata P236 (ISSN) doesn't distinguish print vs electronic,
        # so we don't collect individual ISSNs - only ISSN-L is reliable

        # Title - track English and non-English separately for proper fallback
        title_data = row.get("itemLabel", {})
        title = title_data.get("value")
        if title:
            lang = title_data.get("xml:lang", "")
            if lang == "en":
                if not item["title_en"]:
                    item["title_en"] = normalize_title(title)
            else:
                if not item["title_other"]:
                    item["title_other"] = normalize_title(title)

        # Publisher (English only)
        publisher = row.get("publisherLabel", {}).get("value")
        if publisher and not item["publisher"]:
            item["publisher"] = normalize_publisher(publisher)

        # Country code (ISO 3166-1 alpha-2)
        country = row.get("countryCode2", {}).get("value")
        if country and not item["country"]:
            item["country"] = country.upper()

    # Convert grouped items to JournalDict
    journals = []
    for qid, item in items.items():
        issn_l = item["issn_l"]
        if not issn_l:
            continue  # Skip items without ISSN-L

        # Wikidata P236 (ISSN) doesn't distinguish print vs electronic
        # Don't guess - leave as None and let merger fill from other sources
        # Use English title if available, otherwise fall back to other language
        title = item["title_en"] or item["title_other"]

        journal = JournalDict(
            title=title,
            publisher=item["publisher"],
            issn_print=None,
            issn_electronic=None,
            issn_l=issn_l,
            wikidata_id=qid,
            country=item["country"],
            source=DataSource.WIKIDATA,
        )
        journals.append(journal)

    return journals


def load_wikidata_data(input_dir: Path) -> list[JournalDict]:
    """
    Load Wikidata journal data from SPARQL query results.

    The query specifically targets journals that don't have NLM or OpenAlex IDs,
    making this a gap-filling source for journals not covered elsewhere.

    Args:
        input_dir: Directory containing wikidata/sparql_results.json

    Returns:
        List of JournalDict records
    """
    wikidata_dir = input_dir / "wikidata"
    json_path = wikidata_dir / "sparql_results.json"

    if not json_path.exists():
        logger.warning(f"Wikidata data not found at {json_path}, skipping...")
        return []

    logger.info(f"Loading Wikidata data from: {json_path}")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Wikidata JSON: {e}")
        return []

    results = data.get("results", {}).get("bindings", [])
    if not results:
        logger.warning("No results found in Wikidata SPARQL response")
        return []

    logger.info(f"  Processing {len(results):,} SPARQL result rows...")

    journals = process_wikidata_results(results)
    logger.info(f"  Grouped into {len(journals):,} unique journals")

    # Deduplicate within source
    journals = deduplicate_journals(journals, "Wikidata")

    logger.info(f"Loaded {len(journals):,} journals from Wikidata")
    return journals
