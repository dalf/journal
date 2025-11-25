"""Statistics and reporting for unified ISSN data."""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def print_stats(df: pd.DataFrame, output_path: Optional[Path] = None) -> dict:
    """
    Print and return statistics about the unified data.

    Args:
        df: DataFrame containing unified journal records
        output_path: Optional path to save statistics as text file

    Returns:
        Dictionary of computed statistics
    """
    total = len(df)
    lines: list[str] = []  # Collect output for file

    def output(msg: str = "") -> None:
        """Log message and collect for file output."""
        logger.info(msg)
        lines.append(msg)

    # Helper to safely count non-null values
    def count_notna(col: str) -> int:
        if col in df.columns:
            return int(df[col].notna().sum())
        return 0

    stats = {
        "total": total,
        # Core fields
        "with_issn_l": count_notna("issn_l"),
        "with_issn_print": count_notna("issn_print"),
        "with_issn_electronic": count_notna("issn_electronic"),
        "with_title": count_notna("title"),
        "with_publisher": count_notna("publisher"),
        "with_country": count_notna("country"),
        # Basic metadata
        "with_alternative_titles": count_notna("alternative_titles"),
        "with_other_organisations": count_notna("other_organisations"),
        "with_source_type": count_notna("source_type"),
        "with_is_oa": count_notna("is_oa"),
        "with_subjects": count_notna("subjects"),
        "with_apc_amount": count_notna("apc_amount"),
        "with_apc_currency": count_notna("apc_currency"),
        "with_language": count_notna("language"),
        # HIGH PRIORITY: URLs
        "with_journal_url": count_notna("journal_url"),
        # HIGH PRIORITY: Licensing
        "with_license": count_notna("license"),
        "with_license_url": count_notna("license_url"),
        # HIGH PRIORITY: Editorial
        "with_review_process": count_notna("review_process"),
        "with_review_process_url": count_notna("review_process_url"),
        # HIGH PRIORITY: Preservation
        "with_preservation_services": count_notna("preservation_services"),
        # MEDIUM PRIORITY: Copyright
        "with_copyright_author": count_notna("copyright_author"),
        "with_copyright_url": count_notna("copyright_url"),
        # MEDIUM PRIORITY: Quality
        "with_plagiarism_screening": count_notna("plagiarism_screening"),
        "with_deposit_policy": count_notna("deposit_policy"),
        # HIGH PRIORITY: Metrics
        "with_works_count": count_notna("works_count"),
        "with_cited_by_count": count_notna("cited_by_count"),
        # MEDIUM PRIORITY: Additional metrics
        "with_h_index": count_notna("h_index"),
    }

    output("=" * 60)
    output("Statistics")
    output("=" * 60)

    output(f"Total unique journals: {stats['total']:,}")

    # Guard against division by zero
    if total == 0:
        logger.warning("No journals found - statistics unavailable")
        stats["source_counts"] = {}
        stats["multi_source"] = 0
        stats["oa_journals"] = 0
        return stats

    def log_stat(label: str, key: str) -> None:
        val = stats[key]
        output(f"  {label}: {val:,} ({val / total * 100:.1f}%)")

    # Core fields
    output("")
    output("Core fields:")
    log_stat("With ISSN-L", "with_issn_l")
    log_stat("With Print ISSN", "with_issn_print")
    log_stat("With Electronic ISSN", "with_issn_electronic")
    log_stat("With Title", "with_title")
    log_stat("With Publisher", "with_publisher")
    log_stat("With Country", "with_country")

    # URLs
    output("")
    output("URLs:")
    log_stat("With Journal URL", "with_journal_url")

    # Licensing
    output("")
    output("Licensing:")
    log_stat("With License", "with_license")
    log_stat("With License URL", "with_license_url")

    # Editorial
    output("")
    output("Editorial:")
    log_stat("With Review Process", "with_review_process")
    log_stat("With Review Process URL", "with_review_process_url")
    log_stat("With Plagiarism Screening", "with_plagiarism_screening")

    # Preservation & Copyright
    output("")
    output("Preservation & Copyright:")
    log_stat("With Preservation Services", "with_preservation_services")
    log_stat("With Copyright (Author)", "with_copyright_author")
    log_stat("With Deposit Policy", "with_deposit_policy")

    # Metrics
    output("")
    output("Metrics:")
    log_stat("With Works Count", "with_works_count")
    log_stat("With Cited By Count", "with_cited_by_count")
    log_stat("With h-index", "with_h_index")

    # Extended metadata
    output("")
    output("Extended metadata:")
    log_stat("With Alternative Titles", "with_alternative_titles")
    log_stat("With Other Organisations", "with_other_organisations")
    log_stat("With Source Type", "with_source_type")
    log_stat("With Subjects", "with_subjects")
    log_stat("With Language", "with_language")
    log_stat("With APC Amount", "with_apc_amount")
    log_stat("With APC Currency", "with_apc_currency")

    # Open Access statistics
    stats["oa_journals"] = int(df["is_oa"].sum())
    output("")
    output(f"Open Access journals: {stats['oa_journals']:,} ({stats['oa_journals'] / total * 100:.1f}%)")

    # Source coverage
    output("")
    output("Source coverage:")
    source_counts = df["sources"].str.split(",").explode().value_counts()
    stats["source_counts"] = source_counts.to_dict()

    for source, count in source_counts.items():
        pct = count / total * 100
        output(f"  {source}: {count:,} ({pct:.1f}%)")

    # Multi-source coverage
    multi_source = df[df["sources"].str.contains(",", regex=False)]
    stats["multi_source"] = len(multi_source)
    output("")
    output(f"Journals in multiple sources: {stats['multi_source']:,} ({stats['multi_source'] / total * 100:.1f}%)")

    # License distribution
    if stats["with_license"] > 0:
        output("")
        output("License distribution:")
        license_counts = df["license"].value_counts()
        for lic, count in license_counts.head(10).items():
            if pd.notna(lic):
                output(f"  {lic}: {count:,}")

    # Review process distribution (explode pipe-separated values)
    if stats["with_review_process"] > 0:
        output("")
        output("Review process distribution:")
        review_counts = df["review_process"].str.split("|").explode().value_counts()
        for rp, count in review_counts.head(10).items():
            if pd.notna(rp) and rp:
                output(f"  {rp}: {count:,}")

    # Source type distribution
    if stats["with_source_type"] > 0:
        output("")
        output("Source type distribution:")
        type_counts = df["source_type"].value_counts()
        for stype, count in type_counts.head(10).items():
            if pd.notna(stype):
                output(f"  {stype}: {count:,}")

    # Write to file if requested
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write("\n".join(lines))
        logger.info(f"Statistics saved to: {output_path}")

    return stats
