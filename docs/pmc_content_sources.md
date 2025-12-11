# PMC Data in sibils-journals

> **Policy status as of:** December 2024
>
> **This document will become stale.** Funder policies evolved rapidly during 2023-2024 and will continue to do so. Anyone using this operationally in 2025 or later should verify current requirements directly with funders. Numerical values are **snapshot values**, not structural constants.

## 1. What `is_pmc_indexed` Means

### The Short Version

The `is_pmc_indexed` field in sibils-journals indicates whether a journal has a **formal deposit agreement** with PubMed Central—not whether it has any PMC content.

| If `is_pmc_indexed` is... | It means... | It does NOT mean... |
|---------------------------|-------------|---------------------|
| `true` | Journal has (or has had) a publisher deposit agreement with PMC | All articles are in PMC, or journal is actively depositing |
| `false` | No formal agreement found | No PMC content exists (author deposits may still be present) |

**Key limitation:** This boolean conflates radically different situations:

| Scenario | is_pmc_indexed | Actual PMC coverage |
|----------|----------------|---------------------|
| Fully OA journal with publisher agreement | true | ~100% of articles |
| Subscription journal, one NIH manuscript from 2010 | true | <1% of articles |
| Journal with no PMC content | false | 0% |

Do not over-interpret this field.

### The Gap: ~4,400 vs ~20,800 Journals

| Source | Journals | What It Represents |
|--------|----------|-------------------|
| **PMC Journal List** (jlist.csv) | ~4,400 | Formal publisher deposit agreements |
| **EuropePMC bulk metadata** | ~20,800 | Journals with ≥1 full-text article in PMC |
| **Difference** | ~16,400 | Journals with PMC content but no formal agreement |

