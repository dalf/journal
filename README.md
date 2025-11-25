# ISSN Unifier

Unifies journal metadata from multiple sources (OpenAlex, Crossref, DOAJ, EuropePMC, NLM Catalog) into a single normalized dataset using ISSN-L as the primary key, with fallback to NLM ID or OpenAlex ID for journals without ISSN. Includes MEDLINE indexing status and PMC availability flags. Exports to CSV and optionally to Elasticsearch.

## Install

### Using pip

```bash
pip install git+ssh://git@github.com/dalf/journal.git
```

Or with HTTPS:

```bash
pip install git+https://github.com/dalf/journal.git
```

### Using uv (development)

```bash
git clone git@github.com:dalf/journal.git
cd journal
uv sync
```

## Usage

### With pip install

```bash
# Download source data
issn-unifier download

# Fetch SIBiLS journal list (optional, for filtering)
issn-unifier fetch-sibils

# Unify and export
issn-unifier unify --sibils-filter
```

### With uv

```bash
# Download source data
uv run python -m issn_unifier download

# Fetch SIBiLS journal list (optional, for filtering)
uv run python -m issn_unifier fetch-sibils

# Unify and export
uv run python -m issn_unifier unify --sibils-filter
```

Output: `data/unified/unified_issn.csv`

## Options

```bash
usage: issn_unifier unify [-h] [--input-dir INPUT_DIR] [--output-dir OUTPUT_DIR] [--output-file OUTPUT_FILE] [--skip-checksum] [-v] [--sibils-filter [VERSION]]
                          [--es-url ES_URL] [--es-index ES_INDEX] [--es-api-key ES_API_KEY] [--es-recreate]

Unify ISSN data from multiple sources

options:
  -h, --help            show this help message and exit
  --input-dir INPUT_DIR
                        Input directory with raw data (default: data/raw)
  --output-dir OUTPUT_DIR
                        Output directory for unified data (default: data/unified)
  --output-file OUTPUT_FILE
                        Output filename (default: unified_issn.csv)
  --skip-checksum       Skip ISSN checksum validation
  -v, --verbose         Enable verbose/debug logging

SIBiLS filtering:
  --sibils-filter [VERSION]
                        Filter to keep only journals referenced in SIBiLS. Optionally specify version (e.g., 5.0.5.8)

Elasticsearch export:
  --es-url ES_URL       Elasticsearch URL (e.g., https://user:pass@localhost:9200). If provided, exports to ES.
  --es-index ES_INDEX   Elasticsearch index name (default: journals)
  --es-api-key ES_API_KEY
                        Elasticsearch API key (alternative to auth in URL)
  --es-recreate         Delete and recreate Elasticsearch index

Examples:
  issn_unifier unify                                        # Use default directories
  issn_unifier unify --output-file journals.csv             # Custom output filename
  issn_unifier unify --skip-checksum                        # Disable ISSN checksum validation
  issn_unifier unify --es-url http://localhost:9200         # Export to local Elasticsearch
  issn_unifier unify --es-url https://u:p@es.example.com:9200 --es-recreate  # With auth, recreate index
```

### Examples

```bash
# Download specific sources
uv run python -m issn_unifier download --sources crossref,doaj

# Download all sources non-interactively
uv run python -m issn_unifier download --yes

# Unify with custom output
uv run python -m issn_unifier unify --output-file journals.csv

# Export to Elasticsearch
uv run python -m issn_unifier unify --es-url http://localhost:9200

# ES with auth and recreate index
uv run python -m issn_unifier unify --es-url https://user:pass@es.example.com:9200 --es-recreate

# Fetch SIBiLS journals and filter unified output
uv run python -m issn_unifier fetch-sibils --version 5.0.5.8
uv run python -m issn_unifier unify --sibils-filter
```

## Data Sources & Licenses

