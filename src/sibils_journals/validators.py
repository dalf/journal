"""Data quality validators for SIBiLS journals."""

import csv
import logging
from dataclasses import dataclass
from pathlib import Path

from .models import DataSource, JournalDict

logger = logging.getLogger(__name__)


@dataclass
class ISSNConflict:
    """Represents an ISSN-L consistency conflict.

    This occurs when a record has print and electronic ISSNs that resolve
    to different ISSN-L values in the official ISSN-L table, indicating
    the record incorrectly combines ISSNs from two different journals.
    """

    source: DataSource
    title: str | None
    issn_print: str
    issn_electronic: str
    issn_l_print: str
    issn_l_electronic: str


def validate_issn_l_consistency(
    journals: list[JournalDict],
    issn_l_map: dict[str, str],
) -> list[ISSNConflict]:
    """
    Detect records where print and electronic ISSNs resolve to different ISSN-L.

    This indicates a data quality issue - the record claims two ISSNs that
    belong to different journals according to the official ISSN-L table.

    Args:
        journals: List of journal records to validate
        issn_l_map: Mapping from ISSN to ISSN-L

    Returns:
        List of ISSNConflict instances for records with mismatched ISSN-L
    """
    conflicts = []
    for j in journals:
        pissn = j.get("issn_print")
        eissn = j.get("issn_electronic")
        if pissn and eissn:
            issn_l_p = issn_l_map.get(pissn)
            issn_l_e = issn_l_map.get(eissn)
            if issn_l_p and issn_l_e and issn_l_p != issn_l_e:
                conflicts.append(
                    ISSNConflict(
                        source=j.get("source", DataSource.CROSSREF),
                        title=j.get("title"),
                        issn_print=pissn,
                        issn_electronic=eissn,
                        issn_l_print=issn_l_p,
                        issn_l_electronic=issn_l_e,
                    )
                )
    return conflicts


def export_issn_conflicts(conflicts: list[ISSNConflict], output_path: Path) -> None:
    """
    Export ISSN conflicts to CSV for review.

    Args:
        conflicts: List of ISSNConflict instances
        output_path: Path to write CSV file
    """
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "source",
                "title",
                "issn_print",
                "issn_electronic",
                "issn_l_print",
                "issn_l_electronic",
            ]
        )
        for c in conflicts:
            writer.writerow(
                [
                    c.source.value if hasattr(c.source, "value") else c.source,
                    c.title,
                    c.issn_print,
                    c.issn_electronic,
                    c.issn_l_print,
                    c.issn_l_electronic,
                ]
            )
    logger.info(f"Exported {len(conflicts)} ISSN conflicts to {output_path}")
