"""Summary exporters for unified ISSN data statistics."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def export_summary_json(stats: dict, output_path: Path) -> Path:
    """
    Export statistics summary as JSON.

    Args:
        stats: Dictionary of statistics from print_stats()
        output_path: Path to output JSON file

    Returns:
        Path to the created JSON file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(stats, f, indent=2)

    logger.info(f"Summary saved to: {output_path}")
    return output_path
