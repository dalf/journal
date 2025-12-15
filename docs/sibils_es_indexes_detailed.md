# SIBiLS Elasticsearch Indexes - Detailed Documentation

## Overview

SIBiLS (Swiss Institute of Bioinformatics Literature Services) provides Elasticsearch indexes containing biomedical and scientific literature. These indexes are used for literature search, text mining, and journal validation.

**ES Cluster URL:** `http://sibils-es.lan.text-analytics.ch:9200/`
**Current Version:** `5.0.5.8`

## Index Collections

### MEDLINE (`sibils_med*`)

The MEDLINE index contains abstracts and metadata from PubMed/MEDLINE.

| Property | Value |
|----------|-------|
| Pattern | `sibils_med*_v{version}` |
| Example | `sibils_med25_r1_v5.0.5.8` |
| Documents | ~40 million |
| Source | NLM MEDLINE database |

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `journal` | text | Full journal name |
| `medline_ta` | text | MEDLINE title abbreviation |
| `title` | text | Article title |
| `abstract` | text | Article abstract |
| `authors` | text | Author names |
| `pmid` | keyword | PubMed ID |
| `doi` | keyword | Digital Object Identifier |
| `publication_date` | date | Publication date |
| `mesh_terms` | text | MeSH subject headings |
| `keywords` | keyword | Article keywords |
| `language` | keyword | Language code |

### PMC (`sibils_pmc*`)

The PMC index contains full-text articles from PubMed Central.

| Property | Value |
|----------|-------|
| Pattern | `sibils_pmc*_v{version}` |
| Example | `sibils_pmc25_r1_v5.0.5.8` |
| Documents | ~8 million |
| Source | PubMed Central |

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `journal` | text | Full journal name |
| `medline_ta` | text | MEDLINE title abbreviation |
| `subset` | keyword | PMC subset category |
| `title` | text | Article title |
| `abstract` | text | Article abstract |
| `full_text` | text | Complete article text |
| `pmcid` | keyword | PMC ID |
| `pmid` | keyword | PubMed ID (if available) |
| `doi` | keyword | Digital Object Identifier |
| `figures_captions` | text | Figure captions |
| `tables` | text | Table content |
| `publication_date` | date | Publication date |

### Zenodo (`sibils_zen*`)

The Zenodo index contains research data and publications from Zenodo.

| Property | Value |
|----------|-------|
| Pattern | `sibils_zen*_v{version}` |
| Example | `sibils_zen25_r1_v5.0.5.8` |
| Documents | ~150,000 |
| Source | Zenodo.org |

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `journal` | text | Journal name (if applicable) |
| `title` | text | Record title |
| `authors` | text | Author/creator names |
| `creators` | text | Zenodo creators field |
| `doi` | keyword | Digital Object Identifier |
| `zenodo_id` | keyword | Zenodo record ID |
| `resource_type` | keyword | Type (Journal article, Dataset, etc.) |
| `communities` | keyword | Zenodo communities |
| `creation_date` | date | Record creation date |

**Note:** Zenodo does not have the `medline_ta` field since it contains non-MEDLINE content.

### Other Indexes

| Index | Pattern | Documents | Description |
|-------|---------|-----------|-------------|
| Clinical Trials | `sibils_cli*` | ~545K | Clinical trial records |
| Planta | `sibils_pla*` | ~985K | Plant science literature |
| Supplementary | `sibils_sup*` | ~30M | Supplementary materials |

## Journal-Related Fields in Detail

### `journal` Field

The `journal` field contains the full journal name as it appears in the source database.

**Type:** `text` with `.keyword` subfield
**Present in:** All indexes

**Examples:**
```
"Nature"
"IEEE Conference on Artificial Intelligence"
"Bonner zoologische Beiträge : Herausgeber: Zoologisches Forschungsinstitut"
"Journal of the Arnold Arboretum"
```

**Querying:**
```json
// Full-text search
{"match": {"journal": "nature medicine"}}

// Exact match
{"term": {"journal.keyword": "Nature Medicine"}}

// Aggregation
{"aggs": {"journals": {"terms": {"field": "journal.keyword", "size": 100}}}}
```

### `medline_ta` Field

The `medline_ta` field contains the official MEDLINE Title Abbreviation assigned by NLM.

**Type:** `text` (no `.keyword` subfield)
**Present in:** MEDLINE, PMC only

> **Note:** Unlike `journal`, the `medline_ta` field does not have a `.keyword` subfield, making it unsuitable for direct aggregations. Use scroll API with `_source` or `top_hits` sub-aggregation to analyze medline_ta values.

**Possible values:**
1. **Text abbreviation** (most common): Standard NLM abbreviation
   - `"Nat Med"` for Nature Medicine
   - `"J Biol Chem"` for Journal of Biological Chemistry
   - `"IEEE Glob Commun Conf"` for IEEE Global Communications Conference