| Source | License | URL |
|--------|---------|-----|
| Crossref | CC0 (Public Domain) | https://www.crossref.org/documentation/retrieve-metadata/rest-api/ |
| DOAJ | CC BY-SA 4.0 | https://doaj.org/docs/public-data-dump/ |
| OpenAlex | CC0 (Public Domain) | https://docs.openalex.org/additional-help/faq#licensing |
| EuropePMC | Open | https://europepmc.org/downloads |
| NLM Catalog | Public Domain (US Gov) | https://www.nlm.nih.gov/databases/download/pubmed_medline.html |
| NCBI E-utilities | Free w/ guidelines | https://www.ncbi.nlm.nih.gov/books/NBK25497/ |
| ISSN-L table | ISSN.org Terms | https://www.issn.org/services/online-services/access-to-issn-l-table/ |

**Note:** The unified output dataset is subject to the most restrictive license among the sources used. When including DOAJ data, the output is governed by **CC BY-SA 4.0**, requiring attribution and share-alike for derivative works.

## Data Pipeline

```mermaid
flowchart TD
    subgraph sources["1a. DATA SOURCES"]
        CR[("Crossref<br/>~130K titles")]
        OA[("OpenAlex<br/>~250K sources")]
        DOAJ[("DOAJ<br/>~20K OA journals")]
        PMC[("EuropePMC<br/>~50K PMC flag")]
        NLM[("NLM<br/>~35K MEDLINE")]
    end

    subgraph loaders["1b. LOADERS"]
        L1["Parse CSV/JSON/API"]
        L2["Normalize fields<br/>(ISSN, titles, countries)"]
        L3["Deduplicate within source"]
        L4["Tag with DataSource"]
    end

    subgraph issnl["2. ISSN-L REFERENCE"]
        ISSNL[("ISSN-L Table<br/>~2.5M mappings<br/>ISSN → ISSN-L")]
    end

    subgraph validation["3. VALIDATION"]
        VAL["ISSN-L Consistency Check<br/>Detect conflicting ISSNs"]
        CONF[/"issn_conflicts.csv"/]
        VAL --> CONF
    end

    subgraph priority["Source Priority"]
        PR["DOAJ &amp; NLM (6)<br>OpenAlex (5)<br/>Crossref (4)<br>EuropePMC (1)"]
    end

    subgraph merge["4. MERGE (merger.py)"]
        direction TB
        P1["Phase 1: Key Resolution<br/>ISSN → canonical key"]
        P2["Phase 2: ISSN-based Merge<br/>Group by ISSN-L"]
        P3["Phase 3: Title-based Merge<br/>Records without ISSN"]
        P4["Phase 4: Synthetic IDs<br/>NLM-xxx, ISBN-xxx, OPENALEX-xxx, TITLE-xxx"]

        P1 --> P2 --> P3 --> P4
    end

    subgraph sibils["5. SIBiLS FILTER (optional)"]
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

    subgraph output["6. OUTPUT"]
        CSV[/"unified_issn.csv"/]
        JSON[/"summary.json"/]
        ES[("Elasticsearch<br/>(optional)")]
    end

    %% Main flow
    sources --> loaders
    loaders --> merge
    loaders --> VAL
    ISSNL --> merge
    ISSNL --> VAL
    priority -.-> merge
    merge --> |"~180K unified records"| sibils
    merge --> |"without --sibils-filter"| output
    sibils --> |"~70K SIBiLS records"| output

    %% Styling
    classDef source fill:#e1f5fe,stroke:#01579b
    classDef process fill:#fff3e0,stroke:#e65100
    classDef data fill:#f3e5f5,stroke:#7b1fa2
    classDef file fill:#e8f5e9,stroke:#2e7d32
    classDef db fill:#fce4ec,stroke:#c2185b

    class CR,OA,DOAJ,PMC,NLM source
    class L1,L2,L3,L4,VAL,P1,P2,P3,P4,M1,M2,M3,M4,F1,F2,F3,F4 process
    class ISSNL,SD db
    class CONF,CSV,JSON,REM,UNM file
    class ES db
```
