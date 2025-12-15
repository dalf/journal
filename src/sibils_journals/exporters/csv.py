"""CSV exporter for unified ISSN data."""

import csv
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def export_csv(
    df: pd.DataFrame,
    output_path: Path,
    quoting: int = csv.QUOTE_NONNUMERIC,
) -> Path:
    """
    Export unified journal data to CSV.

    Args:
        df: DataFrame containing unified journal records
        output_path: Path to output CSV file
        quoting: CSV quoting style (default: QUOTE_NONNUMERIC)

    Returns:
        Path to the created CSV file
    """
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Reorder columns to put unified_id first and sort rows by it
    if "unified_id" in df.columns:
        cols = ["unified_id"] + [c for c in df.columns if c != "unified_id"]
        df = df[cols].sort_values("unified_id")

    df.to_csv(output_path, index=False, quoting=quoting)
    logger.info(f"Unified data saved to: {output_path}")

    return output_path
