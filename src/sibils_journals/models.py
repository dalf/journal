"""Data models and constants for SIBiLS journals."""

import re
from enum import Enum
from typing import TypedDict, get_origin, get_type_hints

# ISSN regex pattern (NNNN-NNNX where X is digit or X)
ISSN_PATTERN = re.compile(r"^\d{4}-\d{3}[\dXx]$")

# Synthetic identifier patterns for journals without ISSN
NLM_ID_PATTERN = re.compile(r"^NLM-\d+$")
OPENALEX_ID_PATTERN = re.compile(r"^OPENALEX-S\d+$")

# ISBN-13 pattern (starts with 978- or 979-)
ISBN_PATTERN = re.compile(r"^97[89]-[\d-]+$")

# Synthetic identifier patterns for ISBN and TITLE
ISBN_ID_PATTERN = re.compile(r"^ISBN-97[89][\d-]+$")  # ISBN-{isbn13}
TITLE_ID_PATTERN = re.compile(r"^TITLE-[0-9a-f]{8}$")  # TITLE-{md5hash}


def make_nlm_identifier(nlm_id: str) -> str:
    """Create a synthetic identifier from an NLM ID."""
    return f"NLM-{nlm_id}"


def make_openalex_identifier(openalex_id: str) -> str:
    """Create a synthetic identifier from an OpenAlex ID.

    Args:
        openalex_id: OpenAlex ID (e.g., 'S4306530189' or full URL)

    Returns:
        Synthetic identifier like 'OPENALEX-S4306530189'
    """
    # Extract just the ID part if full URL provided
    if openalex_id.startswith("https://openalex.org/"):
        openalex_id = openalex_id.replace("https://openalex.org/", "")
    return f"OPENALEX-{openalex_id}"


def is_isbn(value: str | None) -> bool:
    """Check if a value looks like an ISBN-13."""
    if not value:
        return False
    return bool(ISBN_PATTERN.match(value))


def make_isbn_identifier(isbn: str) -> str:
    """Create a synthetic identifier from an ISBN."""
    return f"ISBN-{isbn}"


class DataSource(str, Enum):
    """Data sources for journal metadata."""

    OPENALEX = "openalex"
    CROSSREF = "crossref"
    DOAJ = "doaj"
    PMC = "pmc"  # PubMed Central journal list (journals with deposit agreements)
    NLM = "nlm"
    LSIOU = "lsiou"  # NLM List of Serials Indexed for Online Users (MEDLINE journals)
    JSTAGE = "jstage"  # J-STAGE (Japan Science and Technology Information Aggregator)
    WIKIDATA = "wikidata"  # Wikidata journals (gap-filling: no NLM/OpenAlex ID)
    SIBILS = "sibils"  # SIBiLS journal references (title-only, no ISSN)


# Default source priority (higher = preferred)
# Principle: curated sources > aggregated sources
DEFAULT_SOURCE_PRIORITY = {
    DataSource.DOAJ: 6,  # Curated OA data (strict quality criteria)
    DataSource.NLM: 6,  # Curated biomedical data (librarian-maintained)
    DataSource.LSIOU: 7,  # NLM MEDLINE serials (most authoritative for biomedical journals)
    DataSource.OPENALEX: 5,  # Broad coverage, metrics, subjects
    DataSource.CROSSREF: 4,  # Publisher-reported data, fill gaps
    DataSource.JSTAGE: 4,  # J-STAGE Japanese journals (JST-maintained)
    DataSource.PMC: 3,  # PMC journal list (is_pmc_indexed flag + publisher)
    DataSource.WIKIDATA: 2,  # Gap-filling (journals without NLM/OpenAlex IDs)
    DataSource.SIBILS: 0,  # Title-only data (added via --sibils-filter)
}


class ReviewProcess(str, Enum):
    """Peer review process types (controlled vocabulary)."""

    DOUBLE_BLIND = "double-blind"  # Author and reviewer identities hidden from each other
    SINGLE_BLIND = "single-blind"  # Author identity hidden from reviewers
    TRIPLE_BLIND = "triple-blind"  # Author, reviewer, AND editor identities hidden
    OPEN = "open"  # All identities known (transparent review)
    EDITORIAL = "editorial"  # Review by editors/editorial board
    COMMITTEE = "committee"  # Review by committee
    PEER_REVIEW = "peer-review"  # Generic peer review (unspecified type)
    POST_PUBLICATION = "post-publication"  # Review after publication
    NONE = "none"  # No peer review


