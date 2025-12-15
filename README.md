# SIBiLS Journals

Journal repository for SIBiLS. Unifies journal metadata from multiple sources (OpenAlex, Crossref, DOAJ, PMC, NLM Catalog, LSIOU, J-STAGE, Wikidata) into a single normalized dataset using ISSN-L as the primary key, with fallback to NLM ID or OpenAlex ID for journals without ISSN. Includes MEDLINE indexing status, PMC agreement details (status, embargo, last deposit year), and journal predecessor/successor relationships. Exports to CSV and optionally to Elasticsearch.

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
sibils-journals download

# Fetch SIBiLS journal list (optional, for filtering)
sibils-journals fetch-sibils

# Unify and export
sibils-journals unify --sibils-filter
```

### With uv

```bash
# Download source data
uv run python -m sibils_journals download

# Fetch SIBiLS journal list (optional, for filtering)
uv run python -m sibils_journals fetch-sibils

# Unify and export
uv run python -m sibils_journals unify --sibils-filter
```

Output: `data/unified/unified_issn.csv`

## Options

```bash
usage: sibils_journals unify [-h] [--input-dir INPUT_DIR] [--output-dir OUTPUT_DIR] [--output-file OUTPUT_FILE] [--skip-checksum] [-v] [--sibils-filter [VERSION]]
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
  sibils_journals unify                                        # Use default directories
  sibils_journals unify --output-file journals.csv             # Custom output filename
  sibils_journals unify --skip-checksum                        # Disable ISSN checksum validation
  sibils_journals unify --es-url http://localhost:9200         # Export to local Elasticsearch
  sibils_journals unify --es-url https://u:p@es.example.com:9200 --es-recreate  # With auth, recreate index
```

### Examples

```bash
# Download specific sources
uv run python -m sibils_journals download --sources crossref,doaj,lsiou

# Download all sources non-interactively
uv run python -m sibils_journals download --yes

# Unify with custom output
uv run python -m sibils_journals unify --output-file journals.csv

# Export to Elasticsearch
uv run python -m sibils_journals unify --es-url http://localhost:9200

# ES with auth and recreate index
uv run python -m sibils_journals unify --es-url https://user:pass@es.example.com:9200 --es-recreate

# Fetch SIBiLS journals and filter unified output
uv run python -m sibils_journals fetch-sibils --version 5.0.5.8
uv run python -m sibils_journals unify --sibils-filter
```

## Data Sources & Licenses

| Source | License | Updates | Records | URL |
|--------|---------|---------|---------|-----|
| Crossref | [Public Domain](https://www.crossref.org/documentation/retrieve-metadata/) | [Live](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) | 130,398 | https://api.crossref.org/ |
| DOAJ | [CC0](https://doaj.org/terms/) | [Weekly](https://doaj.org/docs/public-data-dump/) | 22,234 | https://doaj.org/docs/public-data-dump/ |
| OpenAlex | [CC0](https://docs.openalex.org/additional-help/faq#licensing) | [Monthly](https://docs.openalex.org/additional-help/faq) | 255,216 | https://docs.openalex.org/additional-help/faq#licensing |
| PMC Journal List | [US Gov't - attribution req.](https://www.nlm.nih.gov/databases/download.html) | Ongoing | 4,344 | https://pmc.ncbi.nlm.nih.gov/journals/ |
| NLM Catalog | [US Gov't - attribution req.](https://www.nlm.nih.gov/databases/download.html) | [Daily](https://www.nlm.nih.gov/bsd/serfile_addedinfo.html) | 41,465 | https://www.nlm.nih.gov/databases/download.html |
| LSIOU | [Public Domain](https://www.nlm.nih.gov/tsd/serials/lsiou.html) | [Discontinued](https://www.nlm.nih.gov/tsd/serials/lsiou.html) | 15,435 | https://www.nlm.nih.gov/tsd/serials/lsiou.html |
| J-STAGE | [Platform - see terms](https://www.jstage.jst.go.jp/static/pages/TermsAndPolicies/ForIndividuals/-char/en) | Ongoing | 4,149 | https://www.jstage.jst.go.jp/ |
| Wikidata | [CC0](https://www.wikidata.org/wiki/Wikidata:Data_access) | [Live](https://query.wikidata.org/) | 11,302 | https://www.wikidata.org/wiki/Wikidata:Data_access |
| NCBI E-utilities | [Free w/ guidelines](https://www.ncbi.nlm.nih.gov/books/NBK25497/) | Live | — | https://www.ncbi.nlm.nih.gov/books/NBK25497/ |
| ISSN-L table | [ISSN.org Terms](https://www.issn.org/services/online-services/access-to-issn-l-table/) | [Daily](https://www.issn.org/services/online-services/access-to-issn-l-table/) | — | https://www.issn.org/services/online-services/access-to-issn-l-table/ |

**Note:** Most metadata sources (Crossref, DOAJ, OpenAlex, Wikidata, NLM) are CC0/public domain. Users should review individual source licenses for their specific use case. NCBI E-utilities is used to determine MEDLINE indexing status (`medline_indexed` field), not as a primary journal metadata source. J-STAGE is a publishing platform; article licenses vary by journal—journal metadata (ISSN, title, publisher) used here is factual information.

## Developer Documentation

For Python API, package structure, and data pipeline diagram, see [src/sibils_journals/README.md](src/sibils_journals/README.md).