2. **Numeric NLM ID** (rare, PMC only): For journals in PMC but not in MEDLINE
   - The code handles this case, but current data shows 0 occurrences

3. **Empty/missing**: Journals without NLM cataloging
   - ~48% of extracted journal entries have empty `medline_ta`

**Querying:**
```json
// Full-text search (no .keyword available)
{"match": {"medline_ta": "Nat Med"}}

// Find documents with medline_ta
{"exists": {"field": "medline_ta"}}

// Find documents without medline_ta
{"bool": {"must_not": {"exists": {"field": "medline_ta"}}}}

// Get medline_ta via top_hits (since no .keyword for aggregation)
{
  "aggs": {
    "by_journal": {
      "terms": {"field": "journal.keyword", "size": 100},
      "aggs": {
        "sample_ta": {
          "top_hits": {"size": 1, "_source": ["medline_ta"]}
        }
      }
    }
  }
}
```

### `subset` Field (PMC Only)

The `subset` field indicates the PMC license/access category.

**Type:** `keyword`
**Present in:** PMC only

**Values:**

| Value | Documents | Description |
|-------|-----------|-------------|
| `PMC OA Subset` | 7,081,271 | Open Access - freely available |
| `PMC Author Manuscripts` | 909,003 | NIH-funded author manuscripts |
| `PMC+ subset` | 34,886 | Extended license articles |

**Querying:**
```json
// Filter by Open Access
{"term": {"subset": "PMC OA Subset"}}

// Aggregate by subset
{"aggs": {"subsets": {"terms": {"field": "subset"}}}}
```

## PMC Subset vs Journal/medline_ta Analysis

### Per-Subset Journal Statistics

| Subset | Documents | Unique Journals | With medline_ta | % with TA |
|--------|-----------|-----------------|-----------------|-----------|
| PMC OA Subset | 7,081,271 | 19,948 | 19,384 | 97.2% |
| PMC Author Manuscripts | 909,003 | 18,974 | 18,974 | 100% |
| PMC+ subset | 34,886 | 787 | 787 | 100% |

### Cross-Subset Analysis

| Metric | Value |
|--------|-------|
| Total unique journals in PMC | 35,105 |
| Journals with medline_ta | 34,541 (98.4%) |
| Unique medline_ta values | 33,583 |

### Journal Overlap Between Subsets

| Overlap | Count |
|---------|-------|
| OA ∩ Author Manuscripts | 4,416 journals |
| OA ∩ PMC+ | 160 journals |
| Author Manuscripts ∩ PMC+ | 66 journals |
| All three subsets | 38 journals |

### Key Insights

1. **Author Manuscripts and PMC+ have 100% medline_ta coverage** - all journals in these subsets are catalogued in MEDLINE
2. **OA Subset has 564 journals without medline_ta** - these are Open Access-only journals not in MEDLINE
3. **Most journals are subset-exclusive** - only ~4,400 journals appear in multiple subsets
4. **PMC+ is very small** (787 journals) compared to OA (19,948) and Author Manuscripts (18,974)

### Implications for Journal Matching

- When matching against PMC journals:
  - Author Manuscripts provide reliable medline_ta for cross-referencing with NLM catalog
  - OA Subset may require title-based matching for ~3% of journals without medline_ta
  - PMC+ has few unique journals (most overlap with OA)

## Data Statistics (v5.0.5.8)

### Extracted Journal Data

The `fetch-sibils` command extracts unique (journal, medline_ta) pairs from MEDLINE and PMC indexes:

| Metric | Value |
|--------|-------|
| Total unique pairs | 72,890 |
| With medline_ta | 37,776 (52%) |
| Empty medline_ta | 35,114 (48%) |
| Numeric medline_ta | 0 (none in current data) |

### Index Document Counts

| Index | Documents |
|-------|-----------|
| `sibils_med25_r1_v5.0.5.8` | 39,707,316 |
| `sibils_pmc25_r1_v5.0.5.8` | 8,025,160 |
| `sibils_zen25_r1_v5.0.5.8` | 150,143 |

## Collection Differences

| Aspect | MEDLINE | PMC | Zenodo |
|--------|---------|-----|--------|
| **Content type** | Abstracts/metadata | Full-text articles | Research data |
| **journal field** | Always present | Always present | Present if journal article |
| **medline_ta** | Always present | Always present | Not available |
| **subset** | Not available | OA/Author/PMC+ | Not available |
| **Full text** | No | Yes | Varies |
| **Primary ID** | PMID | PMCID | Zenodo ID |
| **Source** | NLM MEDLINE | PubMed Central | Zenodo.org |

