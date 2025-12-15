# SIBiLS Elasticsearch Indexes - Quick Reference

SIBiLS (Swiss Institute of Bioinformatics Literature Services) provides Elasticsearch indexes for biomedical literature search.

**ES Cluster:** `http://sibils-es.lan.text-analytics.ch:9200/`
**Current Version:** `5.0.5.8`

## Available Indexes

| Index | Pattern | Documents | Description |
|-------|---------|-----------|-------------|
| MEDLINE | `sibils_med*_v{version}` | ~40M | PubMed abstracts and metadata |
| PMC | `sibils_pmc*_v{version}` | ~8M | PubMed Central full-text articles |
| Zenodo | `sibils_zen*_v{version}` | ~150K | Research data from Zenodo |

Index naming: `sibils_{collection}{year}_r{release}_v{version}`
Example: `sibils_med25_r1_v5.0.5.8`

## Journal-Related Fields

### `journal`
- **Type:** `text` (with `.keyword` subfield)
- **Present in:** All indexes
- **Content:** Full journal name/title
- **Example:** `"Nature"`, `"IEEE Conference on Artificial Intelligence"`

### `medline_ta`
- **Type:** `text` (no `.keyword` subfield - not aggregatable)
- **Present in:** MEDLINE, PMC only
- **Content:** MEDLINE Title Abbreviation (official NLM abbreviation)
- **Example:** `"Nat Med"`, `"J Biol Chem"`, `"IEEE Glob Commun Conf"`
- **Note:** May be empty for journals not in NLM catalog (~3% in PMC OA)

### `subset` (PMC only)
- **Type:** `keyword`
- **Content:** PMC license category
- **Values:**
  - `PMC OA Subset` - Open Access articles
  - `PMC Author Manuscripts` - NIH-funded manuscripts
  - `PMC+ subset` - Extended license articles

## Field Availability by Index

| Field | MEDLINE | PMC | Zenodo |
|-------|---------|-----|--------|
| `journal` | Yes | Yes | Yes |
| `medline_ta` | Yes | Yes | No |
| `subset` | No | Yes | No |

## Usage

Extract journal fields for matching:

```bash
sibils-journals fetch-sibils --version 5.0.5.8 --source both
```

Output: `data/sibils/journal_fields_v5.0.5.8.csv`

## See Also

- [Detailed documentation](sibils_es_indexes_detailed.md) - Complete field mappings, statistics, and query examples
- `sibils_journals/fetch_sibils.py` - Extraction implementation
- `sibils_journals/sibils.py` - Journal matching logic
