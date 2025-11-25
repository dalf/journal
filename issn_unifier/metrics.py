"""Data quality metrics collection during processing."""

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Max samples to keep for each failure type
_MAX_SAMPLES = 10


@dataclass
class QualityMetrics:
    """Collects data quality metrics during processing."""

    # ISSN validation
    issn_total: int = 0
    issn_valid: int = 0
    issn_invalid_format: int = 0
    issn_invalid_checksum: int = 0

    # Sample of failed ISSNs for debugging
    issn_invalid_format_samples: list = field(default_factory=list)
    issn_invalid_checksum_samples: list = field(default_factory=list)

    # Normalization fallbacks (value couldn't be normalized)
    normalization_failures: Counter = field(default_factory=Counter)

    # Records processing
    records_total: int = 0
    records_with_issn: int = 0
    records_without_issn: int = 0

    # Duplicates removed per source
    duplicates_removed: Counter = field(default_factory=Counter)

    def record_issn_validation(
        self,
        valid: bool,
        invalid_format: bool = False,
        invalid_checksum: bool = False,
        issn_value: str | None = None,
    ) -> None:
        """Record an ISSN validation attempt."""
        self.issn_total += 1
        if valid:
            self.issn_valid += 1
        elif invalid_format:
            self.issn_invalid_format += 1
            if issn_value and len(self.issn_invalid_format_samples) < _MAX_SAMPLES:
                self.issn_invalid_format_samples.append(issn_value)
        elif invalid_checksum:
            self.issn_invalid_checksum += 1
            if issn_value and len(self.issn_invalid_checksum_samples) < _MAX_SAMPLES:
                self.issn_invalid_checksum_samples.append(issn_value)

    def record_normalization_failure(self, field_name: str) -> None:
        """Record a normalization that couldn't find a match."""
        self.normalization_failures[field_name] += 1

    def record_duplicate_removed(self, source: str, count: int = 1) -> None:
        """Record duplicate(s) removed during deduplication."""
        self.duplicates_removed[source] += count

    def report(self) -> dict:
        """Generate quality metrics report."""
        report = {
            "issn": {
                "total": self.issn_total,
                "valid": self.issn_valid,
                "invalid_format": self.issn_invalid_format,
                "invalid_checksum": self.issn_invalid_checksum,
                "validation_rate": (f"{self.issn_valid / self.issn_total * 100:.1f}%" if self.issn_total > 0 else "N/A"),
            },
            "normalization_failures": dict(self.normalization_failures),
            "duplicates_removed": dict(self.duplicates_removed),
        }
        return report

    def print_report(self) -> None:
        """Print quality metrics to logger."""
        logger.info("=" * 60)
        logger.info("Data Quality Metrics")
        logger.info("=" * 60)

        # ISSN validation
        logger.info("")
        logger.info("ISSN Validation:")
        logger.info(f"  Total processed: {self.issn_total:,}")
        if self.issn_total > 0:
            logger.info(f"  Valid: {self.issn_valid:,} ({self.issn_valid / self.issn_total * 100:.1f}%)")
            if self.issn_invalid_format > 0:
                logger.info(f"  Invalid format: {self.issn_invalid_format:,} ({self.issn_invalid_format / self.issn_total * 100:.1f}%)")
                if self.issn_invalid_format_samples:
                    logger.info(f"    Samples: {', '.join(self.issn_invalid_format_samples)}")
            if self.issn_invalid_checksum > 0:
                logger.info(f"  Invalid checksum: {self.issn_invalid_checksum:,} ({self.issn_invalid_checksum / self.issn_total * 100:.1f}%)")
                if self.issn_invalid_checksum_samples:
                    logger.info(f"    Samples: {', '.join(self.issn_invalid_checksum_samples)}")

        # Normalization failures
        if self.normalization_failures:
            logger.info("")
            logger.info("Normalization failures (unrecognized values):")
            for field_name, count in self.normalization_failures.most_common(10):
                logger.info(f"  {field_name}: {count:,}")

        # Duplicates removed
        if self.duplicates_removed:
            total_dups = sum(self.duplicates_removed.values())
            logger.info("")
            logger.info(f"Duplicates removed: {total_dups:,}")
            for source, count in self.duplicates_removed.most_common():
                logger.info(f"  {source}: {count:,}")

    def reset(self) -> None:
        """Reset all metrics."""
        self.issn_total = 0
        self.issn_valid = 0
        self.issn_invalid_format = 0
        self.issn_invalid_checksum = 0
        self.issn_invalid_format_samples.clear()
        self.issn_invalid_checksum_samples.clear()
        self.normalization_failures.clear()
        self.records_total = 0
        self.records_with_issn = 0
        self.records_without_issn = 0
        self.duplicates_removed.clear()


# Global metrics instance
_metrics: Optional[QualityMetrics] = None


def get_metrics() -> QualityMetrics:
    """Get the global metrics instance, creating if needed."""
    global _metrics
    if _metrics is None:
        _metrics = QualityMetrics()
    return _metrics


def reset_metrics() -> None:
    """Reset global metrics."""
    global _metrics
    if _metrics is not None:
        _metrics.reset()
