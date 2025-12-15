"""Command-line interface for ISSN data unification."""

import argparse
import logging
from pathlib import Path

from . import config
from .exporters import export_csv, export_elasticsearch, export_summary_json
from .loaders import (
    load_crossref_data,
    load_doaj_data,
    load_issn_l_table,
    load_jstage_data,
    load_lsiou_data,
    load_nlm_data,
    load_openalex_data,
    load_pmc_data,
    load_wikidata_data,
)
from .merger import unify_journals
from .metrics import get_metrics, reset_metrics
from .config import DEFAULT_OUTPUT_DIR, DEFAULT_RAW_DIR
from .sibils_filter import apply_sibils_filter
from .stats import print_stats
from .validators import export_issn_conflicts, validate_issn_l_consistency

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="Unify ISSN data from multiple sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                        # Use default directories
  %(prog)s --output-file journals.csv             # Custom output filename
  %(prog)s --skip-checksum                        # Disable ISSN checksum validation
  %(prog)s --es-url http://localhost:9200         # Export to local Elasticsearch
  %(prog)s --es-url https://u:p@es.example.com:9200 --es-recreate  # With auth, recreate index
        """,
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help=f"Input directory with raw data (default: {DEFAULT_RAW_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for unified data (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="unified_issn.csv",
        help="Output filename (default: unified_issn.csv)",
    )
    parser.add_argument(
        "--skip-checksum",
        action="store_true",
        help="Skip ISSN checksum validation",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose/debug logging",
    )

    # SIBiLS filter options
    sibils_group = parser.add_argument_group("SIBiLS filtering")
    sibils_group.add_argument(
        "--sibils-filter",
        nargs="?",
        const=True,
        default=False,
        metavar="VERSION",
        help="Filter to keep only journals referenced in SIBiLS. Optionally specify version (e.g., 5.0.5.8)",
    )

    # Elasticsearch export options
    es_group = parser.add_argument_group("Elasticsearch export")
    es_group.add_argument(
        "--es-url",
        type=str,
        help="Elasticsearch URL (e.g., https://user:pass@localhost:9200). If provided, exports to ES.",
    )
    es_group.add_argument(
        "--es-index",
        type=str,
        default="journals",
        help="Elasticsearch index name (default: journals)",
    )
    es_group.add_argument(
        "--es-api-key",
        type=str,
        help="Elasticsearch API key (alternative to auth in URL)",
    )
    es_group.add_argument(
        "--es-recreate",
        action="store_true",
        help="Delete and recreate Elasticsearch index",
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Set global checksum validation flag
    if args.skip_checksum:
        config.SKIP_CHECKSUM_VALIDATION = True
        logger.info("ISSN checksum validation disabled")

    # Reset metrics at start
    reset_metrics()

    logger.info("ISSN Data Unifier")
    logger.info("=" * 60)
    logger.info(f"Input directory: {args.input_dir}")
    logger.info(f"Output directory: {args.output_dir}")

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Load ISSN-L mapping
    logger.info("=" * 60)
    logger.info("Loading ISSN-L Mapping Table")
    logger.info("=" * 60)
    issn_l_map = load_issn_l_table(args.input_dir)

    # Load data from each source
    logger.info("=" * 60)
    logger.info("Loading Source Data")
    logger.info("=" * 60)

    all_journals = []

    # Load each source
    all_journals.extend(load_crossref_data(args.input_dir))
    all_journals.extend(load_openalex_data(args.input_dir))
    all_journals.extend(load_pmc_data(args.input_dir))
    all_journals.extend(load_doaj_data(args.input_dir))
    all_journals.extend(load_nlm_data(args.input_dir))
    all_journals.extend(load_lsiou_data(args.input_dir))
    all_journals.extend(load_jstage_data(args.input_dir))
    all_journals.extend(load_wikidata_data(args.input_dir))  # Gap-filling: no NLM/OpenAlex IDs

    logger.info(f"Total records loaded: {len(all_journals):,}")

    if not all_journals:
        logger.error("No data found! Run 'python -m sibils_journals download' first.")
        return 1

    # Validate ISSN-L consistency (detect records with conflicting ISSNs)
    if issn_l_map:
        conflicts = validate_issn_l_consistency(all_journals, issn_l_map)
        if conflicts:
            logger.warning(f"Found {len(conflicts)} ISSN-L consistency conflicts")
            export_issn_conflicts(conflicts, args.output_dir / "issn_conflicts.csv")

    # Unify data
    df = unify_journals(all_journals, issn_l_map, output_dir=args.output_dir)

    # Apply SIBiLS filter if requested
    if args.sibils_filter:
        # sibils_filter is True (no version) or a version string
        version = args.sibils_filter if isinstance(args.sibils_filter, str) else None
        df = apply_sibils_filter(df, output_dir=args.output_dir, version=version)

    # Print statistics (and save to file)
    stats = print_stats(df, output_path=args.output_dir / "summary.txt")

    # Export unified data
    export_csv(df, args.output_dir / args.output_file)
    export_summary_json(stats, args.output_dir / "summary.json")

    # Export to Elasticsearch if URL provided
    if args.es_url:
        export_elasticsearch(
            df,
            es_url=args.es_url,
            index_name=args.es_index,
            es_api_key=args.es_api_key,
            recreate_index=args.es_recreate,
        )

    # Print data quality metrics
    get_metrics().print_report()

    logger.info("=" * 60)
    logger.info("Unification Complete!")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
