"""Extract unique journal fields from SIBiLS Elasticsearch indices.

This command extracts (journal, medline_ta, nlm_id) tuples from SIBiLS MEDLINE
and PMC indices for journal matching and validation purposes.

In PMC, some medline_ta values are numeric NLM IDs (for journals not in MEDLINE).
These are detected and stored in the nlm_id column.
"""

import argparse
import csv
import logging
import sys
from pathlib import Path

from elasticsearch import Elasticsearch
from tqdm import tqdm

from .config import DEFAULT_SIBILS_DIR, DEFAULT_SIBILS_VERSION, SIBILS_ES_URL

logger = logging.getLogger(__name__)


def find_index(es: Elasticsearch, pattern: str) -> str | None:
    """Find index matching pattern, return first match or None."""
    indices = es.indices.get(index=pattern, ignore_unavailable=True)
    if indices:
        return list(indices.keys())[0]
    return None


def extract_from_medline(es: Elasticsearch, index: str, batch_size: int = 10000) -> set[tuple[str, str, str]]:
    """Extract unique (journal, medline_ta, nlm_id) tuples from MEDLINE index.

    MEDLINE medline_ta values are always text abbreviations, so nlm_id is empty.
    """
    unique_tuples: set[tuple[str, str, str]] = set()

    resp = es.search(
        index=index,
        query={"match_all": {}},
        source=["journal", "medline_ta"],
        scroll="5m",
        size=batch_size,
    )

    scroll_id = resp["_scroll_id"]
    total = resp["hits"]["total"]["value"]

    with tqdm(total=total, desc=f"Scanning {index}", unit="docs") as pbar:
        while True:
            hits = resp["hits"]["hits"]
            if not hits:
                break

            for hit in hits:
                src = hit.get("_source", {})
                journal = src.get("journal", "")
                medline_ta = src.get("medline_ta", "")
                if journal or medline_ta:
                    # MEDLINE medline_ta is always a text abbreviation, nlm_id is empty
                    unique_tuples.add((journal or "", medline_ta or "", ""))

            pbar.update(len(hits))
            pbar.set_postfix(unique=len(unique_tuples))

            resp = es.scroll(scroll_id=scroll_id, scroll="5m")

    es.clear_scroll(scroll_id=scroll_id)
    return unique_tuples


def extract_from_pmc(es: Elasticsearch, index: str, batch_size: int = 10000) -> set[tuple[str, str, str]]:
    """Extract unique (journal, medline_ta, nlm_id) tuples from PMC index.

    PMC documents may have medline_ta values that are either:
    - Text abbreviations (same as MEDLINE) -> stored in medline_ta, nlm_id empty
    - Numeric NLM IDs (for journals not in MEDLINE) -> stored in nlm_id, medline_ta empty

    Note: PMC's medline_ta field is type 'text' (not 'keyword'), so we use
    scroll API like MEDLINE instead of composite aggregation.
    """
    unique_tuples: set[tuple[str, str, str]] = set()

    resp = es.search(
        index=index,
        query={"match_all": {}},
        source=["journal", "medline_ta"],
        scroll="5m",
        size=batch_size,
    )

    scroll_id = resp["_scroll_id"]
    total = resp["hits"]["total"]["value"]

    with tqdm(total=total, desc=f"Scanning {index}", unit="docs") as pbar:
        while True:
            hits = resp["hits"]["hits"]
            if not hits:
                break

            for hit in hits:
                src = hit.get("_source", {})
                journal = src.get("journal", "")
                raw_medline_ta = src.get("medline_ta", "")

                if journal or raw_medline_ta:
                    # Detect if medline_ta is actually a numeric NLM ID
                    if raw_medline_ta and raw_medline_ta.isdigit():
                        # Numeric value -> it's an NLM ID, not an abbreviation
                        unique_tuples.add((journal or "", "", raw_medline_ta))
                    else:
                        # Text abbreviation
                        unique_tuples.add((journal or "", raw_medline_ta or "", ""))

            pbar.update(len(hits))
            pbar.set_postfix(unique=len(unique_tuples))

            resp = es.scroll(scroll_id=scroll_id, scroll="5m")

    es.clear_scroll(scroll_id=scroll_id)
    return unique_tuples


def main() -> int:
    """Extract journal fields from SIBiLS indices."""
    parser = argparse.ArgumentParser(description="Extract journal fields from SIBiLS Elasticsearch indices")
    parser.add_argument(
        "--version",
        default=DEFAULT_SIBILS_VERSION,
        help=f"SIBiLS version (default: {DEFAULT_SIBILS_VERSION})",
    )
    parser.add_argument(
        "--source",
        choices=["medline", "pmc", "both"],
        default="both",
        help="Which index to extract from (default: both)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_SIBILS_DIR,
        help=f"Output directory (default: {DEFAULT_SIBILS_DIR})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10000,
        help="Batch size for scrolling (default: 10000)",
    )
    parser.add_argument(
        "--es-url",
        default=SIBILS_ES_URL,
        help=f"Elasticsearch URL (default: {SIBILS_ES_URL})",
    )
    args = parser.parse_args()

    with Elasticsearch(args.es_url, request_timeout=300) as es:
        if not es.ping():
            print(f"Cannot connect to Elasticsearch at {args.es_url}", file=sys.stderr)
            return 1

        print(f"Connected to {args.es_url}")

        # Find indices matching the version pattern
        medline_pattern = f"sibils_med*_v{args.version}"
        pmc_pattern = f"sibils_pmc*_v{args.version}"

        medline_index = find_index(es, medline_pattern)
        pmc_index = find_index(es, pmc_pattern)

        if args.source in ("medline", "both") and not medline_index:
            print(
                f"No MEDLINE index found matching pattern: {medline_pattern}",
                file=sys.stderr,
            )
            return 1

        if args.source in ("pmc", "both") and not pmc_index:
            print(f"No PMC index found matching pattern: {pmc_pattern}", file=sys.stderr)
            return 1

        print(f"Using indices: MEDLINE={medline_index}, PMC={pmc_index}")

        unique_tuples: set[tuple[str, str, str]] = set()

        if args.source in ("medline", "both"):
            unique_tuples.update(extract_from_medline(es, medline_index, args.batch_size))
            print(f"After MEDLINE: {len(unique_tuples):,} unique tuples")

        if args.source in ("pmc", "both"):
            unique_tuples.update(extract_from_pmc(es, pmc_index, args.batch_size))
            print(f"After PMC: {len(unique_tuples):,} unique tuples")

    # Count how many have nlm_id
    nlm_id_count = sum(1 for _, _, nlm_id in unique_tuples if nlm_id)
    print(f"Total: {len(unique_tuples):,} unique tuples ({nlm_id_count:,} with NLM ID)")

    # Create output directory if needed
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_file = args.output_dir / f"journal_fields_v{args.version}.csv"

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["journal", "medline_ta", "nlm_id"])
        for journal, medline_ta, nlm_id in sorted(unique_tuples):
            writer.writerow([journal, medline_ta, nlm_id])

    print(f"Wrote to '{output_file}'")
    return 0
