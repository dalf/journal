"""OpenAlex sources loader."""

import gzip
import json
import logging
from pathlib import Path
from typing import Optional

from tqdm import tqdm

from ..models import DataSource, JournalDict
from ..normalizers import normalize_country, normalize_issn, normalize_publisher, normalize_title
from .utils import deduplicate_journals

logger = logging.getLogger(__name__)


def process_openalex_record(source: dict, include_no_issn: bool = True) -> Optional[JournalDict]:
    """
    Process a single OpenAlex source record into normalized journal dict.

    Extracts this into a separate function to:
    1. Make testing easier (pure function)
    2. Enable memory-efficient batch processing
    3. Improve code organization

    Args:
        source: Raw OpenAlex source record (parsed JSON)
        include_no_issn: If True, include records without ISSN (using OpenAlex ID)

    Returns:
        Normalized journal dict, or None if record should be skipped
    """
    # Extract OpenAlex ID (e.g., "https://openalex.org/S4306530189" -> "S4306530189")
    openalex_id = source.get("id")
    if openalex_id and openalex_id.startswith("https://openalex.org/"):
        openalex_id = openalex_id.replace("https://openalex.org/", "")

    # Get ISSN information
    issn_l = normalize_issn(source.get("issn_l"), validate_checksum=False)
    issns = source.get("issn", []) or []

    # Normalize all ISSNs
    normalized_issns = []
    for issn in issns:
        norm = normalize_issn(issn, validate_checksum=False)
        if norm:
            normalized_issns.append(norm)

    # Skip records without ISSN unless include_no_issn is True
    if not normalized_issns and not issn_l:
        if not include_no_issn:
            return None
        # For records without ISSN, we need at least a title
        if not source.get("display_name"):
            return None

    # OpenAlex doesn't distinguish print vs electronic
    # Use ISSN-L as primary, others as secondary
    pissn = None
    eissn = None

    for issn in normalized_issns:
        if issn == issn_l:
            continue  # Skip ISSN-L, handle separately
        if not pissn:
            pissn = issn
        elif not eissn:
            eissn = issn

    # If no distinct ISSNs, use ISSN-L as print
    if not pissn:
        pissn = issn_l

    # Extract Wikidata ID from ids object (e.g., "https://www.wikidata.org/entity/Q180445" -> "Q180445")
    wikidata_id = None
    ids_obj = source.get("ids") or {}
    wikidata_url = ids_obj.get("wikidata")
    if wikidata_url and isinstance(wikidata_url, str):
        # Extract QID from URL
        if wikidata_url.startswith("https://www.wikidata.org/entity/"):
            wikidata_id = wikidata_url.replace("https://www.wikidata.org/entity/", "")

    journal = {
        "title": normalize_title(source.get("display_name")),
        "publisher": normalize_publisher(source.get("host_organization_name")),
        "issn_print": pissn,
        "issn_electronic": eissn,
        "issn_l": issn_l,
        "openalex_id": openalex_id,
        "wikidata_id": wikidata_id,
        "country": normalize_country(source.get("country_code")),
        "source": DataSource.OPENALEX,
    }

    # HIGH PRIORITY: Homepage URL
    homepage_url = source.get("homepage_url")
    if homepage_url:
        journal["journal_url"] = homepage_url

    # Additional fields from OpenAlex
    # Abbreviated title (from ISSN Centre) and alternate titles
    alternative_titles = []

    # Add abbreviated title first (standard abbreviation for citations)
    abbreviated_title = source.get("abbreviated_title")
    if abbreviated_title:
        alternative_titles.append(abbreviated_title.strip())

    # Add other alternate titles
    alt_titles = source.get("alternate_titles") or []
    for t in alt_titles:
        if t:
            normalized = normalize_title(t)
            if normalized and normalized not in alternative_titles:
                alternative_titles.append(normalized)

    if alternative_titles:
        journal["alternative_titles"] = alternative_titles

    # Host organization lineage (other organisations)
    lineage = source.get("host_organization_lineage_names") or []
    if lineage:
        # Filter out the main publisher name
        main_publisher = source.get("host_organization_name")
        other_orgs = [normalize_publisher(org) for org in lineage if org and org != main_publisher]
        if other_orgs:
            journal["other_organisations"] = other_orgs

    # Source type (journal, repository, conference, etc.)
    source_type = source.get("type")
    if source_type:
        journal["source_type"] = source_type.lower()

    # Open access status
    is_oa = source.get("is_oa")
    if is_oa is not None:
        journal["is_oa"] = is_oa

    # APC (Article Processing Charge) - OpenAlex provides in USD
    apc_usd = source.get("apc_usd")
    if apc_usd is not None:
        try:
            journal["apc_amount"] = float(apc_usd)
            journal["apc_currency"] = "USD"
        except (ValueError, TypeError):
            pass

    # HIGH PRIORITY: Metrics
    works_count = source.get("works_count")
    if works_count is not None:
        try:
            journal["works_count"] = int(works_count)
        except (ValueError, TypeError):
            pass

    cited_by_count = source.get("cited_by_count")
    if cited_by_count is not None:
        try:
            journal["cited_by_count"] = int(cited_by_count)
        except (ValueError, TypeError):
            pass

    # MEDIUM PRIORITY: h-index from summary_stats
    summary_stats = source.get("summary_stats") or {}
    h_index = summary_stats.get("h_index")
    if h_index is not None:
        try:
            journal["h_index"] = int(h_index)
        except (ValueError, TypeError):
            pass

    # Subjects/topics from OpenAlex (using topics instead of deprecated x_concepts)
    topics = source.get("topics") or []
    if topics:
        # Get topics with high relevance (score > 0.5 on 0-1 scale)
        relevant = [t for t in topics if t.get("score", 0) > 0.5]

        if relevant:
            # Extract hierarchy from top topic
            top = relevant[0]
            domain = top.get("domain", {}).get("display_name")
            field = top.get("field", {}).get("display_name")
            subfield = top.get("subfield", {}).get("display_name")

            if domain:
                journal["subject_domain"] = domain
            if field:
                journal["subject_field"] = field
            if subfield:
                journal["subject_subfield"] = subfield

            # Collect all topic names
            topic_names = [t.get("display_name") for t in relevant[:10] if t.get("display_name")]
            if topic_names:
                journal["subjects"] = topic_names

    return journal


