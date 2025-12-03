"""
Data loaders for various ISSN sources.

Each loader imports normalizers from sibils_journals.normalizers and uses
the deduplicate_journals() helper to remove within-source duplicates.

The loading pipeline has three testable layers:
1. normalize_*_dataframe() - DataFrame transformation (testable with synthetic DataFrames)
2. process_*_record() - Record transformation (testable with dict literals)
3. load_*_data() - I/O orchestration (requires real files)
"""

from ..models import JournalDict
from .crossref import load_crossref_data, normalize_crossref_dataframe, process_crossref_record
from .doaj import load_doaj_data, normalize_doaj_dataframe, process_doaj_record
from .europepmc import load_europepmc_data, parse_europepmc_issn, process_europepmc_record
from .issn import load_issn_l_table
from .nlm import load_nlm_data, parse_nlm_record
from .openalex import load_openalex_data, process_openalex_record
from .utils import deduplicate_journals

__all__ = [
    "JournalDict",
    "deduplicate_journals",
    # Loaders
    "load_issn_l_table",
    "load_crossref_data",
    "load_openalex_data",
    "load_europepmc_data",
    "load_doaj_data",
    "load_nlm_data",
    # DataFrame normalizers (testable with synthetic DataFrames)
    "normalize_crossref_dataframe",
    "normalize_doaj_dataframe",
    # Record processors (testable with dict literals)
    "process_crossref_record",
    "process_doaj_record",
    "process_europepmc_record",
    "process_openalex_record",
    "parse_europepmc_issn",
    "parse_nlm_record",
]
