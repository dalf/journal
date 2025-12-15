"""
ISSN Data Unifier

A modular package for merging journal/ISSN data from multiple sources.

Public API:
- Models: JournalDict, constants, serialize_journal
- Normalizers: All normalize_* functions
- Loaders: All load_* functions
- Merger: unify_journals()
- Stats: print_stats()
"""

__version__ = "0.1.0"

# Export exporters
from .exporters import export_csv, export_elasticsearch, export_summary_json

# Export loaders
from .loaders import (
    load_crossref_data,
    load_doaj_data,
    load_issn_l_table,
    load_openalex_data,
    load_pmc_data,
    process_openalex_record,
    process_pmc_record,
)

# Export merger
from .merger import create_unified_record, make_title_identifier, merge_journal_records, unify_journals

# Export metrics
from .metrics import QualityMetrics, get_metrics, reset_metrics

# Export config constants
from .config import DEFAULT_OUTPUT_DIR, DEFAULT_RAW_DIR

# Export models and constants
from .models import (
    DEFAULT_SOURCE_PRIORITY,
    ISSN_PATTERN,
    NLM_ID_PATTERN,
    OPENALEX_ID_PATTERN,
    DataSource,
    JournalDict,
    PreservationService,
    ReviewProcess,
    make_nlm_identifier,
    make_openalex_identifier,
    serialize_journal,
)

# Export all normalizers
from .normalizers import (
    is_valid_identifier,
    normalize_country,
    normalize_deposit_policy,
    normalize_issn,
    normalize_issn_series,
    normalize_language,
    normalize_license,
    normalize_preservation_service,
    normalize_publisher,
    normalize_review_process,
    normalize_text_series,
    normalize_title,
    remove_control_chars,
    validate_issn_checksum,
)

# Export sibils
from .sibils_filter import apply_sibils_filter, load_sibils_journals, load_sibils_raw_data

# Export stats
from .stats import print_stats

# Export validators
from .validators import ISSNConflict, export_issn_conflicts, validate_issn_l_consistency

__all__ = [
    # Version
    "__version__",
    # Models and constants
    "DataSource",
    "ReviewProcess",
    "PreservationService",
    "JournalDict",
    "serialize_journal",
    "DEFAULT_RAW_DIR",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_SOURCE_PRIORITY",
    "ISSN_PATTERN",
    "NLM_ID_PATTERN",
    "OPENALEX_ID_PATTERN",
    "make_nlm_identifier",
    "make_openalex_identifier",
    # Normalizers
    "is_valid_identifier",
    "validate_issn_checksum",
    "normalize_issn",
    "normalize_issn_series",
    "remove_control_chars",
    "normalize_title",
    "normalize_publisher",
    "normalize_text_series",
    "normalize_country",
    "normalize_language",
    "normalize_license",
    "normalize_review_process",
    "normalize_preservation_service",
    "normalize_deposit_policy",
    # Loaders
    "load_issn_l_table",
    "load_crossref_data",
    "load_openalex_data",
    "process_openalex_record",
    "load_pmc_data",
    "process_pmc_record",
    "load_doaj_data",
    # Metrics
    "QualityMetrics",
    "get_metrics",
    "reset_metrics",
    # Core
    "unify_journals",
    "create_unified_record",
    "merge_journal_records",
    "make_title_identifier",
    "print_stats",
    # Exporters
    "export_csv",
    "export_elasticsearch",
    "export_summary_json",
    # SIBiLS
    "apply_sibils_filter",
    "load_sibils_journals",
    "load_sibils_raw_data",
    # Validators
    "ISSNConflict",
    "validate_issn_l_consistency",
    "export_issn_conflicts",
]
