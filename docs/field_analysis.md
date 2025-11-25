# ISSN Data Sources: Field Analysis

This document analyzes the interesting fields available from each data source and identifies common fields that can be unified.

## Data Sources Overview

| Source | Type | Update Frequency | License |
|--------|------|------------------|---------|
| DOAJ | CSV/JSON | Weekly | CC BY-SA 4.0 |
| OpenAlex | S3 JSONL | Daily | CC0 |
| Crossref | CSV | Periodic | Public |
| EuropePMC | XML (tgz) | Weekly | Mixed |
| ROAD | RDF/XML | Archive (2018) | CC BY-NC 4.0 |

---

## 1. DOAJ (Directory of Open Access Journals)

DOAJ is the most comprehensive source for open access journal metadata with 54 columns.

### Available Fields

| Field | Description | Why It's Interesting |
|-------|-------------|---------------------|
| `Journal title` | Official journal name | Primary identifier |
| `Journal URL` | Official website | Essential for verification and discovery |
| `URL in DOAJ` | Link to DOAJ record | Cross-referencing |
| `When did the journal start to publish all content using an open license?` | OA start date | Historical OA tracking |
| `Alternative title` | Variant names | Deduplication, discovery |
| `Journal ISSN (print version)` | Print ISSN | Primary identifier |
| `Journal EISSN (online version)` | Electronic ISSN | Primary identifier |
| `Keywords` | Subject keywords | Discovery, categorization |
| `Languages in which the journal accepts manuscripts` | Accepted languages | Accessibility indicator |
| `Publisher` | Publisher name | Attribution, analysis |
| `Country of publisher` | Publisher location | Geographic analysis |
| `Other organisation` | Associated organizations | Publisher ecosystem |
| `Country of other organisation` | Location of other org | Geographic analysis |
| `Journal license` | Open license type (CC BY, CC BY-SA, etc.) | **Critical for OA compliance** |
| `License attributes` | License modifiers (NC, ND, SA) | Detailed rights information |
| `URL for license terms` | Link to license | Machine-verifiable source |
| `Machine-readable CC licensing information embedded or displayed in articles` | Embedded license metadata | Automation-friendly indicator |
| `Author holds copyright without restrictions` | Copyright policy | **Critical for author rights** |
| `Copyright information URL` | Link to copyright policy | Verifiable policy source |
| `Review process` | Peer review type (single-blind, double-blind, open) | **Quality indicator** |
| `Review process information URL` | Link to review policy | Verifiable policy |
| `Journal plagiarism screening policy` | Plagiarism check status | **Integrity indicator** |
| `URL for journal's aims & scope` | Aims & scope page | Journal focus verification |
| `URL for the Editorial Board page` | Editorial board page | Legitimacy verification |
| `URL for journal's instructions for authors` | Author guidelines | Submission information |
| `Average number of weeks between article submission and publication` | Publication speed | Efficiency metric |
| `APC` | Has article processing charges | Cost indicator |
| `APC information URL` | Link to APC info | Cost transparency |
| `APC amount` | APC cost | **Cost comparison** |
| `Journal waiver policy (for developing country authors etc)` | Fee waiver availability | Accessibility for authors |
| `Waiver policy information URL` | Link to waiver policy | Verifiable policy |
| `Has other fees` | Additional fees | Cost transparency |
| `Other fees information URL` | Link to other fees info | Cost transparency |
| `Preservation Services` | Archiving services (LOCKSS, CLOCKSS, Portico) | **Data longevity** |
| `Preservation Service: national library` | National library archiving | Long-term preservation |
| `Preservation information URL` | Link to preservation info | Verifiable archiving |
| `Deposit policy directory` | Self-archiving policies | SHERPA/RoMEO integration |
| `URL for deposit policy` | Link to deposit policy | Author self-archiving rights |
| `Persistent article identifiers` | DOI, Handle, ARK usage | **Identifier standards** |
| `Does the journal comply to DOAJ's definition of open access?` | DOAJ OA compliance | Quality assurance |
| `Continues` | Previous journal title | **Journal lineage** |
| `Continued By` | Successor journal title | **Journal lineage** |
| `LCC Codes` | Library of Congress Classification | Subject categorization |
| `Subscribe to Open` | S2O participation | OA business model |
| `Subjects` | Subject categories | Discovery, analysis |
| `Added on Date` | Date added to DOAJ | Data freshness |
| `Last updated Date` | Last update date | Data freshness |
| `Number of Article Records` | Article count in DOAJ | Productivity metric |
| `Most Recent Article Added` | Latest article date | Activity indicator |

---

## 2. OpenAlex

OpenAlex provides rich metadata with citation metrics and organizational hierarchy.

### Available Fields