## Extraction Process

### Command

```bash
sibils-journals fetch-sibils [options]
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--version` | `5.0.5.8` | SIBiLS version |
| `--source` | `both` | Index to extract (`medline`, `pmc`, `both`) |
| `--output-dir` | `data/sibils` | Output directory |
| `--batch-size` | `10000` | Batch size for scrolling |
| `--es-url` | `http://sibils-es.lan.text-analytics.ch:9200/` | ES URL |

### Output

CSV file: `data/sibils/journal_fields_v{version}.csv`

```csv
journal,medline_ta
"Nature","Nature"
"Nature Medicine","Nat Med"
"Journal of Biological Chemistry","J Biol Chem"
```

### Extraction Methods

**MEDLINE:** Uses scroll API for document-level extraction
```python
es.search(
    index="sibils_med*_v5.0.5.8",
    query={"match_all": {}},
    source=["journal", "medline_ta"],
    scroll="5m",
    size=10000
)
```

**PMC:** Uses composite aggregation on `journal.keyword` with `top_hits` for `medline_ta`

> **Note:** The code in `fetch_sibils.py` attempts to use `medline_ta.keyword`, but this field doesn't exist in the current mapping. The extraction still works by sampling documents.

```python
# Effective approach: aggregate by journal, sample medline_ta
{
    "aggs": {
        "journals": {
            "composite": {
                "sources": [
                    {"journal": {"terms": {"field": "journal.keyword"}}}
                ]
            },
            "aggs": {
                "sample_doc": {
                    "top_hits": {"size": 1, "_source": ["medline_ta"]}
                }
            }
        }
    }
}
```

## Usage in Journal Matching

The extracted SIBiLS data is used to filter and validate unified journal records:

### Matching Phases

1. **Phase 1: medline_abbreviation match**
   - Match unified `medline_abbreviation` against SIBiLS `medline_ta`
   - Most reliable matching method

2. **Phase 1b: NLM ID match**
   - Match unified `nlm_id` against numeric `medline_ta` values
   - For PMC journals not in MEDLINE

3. **Phase 2: Title match**
   - Match normalized title against SIBiLS `journal`
   - Uses title normalization (lowercase, remove punctuation)

4. **Phase 3: Alternative titles match**
   - Match `alternative_titles` against SIBiLS `journal`
   - Catches aliases and variant spellings

### Title Variant Generation

The matching includes "Journal of X" ↔ "X" variant generation with safety measures:
- Requires 3+ words (blocks "Neurology", "Clinical Medicine")
- Blacklists 72 generic terms (medicine, biology, clinical, etc.)
- Conflict detection: skips if both forms exist

## Query Examples

### Find all articles from a journal
```json
GET sibils_med25_r1_v5.0.5.8/_search
{
  "query": {
    "match": {"journal": "Nature Medicine"}
  }
}
```

### Get unique journal names
```json
GET sibils_med25_r1_v5.0.5.8/_search
{
  "size": 0,
  "aggs": {
    "journals": {
      "terms": {
        "field": "journal.keyword",
        "size": 1000
      }
    }
  }
}
```

### Find journals by medline_ta pattern
```json
GET sibils_pmc25_r1_v5.0.5.8/_search
{
  "query": {
    "match_phrase_prefix": {"medline_ta": "J "}
  },
  "_source": ["journal", "medline_ta"],
  "size": 10
}
```

> **Note:** Since `medline_ta` lacks a `.keyword` subfield, use full-text queries or sample via `top_hits`.

### PMC subset distribution
```json
GET sibils_pmc25_r1_v5.0.5.8/_search
{
  "size": 0,
  "aggs": {
    "by_subset": {
      "terms": {"field": "subset"}
    }
  }
}
```

## Related Files

| File | Description |
|------|-------------|
| `sibils_journals/fetch_sibils.py` | SIBiLS extraction implementation |
| `sibils_journals/sibils.py` | Journal filtering and matching |
| `sibils_journals/config.py` | ES URL and version configuration |
| `data/sibils/journal_fields_v*.csv` | Extracted journal data |

## Index Naming Convention

Pattern: `sibils_{collection}{year}_r{release}_v{version}`

| Component | Values | Description |
|-----------|--------|-------------|
| collection | `med`, `pmc`, `zen`, `cli`, `pla`, `sup` | Data source |
| year | `24`, `25` | Year of release |
| release | `r1` | Release number |
| version | `5.0.5.8` | Version number |

**Examples:**
- `sibils_med25_r1_v5.0.5.8` - MEDLINE 2025 release 1
- `sibils_pmc25_r1_v5.0.5.8` - PMC 2025 release 1
- `sibils_zen25_r1_v5.0.5.8` - Zenodo 2025 release 1