class PreservationService(str, Enum):
    """Digital preservation services (controlled vocabulary)."""

    # Distributed networks
    LOCKSS = "LOCKSS"  # Lots of Copies Keep Stuff Safe
    CLOCKSS = "CLOCKSS"  # Controlled LOCKSS (dark archive)
    PKP_PN = "PKP PN"  # PKP Preservation Network (for OJS journals)

    # Commercial/institutional archives
    PORTICO = "Portico"  # Portico digital preservation service
    JSTOR = "JSTOR"  # JSTOR archival collections

    # Web archives
    INTERNET_ARCHIVE = "Internet Archive"  # archive.org

    # Biomedical archives
    PMC = "PMC"  # PubMed Central (US)
    EUROPE_PMC = "Europe PMC"  # European PubMed Central

    # Academic/library networks
    HATHITRUST = "HathiTrust"  # HathiTrust Digital Library
    SCHOLARS_PORTAL = "Scholars Portal"  # Ontario Council of University Libraries
    MERRITT = "Merritt"  # UC Curation Center repository

    # National libraries
    BRITISH_LIBRARY = "British Library"
    LIBRARY_OF_CONGRESS = "Library of Congress"
    KB = "KB"  # Koninklijke Bibliotheek (Dutch National Library)
    DNB = "DNB"  # Deutsche Nationalbibliothek (German National Library)
    BNF = "BnF"  # Bibliothèque nationale de France
    NLA = "NLA"  # National Library of Australia
    CINES = "CINES"  # Centre Informatique National de l'Enseignement Supérieur (France)

    # Regional networks
    CARINIANA = "Cariniana"  # Brazilian preservation network
    ELIBRARY_RU = "eLIBRARY.RU"  # Russian scientific library
    HRCAK = "Hrčak"  # Croatian portal of scientific journals
    NDPP_CHINA = "NDPP China"  # China National Digital Preservation Program
    MAGIRAN = "Magiran"  # Iranian journal database
    NOORMAGS = "Noormags"  # Iranian scientific journals database
    SID = "SID"  # Scientific Information Database (Iran)
    ISC = "ISC"  # Islamic World Science Citation Center (Iran)
    PHAIDRA = "PHAIDRA"  # Austrian digital asset management
    ZENODO = "Zenodo"  # CERN-hosted open research repository
    SCIENCE_CENTRAL = "Science Central"  # Korean science platform
    KOREAMEDSYNAPSE = "KoreaMed Synapse"  # Korean medical journals archive
    CEEOL = "CEEOL"  # Central and Eastern European Online Library
    GARUDA = "Garuda"  # Indonesian scientific journal network
    SCINDEKS = "SCIndeks"  # Serbian Citation Index
    RACO = "RACO"  # Catalan open access journals repository