The ~16,400 journals with PMC content but no publisher agreement typically have content from **author-deposited manuscripts** under funder mandates (NIH, HHMI, Gates, Wellcome, etc.). See [Appendix: Funder Policy Context](#appendix-funder-policy-context) for details.

---

## 2. Data Sources & Methodology

### PMC Journal List (~4,400 journals)

- **Source:** `jlist.csv` from `https://cdn.ncbi.nlm.nih.gov/pmc/home/jlist.csv`
- **Method:** Count unique journals (rows) with at least one valid ISSN
- **Date:** December 2024
- **What it includes:** Journals with formal PMC deposit agreements (full participation or selective deposit)

> **Caveat:** The PMC Journal List includes journals that have **ceased publication** or are **no longer actively depositing**. A journal appearing in jlist.csv means "has ever had a PMC deposit agreement," not "is currently an active PMC participant."

### EuropePMC Bulk Metadata (~20,800 journals)

- **Source:** `PMCLiteMetadata.tgz` from `https://europepmc.org/ftp/pmclitemetadata/`
- **Method:** Extract unique journal ISSNs from article-level XML metadata
- **Date:** December 2024
- **What it includes:** Any journal with ≥1 full-text article in PMC (regardless of deposit pathway)
- **What it excludes:** PubMed abstracts, patents, Agricola records

> **Caveat:** We assume PMCLiteMetadata represents all journals with full-text articles in PMC. Europe PMC describes this as a PMC full-text metadata dump, but does not explicitly document it as complete.

### Important Limitations

Both figures are **cross-sectional snapshots**, not longitudinal time series. Do not use for:

- Tracking changes in PMC participation over time
- Measuring "current" OA-friendliness of journals
- Assuming active deposit relationships

### Current Implementation

The sibils-journals database uses the **PMC Journal List** (mapped to `is_pmc_indexed`), representing formal participation rather than comprehensive PMC content presence.

| Data Source | Field | Meaning |
|-------------|-------|---------|
| PMC Journal List | `is_pmc_indexed=true` | Journal has (or has had) formal deposit agreement |

---

## 3. Recommended Field Design

### Terminology

The term "indexed" is overloaded:

| Term | Meaning | Example |
|------|---------|---------|
| **PubMed indexed** | Articles discoverable via PubMed (abstracts) | MEDLINE journals |
| **PMC archived** | Has full-text content in PMC | Publisher or author deposits |
| **PMC participation** | Has formal deposit agreement | PMC Journal List |

PMC itself uses "participation"—not "indexed." The legacy field name `is_pmc_indexed` conflates these concepts.

### Recommended Fields

For clarity, consider replacing a single boolean with explicit fields:

| Field | Type | Source | Meaning |
|-------|------|--------|---------|
| `has_pmc_agreement` | boolean | PMC Journal List | Journal has (or has had) formal deposit agreement |
| `has_pmc_fulltext` | boolean | EuropePMC bulk | Journal has ≥1 full-text article in PMC |
| `pmc_article_count` | integer | EuropePMC bulk | Number of full-text articles (if computed) |
| `pmc_last_deposit_year` | integer | EuropePMC bulk | Recency of PMC activity |

> **Caveat on `has_pmc_agreement`:** Reflects agreement *history*, not current status. Do not use alone for submission decisions or "good journal" filters.

> **Caveat on `pmc_coverage_ratio`:** Conceptually useful but treacherous to compute. Requires robust denominator (total article count), which is difficult to obtain reliably. Journal scope changes, ISSN transfers, and indexing gaps can severely distort the ratio.

---

## 4. Why Journals Have PMC Content Without Agreements

### Funder Mandates Drive Author Deposits

Journals can have PMC content without formal publisher agreements because **funder policies require authors to deposit manuscripts**:

1. **NIH** (mandatory since 2008) — largest driver
2. **HHMI** (mandatory since 2022)
3. **Gates Foundation** (mandatory since 2017)
4. **Wellcome/UKRI/ERC** (mandatory since 2021, via Europe PMC)
5. **Other US federal agencies** (VA, CDC, AHRQ, etc.)
6. **Voluntary deposits** by authors
7. **Historical content** digitized and added to PMC

> **Important caveats:**
>
> - We cannot verify deposit pathway from journal-level data. These are plausible explanations, not proven attributions.
>
> - **Funder mandates do not guarantee PMC content.** Compliance is imperfect—a journal may publish funder-covered articles yet have zero PMC deposits.
>
> - **Journal-level PMC presence is only weakly correlated with funder mandates.** The relationship is mediated by compliance workflows, publisher policies, and author behavior. Do not infer "Journal X publishes NIH-funded research → Journal X has PMC content" or vice versa.

### Visual Summary

```
PMC Content Sources
│
├── Publisher Agreements (~4,400 journals)
│   └── Captured by is_pmc_indexed = true
│
└── Author/Funder Deposits (~16,400 additional journals)
    ├── NIH Public Access Policy
    ├── HHMI, Gates, Wellcome mandates
    ├── Other federal agencies
    └── NOT captured by is_pmc_indexed
```

---

## 5. Europe PMC vs PMC

Europe PMC is a **separate database** from PMC with substantial but not complete overlap.

| Aspect | Details |
|--------|---------|
| **PMC → Europe PMC** | Vast majority of PMC articles ingested (not literally 100%) |
| **Europe PMC → PMC** | Author manuscripts via Europe PMC plus typically receive PMCIDs |
| **Europe PMC-only** | Preprints, patents, Agricola records |

According to Europe PMC: it "contains all of the PubMed abstracts, the vast majority of PMC content, plus additional content including preprints, … and Agricola records."

**Do not assume PMC ⊂ Europe PMC** for automated logic—some PMC articles may not appear in Europe PMC.

---

## Appendix: Funder Policy Context

This appendix provides background on the funder policies that drive PMC content. **This section will become stale**—verify current requirements with funders.

> **Time-sensitivity warning:** This reflects policies **as announced by December 2024**:
> - **In effect** — policies actively governing deposits at time of writing
> - **Announced, effective [date]** — adopted but not yet in force
>
> Policies with future effective dates could be modified, delayed, or rescinded.

### A.1 Publisher Deposit Agreements

Journals meeting NLM standards can deposit final published versions directly to PMC. These ~4,400 journals appear in the [PMC Journal List](https://pmc.ncbi.nlm.nih.gov/journals/).

**Requirements:**
- Established peer review process
- Full-text XML meeting PMC technical standards
- Systematic deposit of content

**Selective Deposit:** Publishers can also deposit select articles from subscription journals (hybrid OA, funder-supported articles).

> **Note:** Publisher and author deposit pathways are not mutually exclusive. A journal with a formal PMC agreement may still have author-deposited manuscripts.

**Source:** [PMC Publisher Information](https://pmc.ncbi.nlm.nih.gov/pub/pubinfo/)

---

### A.2 NIH Public Access Policy

**Policy:** In effect since April 2008; updated policy effective July 1, 2025

Since 2008, NIH requires that **any peer-reviewed manuscript arising from NIH funding** must be deposited in PMC.

```
NIH-funded researcher publishes in Journal X
            ↓
    ┌───────┴───────┐
    │               │
Journal has      Journal has NO
PMC agreement    PMC agreement
    │               │
    ↓               ↓
Publisher       Author deposits
deposits        accepted manuscript
automatically   via NIHMS
    │               │
    ↓               ↓
Author does     Author responsible
nothing         for compliance
    │               │
    └───────┬───────┘
            ↓
    Article in PMC
```

#### Policy Timeline

The applicable policy depends on **manuscript acceptance date**:

| Aspect | Accepted before July 1, 2025 | Accepted on/after July 1, 2025 |
|--------|------------------------------|--------------------------------|
| **Submission to PMC** | Within 12 months of publication | At or near acceptance |
| **Public availability** | Up to 12 months embargo | **No embargo** |
| **Enforcement** | Renewals delayed | Any future awards at risk |

> **Transitional rule:** Acceptance date determines which policy applies, regardless of publication date.

#### Deposit Methods

| Route | Who Deposits | Version |
|-------|--------------|---------|
| **Journal-based** | Publisher | Final published article |
| **Manuscript-based** | Author | Accepted manuscript via NIHMS |

> **Legacy terminology:** Methods A/B (journal-based) vs C/D (manuscript-based). NIH now de-emphasizes A-D labels.

#### Scale

NIH is among the largest public funders of biomedical research:
- **~$47–48 billion** annual budget (FY 2024-2025)
- Funds research at virtually every US medical school

**Sources:**
- [NIH Public Access Policy](https://grants.nih.gov/policy-and-compliance/policy-topics/public-access)
- [Submitting to PubMed Central](https://grants.nih.gov/policy-and-compliance/policy-topics/public-access/submitting-pubmed-central)
- [Columbia University: NIH Policy Updates](https://research.columbia.edu/policy-updates-0)

---

### A.3 OSTP Public Access Memo (2022)

**Directive:** Issued August 25, 2022

The "Nelson Memo" directs **all federal agencies** to provide immediate public access to federally funded research.

| Aspect | Previous (2013) | Current (2022) |
|--------|-----------------|----------------|
| **Scope** | Agencies with >$100M R&D | All federal agencies |
| **Embargo** | Up to 12 months | **No embargo** |
| **Format** | Not specified | Machine-readable (e.g., JATS XML) |

> **Note on format:** The memo requires "machine-readable" but does not mandate JATS XML specifically.

#### Timeline

| Date | Milestone |
|------|-----------|
| **Feb 2023** | Large agencies submit plans |
| **Dec 31, 2024** | Agencies publish final policies |
| **Dec 31, 2025** | Policies in effect |
| **Dec 31, 2027** | Research integrity provisions in effect |

> **Note:** As of December 2024, implementation varies by agency. Policy directives can be modified by subsequent administrations.

**Sources:**
- [OSTP Memo (PDF)](https://bidenwhitehouse.archives.gov/wp-content/uploads/2022/08/08-2022-OSTP-Public-Access-Memo.pdf)
- [SPARC Guidance](https://sparcopen.org/our-work/2022-updated-ostp-policy-guidance/)

---

### A.4 Other US Federal Agencies

#### Mandatory PMC Deposit

| Agency | Policy |
|--------|--------|
| **VA** | "Investigators are responsible for depositing manuscripts in PubMed Central... upon acceptance." (Since Feb 2015) |
| **AHRQ** | PMC deposit required |

#### PMC Partner Funders (policies vary)

CDC, FDA, ACL, DHS, EPA, NIST — policies evolving under OSTP memo.

**Source:** [PMC Funder Policies](https://pmc.ncbi.nlm.nih.gov/about/public-access/)

---

### A.5 Private Foundations

#### HHMI

**Policy:** In effect since January 1, 2022; updated policy effective January 1, 2026

| Requirement | 2022 (current) | 2026 (announced) |
|-------------|----------------|------------------|
| **Repository** | PMC or HHMI-designated | Same |
| **Preprint** | Not required | Required |
| **Hybrid APCs** | Permitted | Not permitted |

**Sources:**
- [HHMI 2022 Policy](https://www.hhmi.org/news/hhmi-announces-open-access-publishing-policy)
- [HHMI 2026 Policy (PDF)](https://hhmicdn.blob.core.windows.net/policies/Immediate-Access-to-Research.pdf)

#### Gates Foundation

**Policy:** In effect since January 1, 2017; expansion January 1, 2025

Repository: PMC **or** another openly accessible repository (PMC is preferred/default).

**Source:** [Gates 2025 Policy](https://openaccess.gatesfoundation.org/open-access-policy/2025-open-access-policy/)

#### Health Research Alliance

20+ foundations partner with PMC: Alzheimer's Association, American Heart Association, Cancer Research Institute, etc.

---

### A.6 Europe PMC and International Funders

#### Relationship with PMC

Europe PMC is operated by EMBL-EBI as part of the PMC International (PMCI) network.

| Direction | Details |
|-----------|---------|
| **PMC → Europe PMC** | Vast majority ingested automatically |
| **Europe PMC → PMC** | Author manuscripts typically receive PMCIDs |
| **Europe PMC-only** | Preprints, patents, Agricola records |

> **Note on Europe PMC plus:** Manuscript submission system for Europe PMC funders. Manuscripts typically receive PMCIDs, but public documentation does not explicitly guarantee this for all cases.

**Sources:**
- [Europe PMC Help](https://europepmc.org/help)
- [PMC International](https://pmc.ncbi.nlm.nih.gov/about/pmci/)

#### Plan S / cOAlition S

**Initiative:** In effect since January 1, 2021

Key members: Wellcome, UKRI, ERC, Gates, 20+ European funders.

Compliance routes include repository deposit in Europe PMC/PMC.

**Source:** [cOAlition S](https://www.coalition-s.org/)

#### Wellcome Trust

**Policy:** In effect since January 1, 2021; APC changes January 1, 2025

| Requirement | Details |
|-------------|---------|
| **License** | CC BY |
| **Repository** | Europe PMC and PMC |
| **APCs** | Fully OA journals only (from Jan 2025) |

**Source:** [Wellcome OA Policy](https://wellcome.org/research-funding/guidance/ending-a-grant/open-access-guidance/open-access-policy)

#### Other Europe PMC Funders

ERC, UKRI, Cancer Research UK, British Heart Foundation, MRC — policies vary by discipline and grant type.

> **Caution:** Do not use for automated logic assuming "funder X = always full text in PMC."

---

## References

### PMC/NCBI
- [PubMed Central Home](https://pmc.ncbi.nlm.nih.gov/)
- [PMC Journal List](https://pmc.ncbi.nlm.nih.gov/journals/)
- [PMC Submission Methods](https://pmc.ncbi.nlm.nih.gov/about/submission-methods/)
- [PMC Funder Policies](https://pmc.ncbi.nlm.nih.gov/about/public-access/)
- [PMC International](https://pmc.ncbi.nlm.nih.gov/about/pmci/)

### NIH
- [NIH Public Access Policy](https://grants.nih.gov/policy-and-compliance/policy-topics/public-access)
- [Submitting to PMC](https://grants.nih.gov/policy-and-compliance/policy-topics/public-access/submitting-pubmed-central)

### OSTP
- [2022 OSTP Memo (PDF)](https://bidenwhitehouse.archives.gov/wp-content/uploads/2022/08/08-2022-OSTP-Public-Access-Memo.pdf)
- [SPARC Guidance](https://sparcopen.org/our-work/2022-updated-ostp-policy-guidance/)

### Private Foundations
- [HHMI Policy](https://www.hhmi.org/news/hhmi-announces-open-access-publishing-policy)
- [Gates Policy](https://openaccess.gatesfoundation.org/)

### Europe PMC & Plan S
- [Europe PMC](https://europepmc.org/)
- [Europe PMC Funders](https://europepmc.org/Funders)
- [cOAlition S](https://www.coalition-s.org/)
- [Wellcome OA Policy](https://wellcome.org/research-funding/guidance/ending-a-grant/open-access-guidance/open-access-policy)
