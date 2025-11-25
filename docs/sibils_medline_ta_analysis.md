# SIBiLS medline_ta Field Analysis

The `medline_ta` field in SIBiLS Elasticsearch indices contains multiple types of identifiers, not just MEDLINE title abbreviations.

## Overview

**Indices analyzed:**
- `sibils_med25_r1_v5.0.5.8` (MEDLINE) - 39.7M docs
- `sibils_pmc25_r1_v5.0.5.8` (PMC) - 8.0M docs

**Processed CSV:** `journal_fields_v5.0.5.8.csv` - 75,035 unique journal entries

## Raw Elasticsearch Data

In the raw SIBiLS Elasticsearch indices, the `medline_ta` field contains:

| Type | MEDLINE | PMC OA Subset | PMC Author Manuscripts | PMC+ |
|------|---------|---------------|------------------------|------|
| Abbreviation | ~100% | ~99% | ~1% | ~80% |
| NLM ID (numeric) | 0 | 64,566 docs | 878,007 docs | 7,194 docs |
| ISBN-13 | 0 | 7,448 docs | 0 | 0 |
| DOI | 266 docs | 906 docs | 8,930 docs | 0 |

**Key findings:**
- **ISBN-13**: Only in PMC OA Subset (books/book chapters)
- **NLM ID (numeric)**: Primarily in PMC Author Manuscripts (~97%)
- **DOI**: Primarily in PMC Author Manuscripts
- **MEDLINE**: Almost exclusively abbreviations

## Processed CSV Structure

During fetch (`sibils_fetch.py`), numeric NLM IDs are **extracted to a separate `nlm_id` column**:

```python
# In extract_from_pmc():
if raw_medline_ta and raw_medline_ta.isdigit():
    # Numeric value -> it's an NLM ID, not an abbreviation
    unique_tuples.add((journal, "", raw_medline_ta))  # -> nlm_id column
else:
    unique_tuples.add((journal, raw_medline_ta, ""))  # -> medline_ta column
```

## Field Breakdown (Processed CSV)

### medline_ta column

| Type | Count | % | Pattern |
|------|------:|--:|---------|
| Abbreviation | 52,094 | 69.4% | Text |
| Empty | 19,911 | 26.5% | - |
| ISBN-13 | 2,798 | 3.7% | `^97[89]-` |
| NLM ID (R-suffix) | 183 | 0.2% | `^\d+R$` |
| DOI | 49 | 0.1% | `^10\.\d{4,}/` |

### nlm_id column

| Type | Count | % |
|------|------:|--:|
| Empty | 55,756 | 74.3% |
| Numeric (extracted from PMC) | 19,279 | 25.7% |

### Empty medline_ta breakdown

Of the 19,911 entries with empty `medline_ta`:

| Has nlm_id? | Count | % |
|-------------|------:|--:|
| Yes (PMC journals) | 19,279 | 96.8% |
| No (title only) | 632 | 3.2% |

The 632 entries with **neither** `medline_ta` nor `nlm_id` are orphan records with only a journal title. These appear to be journals indexed in PMC without MEDLINE abbreviations or NLM IDs (e.g., "Advances in...", "Journal of...", Elsevier serials).

## Identifier Patterns

### ISBN-13 (Books)

Records with ISBN indicate **books/monographs**, not journals.

**Pattern:** `^97[89]-`

**Examples:**
```
journal: 100 Tips to Avoid Mistakes in Academic Writing
medline_ta: 978-3-030-44214-9

journal: 13th International Conference on Theory and Application...
medline_ta: 978-3-030-04164-9
```

### DOI-based Identifiers

Some entries use DOI patterns, often with embedded ISSN.

**Pattern:** `^10\.\d{4,}/`

**Examples:**
```
journal: Agricultural & Environmental Letters
medline_ta: 10.1002/(ISSN)2471-9625

journal: British Journal of Management
medline_ta: 10.1111/(ISSN)1467-8551
```

### NLM ID with R-suffix

Legacy internal NLM identifiers, numeric with 'R' suffix.

**Pattern:** `^\d+R$`

**Examples:**
```
journal: Acta Biochimica Polonica
medline_ta: 14520300R

journal: Advances in Clinical Chemistry
medline_ta: 2985173R
```

### NLM ID (numeric)

Pure numeric NLM IDs from PMC for journals not indexed in MEDLINE. These are **extracted to the `nlm_id` column** during fetch.

**Pattern:** `^\d+$` (in raw ES data)

**Examples:**
```
journal: Rheumatology (Oxford)
nlm_id: 100883501

journal: BMC Medical Genomics
nlm_id: 101319628
```

### Standard Abbreviations

Normal MEDLINE title abbreviations (majority of records).

**Examples:**
```
journal: Nature
medline_ta: Nature

journal: The Lancet
medline_ta: Lancet
```

## Implications for Journal Matching

When filtering unified data against SIBiLS:

1. **Books (ISBN):** ~2,800 entries are books, not journals. Consider filtering these out when adding unmatched SIBiLS entries as new journal records.

2. **Conference Proceedings:** Many book entries are conference proceedings (detectable by title patterns like "conference", "proceedings", "symposium").

3. **Empty medline_ta:** ~20,000 entries have no abbreviation - these are PMC-only journals with numeric `nlm_id`.

4. **NLM ID matching:** The 19,279 numeric NLM IDs enable matching PMC journals that aren't in MEDLINE.

## Detection Regex

```python
import re

# ISBN-13 (books)
ISBN_PATTERN = re.compile(r'^97[89]-')

# DOI-based
DOI_PATTERN = re.compile(r'^10\.\d{4,}/')

# NLM R-suffix ID
NLM_R_PATTERN = re.compile(r'^\d+R$')

# NLM ID numeric (in raw ES data, before extraction)
NLM_ID_PATTERN = re.compile(r'^\d+$')

def classify_medline_ta(value: str) -> str:
    """Classify medline_ta value type."""
    if not value:
        return 'empty'
    if ISBN_PATTERN.match(value):
        return 'isbn'
    if DOI_PATTERN.match(value):
        return 'doi'
    if NLM_R_PATTERN.match(value):
        return 'nlm_r_id'
    if NLM_ID_PATTERN.match(value):
        return 'nlm_id_numeric'
    return 'abbreviation'
```
