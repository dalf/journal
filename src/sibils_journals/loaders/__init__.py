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
from .crossref import load_crossref_data, process_crossref_item
from .doaj import load_doaj_data, normalize_doaj_dataframe, process_doaj_record
from .issn import load_issn_l_table
from .jstage import load_jstage_data, process_jstage_record
from .lsiou import load_lsiou_data, parse_lsiou_record
from .nlm import load_nlm_data, parse_nlm_record
from .openalex import load_openalex_data, process_openalex_record
from .pmc import load_pmc_data, process_pmc_record
from .wikidata import load_wikidata_data, process_wikidata_results
from .utils import deduplicate_journals

__all__ = [
    "JournalDict",
    "deduplicate_journals",
    # Loaders
    "load_issn_l_table",
    "load_crossref_data",
    "load_openalex_data",
    "load_pmc_data",
    "load_doaj_data",
    "load_nlm_data",
    "load_lsiou_data",
    "load_jstage_data",
    "load_wikidata_data",
    # DataFrame normalizers (testable with synthetic DataFrames)
    "normalize_doaj_dataframe",
    # Record processors (testable with dict literals)
    "process_crossref_item",
    "process_doaj_record",
    "process_pmc_record",
    "process_openalex_record",
    "parse_nlm_record",
    "parse_lsiou_record",
    "process_jstage_record",
    "process_wikidata_results",
]