def load_openalex_data(input_dir: Path, include_no_issn: bool = True) -> list[JournalDict]:
    """
    Load OpenAlex sources data (JSONL.gz files).

    Args:
        input_dir: Directory containing OpenAlex data
        include_no_issn: If True, include records without ISSN (using OpenAlex ID)

    Returns:
        List of normalized journal dictionaries
    """
    all_journals = []
    openalex_dir = input_dir / "openalex"

    if not openalex_dir.exists():
        logger.warning("OpenAlex data not found, skipping...")
        return all_journals

    # Find all gzipped JSONL files (recursive for nested structure)
    gz_files = list(openalex_dir.glob("**/*.gz"))

    if not gz_files:
        logger.warning("No OpenAlex .gz files found, skipping...")
        return all_journals

    logger.info(f"Loading OpenAlex data from {len(gz_files)} files...")

    total_with_issn = 0
    total_without_issn = 0
    total_skipped = 0

    for gz_path in tqdm(gz_files, desc="OpenAlex files"):
        try:
            with gzip.open(gz_path, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        source = json.loads(line.strip())
                        journal = process_openalex_record(source, include_no_issn=include_no_issn)

                        if journal:
                            all_journals.append(journal)
                            # Track whether record has ISSN
                            if journal.get("issn_l") or journal.get("issn_print") or journal.get("issn_electronic"):
                                total_with_issn += 1
                            else:
                                total_without_issn += 1
                        else:
                            total_skipped += 1

                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON decode error in {gz_path.name}: {e}")
                        total_skipped += 1
                        continue

        except Exception as e:
            logger.error(f"Error processing {gz_path}: {e}")
            continue

    total_processed = total_with_issn + total_without_issn
    logger.info(f"  Processed {total_processed:,} records ({total_with_issn:,} with ISSN, {total_without_issn:,} without), skipped {total_skipped:,}")

    # Deduplicate within source
    all_journals = deduplicate_journals(all_journals, "OpenAlex")

    logger.info(f"Loaded {len(all_journals):,} sources from OpenAlex")
    return all_journals
