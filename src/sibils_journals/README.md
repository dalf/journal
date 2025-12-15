# SIBiLS Journals

Journal repository for SIBiLS - merges journal data from multiple sources.

## Python API

### Import normalized functions

```python
from sibils_journals import (
    JournalDict,
    normalize_issn,
    normalize_country,
    normalize_language,
    normalize_license,
    normalize_review_process,
)

# Use normalizers
issn = normalize_issn("1234-5678")
country = normalize_country("United States")  # Returns "US"
language = normalize_language("English")  # Returns ["en"]
license = normalize_license("CC BY")  # Returns "CC-BY-4.0"
```

### Create journal records

```python
from sibils_journals import JournalDict, serialize_journal

record: JournalDict = {
    "issn_l": "1234-5678",
    "title": "Test Journal",
    "publisher": "Test Publisher",
    "country": "US",
    "language": ["en"],
    "license": "CC-BY-4.0",
    "sources": ["doaj"],
}

# Convert to serializable dict for CSV/DataFrame
serialized = serialize_journal(record)
```

### Unify journals from multiple sources

```python
from sibils_journals import (
    load_issn_l_table,
    load_doaj_data,
    load_crossref_data,
    unify_journals,
)

# Load ISSN-L mapping
issn_l_map = load_issn_l_table(input_dir)

# Load data from sources
journals = []
journals.extend(load_doaj_data(input_dir))
journals.extend(load_crossref_data(input_dir))

# Unify into single DataFrame
df = unify_journals(journals, issn_l_map)
```

## Package Structure

```
sibils_journals/
├── __init__.py                    # Public API exports
├── __main__.py                    # CLI entry point with subcommands
├── config.py                      # Configuration and paths
├── download.py                    # Download data from sources
├── unify.py                       # Unify downloaded data
├── models.py                      # JournalDict TypedDict + constants
├── metrics.py                     # QualityMetrics tracking
├── merger.py                      # Journal unification logic
├── stats.py                       # Statistics generation
├── sibils_fetch.py                # Fetch journal data from SIBiLS Elasticsearch
├── sibils_filter.py               # Filter/match unified data against SIBiLS
├── validators.py                  # ISSN-L consistency validation
├── normalizers/
│   ├── __init__.py               # Export all normalize_* functions
│   ├── identifiers.py            # ISSN validation and normalization
│   ├── text.py                   # Text normalization
│   ├── geography.py              # Country normalization (ISO 3166-1)
│   ├── languages.py              # Language normalization (ISO 639-1)
│   ├── licenses.py               # License normalization (SPDX)
│   ├── subjects.py               # Subject/discipline normalization
│   ├── review_process.py         # Review process normalization
│   ├── preservation.py           # Preservation service normalization
│   ├── deposit_policy.py         # Deposit policy normalization
│   └── utils.py                  # Shared normalizer utilities
├── loaders/
│   ├── __init__.py               # Export all load_* functions
│   ├── issn.py                   # ISSN-L table loader
│   ├── crossref.py               # Crossref data
│   ├── openalex.py               # OpenAlex data
│   ├── pmc.py                    # PMC journal list (deposit agreements)
│   ├── doaj.py                   # DOAJ data
│   ├── nlm.py                    # NLM Catalog data
│   ├── lsiou.py                  # LSIOU (MEDLINE serials with relationships)
│   ├── jstage.py                 # J-STAGE (Japanese journals)
│   ├── wikidata.py               # Wikidata SPARQL (gap-filling)
│   └── utils.py                  # Shared loader utilities
└── exporters/
    ├── __init__.py               # Export all export functions
    ├── csv.py                    # CSV export
    ├── summary.py                # Summary/statistics export
    └── elasticsearch.py          # Elasticsearch export
```

## Data Pipeline