class JournalDict(TypedDict, total=False):
    """
    Typed dictionary for journal data returned by loaders.

    All fields are optional (total=False) since different loaders
    provide different subsets of fields.

    ISSN Identifiers:
        - issn_print (p-ISSN): ISSN for the print edition
        - issn_electronic (e-ISSN): ISSN for the online edition
        - issn_l (Linking ISSN): Groups all editions as "the same journal".
          A journal may have multiple ISSNs (print, online, CD-ROM), but one
          ISSN-L links them together. Essential for deduplication when merging
          data from different sources that may only have p-ISSN or e-ISSN.
    """

    # Unified identifier (always populated, unique per record)
    # Format: ISSN-L if available, otherwise NLM-{id}, ISBN-{isbn}, OPENALEX-S{id}, or TITLE-{hash}
    unified_id: str | None

    # Core identifiers (all loaders should provide these)
    title: str | None
    issn_print: str | None  # p-ISSN: print edition
    issn_electronic: str | None  # e-ISSN: online edition
    source: DataSource

    # Extended identifiers
    issn_l: str | None  # Linking ISSN: groups all editions together
    nlm_id: str | None  # NLM unique identifier (from NLM Catalog)
    openalex_id: str | None  # OpenAlex source identifier (e.g., S4306530189)
    wikidata_id: str | None  # Wikidata QID (e.g., Q180445 for Nature)
    publisher: str | None
    country: str | None  # ISO 3166-1 alpha-2 (e.g., US, GB, DE)

    # Basic metadata
    medline_abbreviation: str | None  # Official MEDLINE title abbreviation (from NLM)
    is_medline_indexed: bool | None  # Currently indexed in MEDLINE (from NLM Catalog API)
    is_pmc_indexed: bool | None  # Has deposit agreement with PubMed Central (from PMC jlist)

    # PMC agreement details (from jlist.csv)
    pmc_agreement_status: str | None  # "Active", "No longer participating", "No longer published", "Predecessor title"
    pmc_last_deposit_year: int | None  # Most recent deposit year (from "Most Recent" column)
    pmc_embargo_months: int | None  # Embargo period in months (0 = immediate release)
    alternative_titles: list[str]  # abbreviations, translations, former names
    other_organisations: list[str]  # affiliated orgs beyond primary publisher
    source_type: str | None  # journal, book series, conference, repository, ebook platform
    is_oa: bool | None
    subjects: list[str]
    subject_domain: str | None  # OpenAlex domain (Health Sciences, Physical Sciences, Life Sciences, Social Sciences)
    subject_field: str | None  # OpenAlex field (Medicine, Engineering, etc.)
    subject_subfield: str | None  # OpenAlex subfield (Health Informatics, etc.)
    apc_amount: float | None  # Article Processing Charge (fee to publish OA)
    apc_currency: str | None  # e.g., USD, EUR, GBP
    language: list[str]  # ISO 639-1 codes (e.g., ["en", "fr", "de"])

    # URLs
    journal_url: str | None

    # Licensing (primarily DOAJ)
    license: str | None  # SPDX identifier (e.g., CC-BY-4.0, CC-BY-NC-ND-4.0)
    license_url: str | None

    # Editorial (primarily DOAJ)
    review_process: list[ReviewProcess]
    review_process_url: str | None

    # Preservation (primarily DOAJ)
    preservation_services: list[PreservationService]

    # Copyright (primarily DOAJ)
    copyright_author: bool | None
    copyright_url: str | None

    # Quality indicators (primarily DOAJ)
    plagiarism_screening: bool | None  # journal uses plagiarism detection tools
    deposit_policy: list[str]  # registries where policy is listed (e.g., SHERPA/RoMEO)

    # Metrics (primarily OpenAlex)
    works_count: int | None
    cited_by_count: int | None
    h_index: int | None

    # Provenance (added during merge)
    sources: list[DataSource]

    # ISSN lookup (all ISSNs for comprehensive search)
    all_issns: list[str]  # All ISSNs: issn_l + issn_print + issn_electronic + historical

    # Journal relationships (from LSIOU TitleRelated)
    predecessor_nlm_ids: list[str]  # NLM IDs of predecessor journals (title changes, etc.)
    successor_nlm_ids: list[str]  # NLM IDs of successor journals


# List fields derived from JournalDict type hints (joined with "|" for CSV export)
LIST_FIELDS = [field for field, type_hint in get_type_hints(JournalDict).items() if get_origin(type_hint) is list]


def serialize_journal(journal: JournalDict) -> dict:
    """
    Serialize a JournalDict for DataFrame/CSV export.

    Converts list fields to pipe-separated strings.

    Args:
        journal: Journal dictionary to serialize

    Returns:
        Dictionary ready for DataFrame conversion
    """
    result = {}

    for key, value in journal.items():
        if key in LIST_FIELDS and isinstance(value, list):
            # Convert enums to strings
            if key == "sources":
                value = sorted(s.value if isinstance(s, DataSource) else s for s in value)
            elif key == "review_process":
                value = [v.value if isinstance(v, ReviewProcess) else v for v in value]
            elif key == "preservation_services":
                value = [v.value if isinstance(v, PreservationService) else v for v in value]
            result[key] = "|".join(str(v) for v in value) if value else None
        elif isinstance(value, (DataSource, ReviewProcess, PreservationService)):
            result[key] = value.value
        else:
            result[key] = value

    return result