| Field | Description | Why It's Interesting |
|-------|-------------|---------------------|
| `id` | OpenAlex ID | Unique identifier |
| `display_name` | Source name | Primary identifier |
| `ids` | External IDs (issn, issn_l, mag, fatcat, wikidata) | Cross-referencing |
| `type` | Source type (journal, repository, conference, ebook platform, book series) | **Source classification** |
| `abbreviated_title` | Title abbreviation (from ISSN Centre) | Citation formatting |
| `alternate_titles` | Alternative names and translations | Deduplication, discovery |
| `homepage_url` | Official website URL | **Essential for verification** |
| `issn` | List of ISSNs | Primary identifiers |
| `issn_l` | Linking ISSN | Canonical identifier |
| `is_oa` | Fully open-access status | **OA classification** |
| `is_in_doaj` | Listed in DOAJ | **Cross-validation** |
| `apc_prices` | APC with multiple currencies | Cost information |
| `apc_usd` | APC in US Dollars | **Standardized cost** |
| `works_count` | Number of hosted works | **Productivity metric** |
| `cited_by_count` | Total citing works | **Impact metric** |
| `counts_by_year` | Annual works and citations (10 years) | Trend analysis |
| `summary_stats.h_index` | h-index | **Impact metric** |
| `summary_stats.i10_index` | i10-index | Impact metric |
| `summary_stats.2yr_mean_citedness` | 2-year mean citedness | Impact metric |
| `host_organization` | Publisher/Institution ID | Publisher identification |
| `host_organization_name` | Publisher name | Attribution |
| `host_organization_lineage` | Parent organization hierarchy | **Publisher ecosystem** |
| `host_organization_lineage_names` | Parent organization names | Publisher relationships |
| `country_code` | ISO country code | Geographic analysis |
| `is_core` | CWTS "core source" designation | Quality indicator |
| `societies` | Associated professional organizations | **Academic affiliations** |
| `x_concepts` | Subject concepts (deprecated, use Topics) | Subject categorization |
| `works_api_url` | API endpoint for works | Data access |
| `created_date` | Creation timestamp | Data provenance |
| `updated_date` | Last modification timestamp | Data freshness |

---

## 3. Crossref

Crossref provides DOI registration data. The title list CSV has limited fields; richer data available via API.

### Available Fields (Title List CSV)

| Field | Description | Why It's Interesting |
|-------|-------------|---------------------|
| `Title` | Journal/publication title | Primary identifier |
| `Publisher` | Publisher name | Attribution |
| `Print ISSN` | Print ISSN | Primary identifier |
| `Electronic ISSN` | Electronic ISSN | Primary identifier |
| `DOI prefix` | Publisher's DOI prefix | **Publisher identification** |

### Additional Fields (via API)

| Field | Description | Why It's Interesting |
|-------|-------------|---------------------|
| `member` | Crossref member ID | Publisher identification |
| `container-title` | Canonical journal title | Authoritative title |
| `license` | Article-level license information | Rights information (aggregated) |
| `deposited` | Last metadata update | Data freshness |
| `coverage` | Metadata completeness statistics | Data quality indicator |
| `subjects` | Subject categories | Categorization |

---

## 4. EuropePMC

EuropePMC is article-centric; journal metadata is extracted from article records.

### Available Fields

| Field | Description | Why It's Interesting |
|-------|-------------|---------------------|
| `journalTitle` | Journal name | Primary identifier |
| `journalIssn` | Print and electronic ISSNs | Primary identifiers |
| `isOpenAccess` | OA status flag | **OA classification** |
| `inEPMC` | Indexed in Europe PMC | Indexing status |
| `inPMC` | Indexed in PubMed Central | Indexing status |
| `hasPDF` | Full-text PDF available | Content availability |
| `citedByCount` | Citation count | **Impact metric** |
| `hasReferences` | References available | Data completeness |
| `hasTextMinedTerms` | Text mining available | Data enrichment |
| `hasLabsLinks` | External tool links | Data enrichment |
| `firstIndexDate` | First indexing date | Historical data |
| `firstPublicationDate` | First publication date | Publication timing |
| `license` (article-level) | CC license information | Rights information |

*Note: Limited journal-level fields; primarily useful for citation counts and indexing status*

---

## 5. ROAD (via ISSN International Centre)

ROAD provides authoritative ISSN data enriched with indexing information.

### Available Fields

| Field | Description | Why It's Interesting |
|-------|-------------|---------------------|
| `title` | Official title (from ISSN authority) | **Authoritative title** |
| `publisher` | Publisher name | Attribution |
| `URL` | Journal website | Discovery |
| `country` | Country of publication | Geographic analysis |
| `frequency` | Publication frequency | Activity indicator |
| `indexed by` | A&I databases coverage | **Visibility indicator** |
| `abstracted in` | Abstracting services | Visibility indicator |
| `registries` | DOAJ, Latindex, Keepers registry | Quality indicators |
| `journal indicators` | Scopus, etc. | **Quality metrics** |
| `subject` | Subject classification | Categorization |
| `start date` | Publication start | Historical data |
| `format` | Medium (online, print) | Format information |

*Note: 2018 archive is dated; current ROAD requires API access*

---

## Common Fields Comparison