```mermaid
flowchart TD
    subgraph ext_data["External Data Sources"]
        direction LR
        EXT_CR[("Crossref API")] ~~~ EXT_OA[("OpenAlex S3")] ~~~ EXT_DOAJ[("DOAJ")] ~~~ EXT_PMC[("PMC jlist")] ~~~ EXT_NLM[("NLM/NCBI")] ~~~ EXT_LSIOU[("LSIOU FTP")] ~~~ EXT_JSTAGE[("J-STAGE")] ~~~ EXT_WD[("Wikidata")] ~~~ EXT_ISSN[("ISSN.org")]
    end

    subgraph ext_sibils["SIBiLS Production"]
        EXT_ES[("SIBiLS ES")]
    end

    subgraph download["0. DOWNLOAD"]
        DL["sibils-journals download<br/>(download.py)"]
        SF["sibils-journals fetch-sibils<br/>(sibils_fetch.py)"]
    end

    subgraph sources["1a. DATA SOURCES"]
        CR[("Crossref<br/>~130K titles")]
        OA[("OpenAlex<br/>~250K sources")]
        DOAJ[("DOAJ<br/>~20K OA journals")]
        PMC[("PMC jlist<br/>~4K agreements")]
        NLM[("NLM<br/>~35K MEDLINE")]
        LSIOU[("LSIOU<br/>~15K MEDLINE serials")]
        JSTAGE[("J-STAGE<br/>~4K Japanese journals")]
        WIKIDATA[("Wikidata<br/>gap-filling")]
        ISSNL[("ISSN-L Table<br/>~2.5M mappings<br/>ISSN → ISSN-L")]
    end

    subgraph loaders["1b. LOADERS (loaders module)"]
        L1["Parse CSV/JSON/API"]
        L2["Normalize fields<br/>(ISSN, titles, countries)"]
        L3["Deduplicate within source"]
        L4["Tag with DataSource"]
    end

    subgraph validation["VALIDATION (validators.py)"]
        VAL["ISSN-L Check"]
    end

    subgraph priority["Source Priority (models.py)"]
        PR["LSIOU (7)<br/>DOAJ &amp; NLM (6)<br/>OpenAlex (5)<br/>Crossref &amp; J-STAGE (4)<br/>PMC (3)<br/>Wikidata (2)"]
    end

    subgraph merge["3. MERGE (merger.py)"]
        direction TB
        P1["Phase 1: Key Resolution<br/>ISSN → canonical key"]
        P2["Phase 2: ISSN-based Merge<br/>Group by ISSN-L"]
        P3["Phase 3: Title-based Merge<br/>Records without ISSN"]
        P4["Phase 4: Synthetic IDs<br/>NLM-xxx, ISBN-xxx, OPENALEX-xxx, TITLE-xxx"]

        P1 --> P2 --> P3 --> P4
    end

    subgraph sibils["4. SIBiLS FILTER, optional<br>(sibils_filter.py)"]
        direction TB
        SD[("SIBiLS Data<br/>75K journal tuples")]

        subgraph matching["Matching Strategy"]
            M1["1a. medline_abbreviation"]
            M2["1b. nlm_id"]
            M3["2. normalized title"]
            M4["3. alternative_titles"]
        end

        subgraph processing["Processing"]
            F1["Filter: keep matched only"]
            F2["Annotate: add 'sibils' source"]
            F3["Enrich: add alt titles"]
            F4["Add unmatched SIBiLS entries"]
        end

        REM[/"sibils_removed.csv"/]
        UNM[/"sibils_unmatched.csv"/]

        SD --> matching
        matching --> processing
        processing --> REM
        processing --> UNM
    end

    subgraph output["5. OUTPUT (exporters module)"]
        direction LR
        EXP_CSV["csv.py"] --> CSV[/"unified_issn.csv"/]
        EXP_SUM["summary.py"] --> JSON[/"summary.json"/]
        EXP_ES["elasticsearch.py"] --> ES[("Elasticsearch<br/>(optional)")]
        CONF[/"issn_conflicts.csv"/]
    end

    %% Main flow
    ext_data --> DL
    DL --> sources
    ext_sibils --> SF
    SF --> SD
    sources --> loaders
    loaders --> merge
    loaders -.-> VAL
    ISSNL -.-> VAL
    VAL -.-> CONF
    priority -.-> merge
    merge --> |"--sibils-filter"| sibils
    merge --> |"without --sibils-filter"| output
    sibils --> output

    %% Styling
    classDef source fill:#e1f5fe,stroke:#01579b
    classDef process fill:#fff3e0,stroke:#e65100
    classDef data fill:#f3e5f5,stroke:#7b1fa2
    classDef file fill:#e8f5e9,stroke:#2e7d32
    classDef db fill:#fce4ec,stroke:#c2185b

    class CR,OA,DOAJ,PMC,NLM,LSIOU,JSTAGE,WIKIDATA source
    class DL,SF,L1,L2,L3,L4,VAL,P1,P2,P3,P4,M1,M2,M3,M4,F1,F2,F3,F4,EXP_CSV,EXP_SUM,EXP_ES process
    class ISSNL,SD db
    class CONF,CSV,JSON,REM,UNM file
    class ES,EXT_CR,EXT_OA,EXT_DOAJ,EXT_PMC,EXT_NLM,EXT_LSIOU,EXT_JSTAGE,EXT_WD,EXT_ISSN,EXT_ES db
```