| Field Category | DOAJ | OpenAlex | Crossref | EuropePMC | ROAD |
|----------------|:----:|:--------:|:--------:|:---------:|:----:|
| **Identifiers** |
| ISSN (Print) | ✅ | ✅ | ✅ | ✅ | ✅ |
| ISSN (Electronic) | ✅ | ✅ | ✅ | ✅ | ✅ |
| ISSN-L | ❌ | ✅ | ❌ | ❌ | ✅ |
| DOI Prefix | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Basic Metadata** |
| Title | ✅ | ✅ | ✅ | ✅ | ✅ |
| Alternative Titles | ✅ | ✅ | ❌ | ❌ | ❌ |
| Publisher | ✅ | ✅ | ✅ | ❌ | ✅ |
| Country | ✅ | ✅ | ❌ | ❌ | ✅ |
| Language | ✅ | ❌ | ❌ | ❌ | ❌ |
| **URLs** |
| Journal Website | ✅ | ✅ | ❌ | ❌ | ✅ |
| License URL | ✅ | ❌ | ❌ | ❌ | ❌ |
| Review Process URL | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Open Access** |
| OA Status | ✅ (implicit) | ✅ | ❌ | ✅ | ✅ (implicit) |
| In DOAJ | ✅ (self) | ✅ | ❌ | ❌ | ✅ |
| **Licensing** |
| License Type | ✅ | ❌ | ⚠️ (article) | ⚠️ (article) | ❌ |
| License Attributes | ✅ | ❌ | ❌ | ❌ | ❌ |
| Machine-readable License | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Editorial** |
| Review Process | ✅ | ❌ | ❌ | ❌ | ❌ |
| Plagiarism Screening | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Copyright** |
| Author Copyright | ✅ | ❌ | ❌ | ❌ | ❌ |
| Copyright URL | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Costs** |
| APC Amount | ✅ | ✅ | ❌ | ❌ | ❌ |
| APC Currency | ✅ | ✅ | ❌ | ❌ | ❌ |
| Waiver Policy | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Preservation** |
| Archiving Services | ✅ | ❌ | ❌ | ❌ | ❌ |
| Deposit Policy | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Metrics** |
| Works Count | ✅ | ✅ | ❌ | ❌ | ❌ |
| Citation Count | ❌ | ✅ | ❌ | ✅ | ❌ |
| h-index | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Lineage** |
| Continues | ✅ | ❌ | ❌ | ❌ | ❌ |
| Continued By | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Indexing** |
| A&I Databases | ❌ | ❌ | ❌ | ✅ | ✅ |
| Registries | ❌ | ✅ | ❌ | ❌ | ✅ |

---

## Recommended Fields to Add

### High Priority (Unique & Critical)

These fields are unique to specific sources and provide critical information:

| Field | Source | Rationale |
|-------|--------|-----------|
| `journal_url` | DOAJ, OpenAlex, ROAD | Official website - essential for verification |
| `license` | DOAJ | Open license type - critical for OA compliance |
| `license_attributes` | DOAJ | Specific license terms (NC, ND, SA) |
| `review_process` | DOAJ | Peer review type - quality indicator |
| `preservation_services` | DOAJ | Archiving - data longevity assurance |
| `works_count` | OpenAlex | Productivity metric |
| `cited_by_count` | OpenAlex | Impact/visibility metric |

### Medium Priority (Useful Enrichment)

| Field | Source | Rationale |
|-------|--------|-----------|
| `license_url` | DOAJ | Machine-verifiable license source |
| `review_process_url` | DOAJ | Verifiable review policy |
| `copyright_author` | DOAJ | Author rights assessment |
| `copyright_url` | DOAJ | Verifiable copyright policy |
| `plagiarism_screening` | DOAJ | Integrity indicator |
| `deposit_policy` | DOAJ | Self-archiving rights (SHERPA/RoMEO) |
| `h_index` | OpenAlex | Impact metric |
| `is_in_doaj` | OpenAlex | Cross-validation flag |

### Lower Priority (Nice to Have)

| Field | Source | Rationale |
|-------|--------|-----------|
| `continues` | DOAJ | Journal lineage tracking |
| `continued_by` | DOAJ | Journal succession |
| `societies` | OpenAlex | Academic affiliations |
| `apc_waiver_policy` | DOAJ | Accessibility information |
| `publication_time_weeks` | DOAJ | Efficiency metric |
| `editorial_board_url` | DOAJ | Legitimacy verification |

---

## Implementation Notes

### Data Type Considerations

- **URLs**: Store as strings, validate format
- **Boolean flags**: `is_oa`, `plagiarism_screening`, `author_copyright`
- **Lists**: `preservation_services` (can have multiple: LOCKSS, CLOCKSS, Portico)
- **Numeric**: `works_count`, `cited_by_count`, `h_index`, `publication_time_weeks`

### Merge Strategy

1. **URLs**: Prefer DOAJ > OpenAlex > ROAD (most authoritative for OA journals)
2. **Metrics**: Prefer OpenAlex (most comprehensive and up-to-date)
3. **License info**: DOAJ only (unique source)
4. **Review process**: DOAJ only (unique source)

### Data Quality Notes

- DOAJ data is self-reported by journals but verified by DOAJ
- OpenAlex metrics are computed from indexed works
- ROAD 2018 archive is dated; use for historical reference only
- EuropePMC is article-centric; journal metadata may be incomplete
