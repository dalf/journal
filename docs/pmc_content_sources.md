# PubMed Central: How Content Gets Into PMC

> **Policy status as of:** December 2024
>
> **Scope:** This document focuses on aspects relevant to understanding journal metadata in the sibils-journals database, particularly the `is_pmc_indexed` field and why ~20,000 journals have PMC content while only ~4,400 have formal deposit agreements.
>
> **Important caveat:** The `is_pmc_indexed` field is a simplification. A boolean flag cannot distinguish between a fully open-access journal depositing 100% of articles via a publisher agreement versus a subscription journal with a single author-deposited manuscript from a decade ago. See [Limitations of a binary flag](#limitations-of-a-binary-flag) for details. Do not over-interpret this field.
>
> **Time-sensitivity warning:** This document reflects policies **as announced by December 2024**. It distinguishes between:
> - **In effect** — policies actively governing deposits at time of writing
> - **Announced, effective [date]** — policies adopted but not yet in force
>
> Policies with future effective dates (NIH July 2025, HHMI preprint mandate January 2026, OSTP agency compliance December 2025) were announced but could be modified, delayed, or rescinded before taking effect. This document does not track post-December-2024 developments.
>
> **This document will become stale.** Funder policies evolved rapidly during 2023-2024 and will continue to do so. Anyone using this operationally in 2025 or later should verify current requirements directly with funders. Numerical values (~4,400 journals, ~20,800 journals, ~$47-48B budget) are **snapshot values**, not structural constants.

## Overview

PubMed Central (PMC) is a free full-text archive of biomedical and life sciences journal literature at the U.S. National Institutes of Health's National Library of Medicine (NIH/NLM). Established in 2000, PMC receives content through multiple pathways:

1. **Publisher agreements** - Journals with formal deposit arrangements
2. **Funder mandates** - Required deposits from grant recipients (author-driven)
3. **International partnerships** - Content shared via PMC International network

## 1. Publisher Deposit Agreements

### Full Journal Participation

Journals meeting NLM standards can deposit final published versions directly to PMC. These ~4,400 journals appear in the [PMC Journal List](https://pmc.ncbi.nlm.nih.gov/journals/).

**Requirements:**
- Established peer review process
- Full-text XML meeting PMC technical standards
- Systematic deposit of content (all articles or all NIH-funded articles)

### Selective Deposit

Publishers deposit select articles from subscription journals:
- Hybrid journals with open access options
- Articles funded by PMC-partner funders

Eligibility criteria include having an established peer review process, an open access publishing program, and the ability to systematically identify funder-supported content. In practice, publishers with MEDLINE-indexed journals or high volumes of funder-supported articles are more likely to have selective deposit arrangements.

**Source:** [PMC Publisher Information](https://pmc.ncbi.nlm.nih.gov/pub/pubinfo/)

> **Note:** Publisher and author deposit pathways are not mutually exclusive. A journal with a formal PMC agreement may still have authors depositing manuscripts via NIHMS (Methods C/D) for articles not covered by the publisher's deposit scope, or when funders require specific license terms.

---

## 2. NIH Public Access Policy

**Policy:** Original policy in effect since April 2008; updated policy adopted 2024, effective July 1, 2025

### The Mechanism

Since 2008, the NIH requires that **any peer-reviewed manuscript arising from NIH funding** must be deposited in PubMed Central. This can happen via publisher or author action, depending on the journal's PMC participation status:

```
NIH-funded researcher publishes in Journal X
            ↓
    ┌───────┴───────┐
    │               │
Journal has      Journal has NO
PMC agreement    PMC agreement
(Method A/B)
    │               │
    ↓               ↓
Publisher       Author deposits
deposits        accepted manuscript
final article   via NIHMS
automatically   (Method C/D)
    │               │
    ↓               ↓
Author does     Author responsible
nothing for     for compliance
compliance
    │               │
    └───────┬───────┘
            ↓
    Article in PMC
```

**Key point:** For journals with journal-based deposit agreements, compliance is automatic—authors need take no action. For other journals, authors must deposit via NIHMS (manuscript-based route). Even journals with formal PMC agreements may have author-deposited content when the publisher's agreement doesn't cover all NIH-funded articles.

### Policy Timeline

The applicable policy depends on **manuscript acceptance date**, not publication date:

| Aspect | Accepted before July 1, 2025 | Accepted on/after July 1, 2025 |
|--------|------------------------------|--------------------------------|
| **Submission to PMC** | Within 12 months of publication | At or near acceptance |
| **Public availability** | Up to 12 months after publication (embargo permitted) | **At publication date, no embargo** |
| **Enforcement** | Non-competing continuation awards delayed until compliance | Non-compliance can block **any future awards** (not just renewals); more automated compliance checking |

Note the distinction:
- **Submission timing** = when the manuscript must be deposited to PMC/NIHMS
- **Public availability** = when the full text becomes publicly accessible in PMC

Under the old policy, authors could submit near the 12-month deadline and the article would become public shortly after. Under the new policy, submission must happen early enough that the article is publicly available *at the time of publication*.

> **Transitional rule:** The acceptance date determines which policy applies, regardless of publication date. A paper accepted June 30, 2025 follows the old policy (12-month embargo permitted) even if published in 2026. A paper accepted July 1, 2025 follows the new policy (no embargo) even if published soon after. During 2025-2026, compliance officers must track acceptance dates to determine which regime applies to each article.

The key change: articles under the new policy must be **publicly accessible in PMC at the time of publication**, not just submitted. This aligns with the [OSTP Nelson Memo](#ostp-public-access-memo-2022) requirements.

### Scale of Impact

NIH is among the largest public funders of biomedical research worldwide:
- **~$47–48 billion** annual budget (FY 2024-2025; subject to congressional appropriations)
- Funds research at virtually every US medical school
- Supports thousands of international collaborations

This means journals publishing biomedical research are highly likely to have NIH-funded content in PMC.

### Deposit Methods

NIH's current documentation describes two primary routes:

| Route | Who Deposits | Version | Notes |
|-------|--------------|---------|-------|
| **Journal-based** | Publisher | Final published article | For journals with PMC deposit agreements; compliance is automatic for authors |
| **Manuscript-based** | Author (or publisher on author's behalf) | Accepted manuscript | Via NIHMS; author responsible for initiating and approving submission |

> **Legacy terminology:** Older documentation and some library guides refer to Methods A, B, C, and D. Methods A/B are journal-based (publisher deposits final article); Methods C/D are manuscript-based (author deposits accepted manuscript, or publisher initiates on author's behalf). NIH's current guidance de-emphasizes these labels in favor of "journal-based" vs "manuscript-based."

The number of journals with journal-based deposit agreements varies; PMC's submission methods page lists participating journals but does not provide a single count. Estimates of ~900 journals for "Method A" (full participation) appear in some library guides but should be verified against [PMC's current journal list](https://pmc.ncbi.nlm.nih.gov/journals/) filtered by deposit method.

**Sources:**
- [NIH Public Access Policy](https://grants.nih.gov/policy-and-compliance/policy-topics/public-access)
- [Submitting to PubMed Central](https://grants.nih.gov/policy-and-compliance/policy-topics/public-access/submitting-pubmed-central)
- [PMC Submission Methods](https://pmc.ncbi.nlm.nih.gov/about/submission-methods/)
- [NIH Budget](https://www.nih.gov/about-nih/organization/budget)
- [Columbia University: NIH Policy Updates](https://research.columbia.edu/policy-updates-0) (enforcement details)

---

## 3. OSTP Public Access Memo (2022)

**Directive:** Issued August 25, 2022; agency compliance deadline December 31, 2025

### Overview

On August 25, 2022, the White House Office of Science and Technology Policy (OSTP) issued the "Nelson Memo" directing **all federal agencies** to provide immediate public access to federally funded research.

### Key Requirements

| Aspect | Previous (2013 Holdren Memo) | Current (2022 Nelson Memo) |
|--------|------------------------------|---------------------------|
| **Scope** | Agencies with >$100M R&D | All federal agencies |
| **Embargo** | Up to 12 months allowed | **No embargo** |
| **Data** | Not addressed | Underlying data included |
| **Format** | Not specified | Machine-readable (e.g., JATS XML) |

> **Note on format:** The memo requires "machine-readable" formats but does not mandate a specific standard. It cites JATS XML (as used by PMC) as an example, not a requirement. Agencies may adopt other machine-readable formats.

### Timeline

There is no single uniform deadline. The memo established a phased timeline:

| Date | Milestone |
|------|-----------|
| **Feb 2023** | Agencies with >$100M R&D submit updated plans (180 days) |
| **Aug 2023** | Agencies with ≤$100M R&D submit updated plans (360 days) |
| **Dec 31, 2024** | Agencies publish final policies |
| **Dec 31, 2025** | Policies in effect (no later than 1 year after publication) |
| **Dec 31, 2026** | Research integrity provisions: final policies due |
| **Dec 31, 2027** | Research integrity provisions: policies in effect |

Effective dates cluster around late 2025 but vary by agency. As of late 2024, implementation progress varies significantly—some agencies (NIH, NASA, DOE) have published updated policies; others (DOD, NSF, USDA) have not.

### Impact on PMC

Federal agencies may designate PMC as their repository or establish their own. NIH's PMC serves as a model implementation of the OSTP requirements.

> **Note on status:** As of December 2024, agencies are in various stages of developing their public access plans. The December 2025 deadline was set by the memo, but actual implementation timelines and details vary by agency. Policy directives can also be modified by subsequent administrations.

**Sources:**
- [OSTP Memo (PDF)](https://bidenwhitehouse.archives.gov/wp-content/uploads/2022/08/08-2022-OSTP-Public-Access-Memo.pdf)
- [SPARC Guidance on OSTP Memo](https://sparcopen.org/our-work/2022-updated-ostp-policy-guidance/)
- [University of Michigan OSTP Guide](https://guides.lib.umich.edu/open-research-and-scholarship/OSTP-memo)

---

## 4. Other US Federal Agency Partners

Federal agencies partner with PMC in different ways. Some have mandatory deposit policies; others route select content via PMC or are still developing their public access implementations under the OSTP memo.

### Mandatory PMC Deposit

| Agency | Policy |
|--------|--------|
| **Department of Veterans Affairs (VA)** | "Investigators are responsible for depositing manuscripts in PubMed Central... upon the manuscripts' acceptance for publication." Applies to all peer-reviewed publications from ORD-funded research with acceptance date ≥ Feb 1, 2015. ([VA Public Access Policy](https://www.research.va.gov/resources/policies/public_access.cfm)) |
| **Agency for Healthcare Research and Quality (AHRQ)** | PMC deposit required for funded research |

### PMC Partner Funders (policies vary)

| Agency | Status |
|--------|--------|
| **Centers for Disease Control and Prevention (CDC)** | HHS agency; public access requirements apply |
| **Food and Drug Administration (FDA)** | HHS agency; public access requirements apply |
| **Administration for Community Living (ACL)** | HHS agency; public access requirements apply |
| **Department of Homeland Security (DHS)** | Partner funder; some content routed to PMC |
| **Environmental Protection Agency (EPA)** | Partner funder; policies evolving |
| **National Institute of Standards and Technology (NIST)** | Partner funder; policies evolving |

> **Note:** Under the 2022 OSTP memo, all federal agencies must implement public access policies by December 2025. Current PMC partnerships and requirements are evolving; consult agency-specific guidance for authoritative details.

**Sources:**
- [PMC and Research Funder Policies](https://pmc.ncbi.nlm.nih.gov/about/public-access/)
- [VA Public Access Policy](https://www.research.va.gov/resources/policies/public_access.cfm)
- [NLM Technical Bulletin: New Granting Organizations](https://www.nlm.nih.gov/pubs/techbull/ma18/ma18_new_granting_orgs.html)

---

## 5. Private Foundations

### Howard Hughes Medical Institute (HHMI)

**Policy:** Adopted 2020, in effect since January 1, 2022; updated policy effective January 1, 2026

| Requirement | 2022 Policy (current) | 2026 Policy (announced) |
|-------------|----------------------|------------------------|
| **License** | CC BY required | CC BY required |
| **Timing** | Immediate upon publication | Immediate upon publication |
| **Repository** | PMC or another HHMI-designated CC BY repository | Same |
| **Preprint** | Not required | Required (bioRxiv, medRxiv, arXiv, or ChemRxiv) prior to journal submission |
| **APC funding** | Permitted | HHMI funds cannot be used for hybrid journal APCs |
| **Scope** | Papers where HHMI scientist is first, last, or corresponding author | Same |

PMC is historically the primary repository for HHMI biology outputs, but the 2022 policy allows deposit in PMC "or another HHMI-designated CC BY repository." The 2026 policy adds a preprint mandate and restricts APC funding for hybrid journals.

**Sources:**
- [HHMI 2022 Open Access Policy Announcement](https://www.hhmi.org/news/hhmi-announces-open-access-publishing-policy)
- [HHMI 2026 Immediate Access to Research Policy (PDF)](https://hhmicdn.blob.core.windows.net/policies/Immediate-Access-to-Research.pdf)
- [University of Wisconsin: HHMI Requirements](https://www.library.wisc.edu/pas/private-funder-requirements/)
- [Nature: HHMI Strict Open-Access Policy](https://www.nature.com/articles/d41586-020-02793-5)

### Bill & Melinda Gates Foundation

**Policy:** In effect since January 1, 2017; expansion in effect January 1, 2025

| Requirement | Details |
|-------------|---------|
| **License** | CC BY 4.0 required |
| **Timing** | Immediate upon publication |
| **Repository** | PMC or another openly accessible repository (PMC is preferred/default) |
| **Scope** | All published research funded by the foundation |

The 2025 policy states articles "shall be deposited immediately upon publication in PubMed Central (PMC), or in another openly accessible repository, with proper metadata tagging identifying Gates funding." Gates has partnered with NLM to enable deposit via NIHMS, making PMC the default pathway for most biomedical research—but it is not the only compliant option.

**Sources:**
- [Gates 2025 Open Access Policy](https://openaccess.gatesfoundation.org/open-access-policy/2025-open-access-policy/)
- [Gates PMC Deposits Guide](https://openaccess.gatesfoundation.org/how-to-comply/pubmed-central-deposits/)

### Health Research Alliance Members

20+ disease-focused foundations partner with PMC, including:
- Alzheimer's Association
- American Heart Association
- Autism Speaks
- Cancer Research Institute
- Crohn's & Colitis Foundation
- Patient-Centered Outcomes Research Institute (PCORI)
- Susan G. Komen

**Source:** [PMC Partner Funders](https://pmc.ncbi.nlm.nih.gov/about/public-access/)

---

## 6. Europe PMC and International Funders

### Relationship Between PMC and Europe PMC

Europe PMC is a partner repository in the PMC International (PMCI) network. According to Europe PMC's own documentation, it "contains all of the PubMed abstracts, the vast majority of PMC content, plus additional content including preprints, … and Agricola records."

| Aspect | Details |
|--------|---------|
| **Operator** | EMBL-EBI (European Bioinformatics Institute) |
| **PMC → Europe PMC** | The vast majority of PMC full-text articles are ingested into Europe PMC (not literally 100%, for technical and policy reasons) |
| **Europe PMC → PMC** | Author manuscripts deposited via Europe PMC plus are processed through the PMCI network and typically receive PMCIDs and appear in PMC; however, some Europe PMC content types (preprints, patents, Agricola records) are not shared back |
| **Europe PMC-only content** | Preprints, patents, Agricola records, certain funder collections |
| **Scale** | 42+ million abstracts, 9+ million full-text articles (as of 2023) |

> **Note on Europe PMC plus:** Europe PMC plus is a manuscript submission system for Europe PMC funders. Manuscripts are converted to XML and made available in Europe PMC. Funder policies and NLM documentation indicate these manuscripts are hosted in PMC and receive PMCIDs, but public documentation does not explicitly guarantee this for all cases.

**Key point:** Europe PMC includes most of PMC's full-text content plus additional sources, but PMC does not include Europe PMC-only content. They are separate databases with substantial but not complete overlap. Do not assume PMC ⊂ Europe PMC for automated logic—some PMC articles may not appear in Europe PMC.

**Sources:**
- [PMC International](https://pmc.ncbi.nlm.nih.gov/about/pmci/)
- [PMC Author Manuscripts](https://pmc.ncbi.nlm.nih.gov/about/authorms/)
- [Europe PMC Help](https://europepmc.org/help)
- [Europe PMC Submitting Data](https://www.ebi.ac.uk/training/online/courses/europepmc-quick-tour/submitting-data-to-europe-pmc)
- [Europe PMC vs PubMed/PMC (PDF)](https://europepmc.org/docs/Information_poster_Europe_PMC_vs_PubMed_and_PMC.pdf)
- [Europe PMC 2023 Paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC10767826/)

### Plan S and cOAlition S

**Initiative:** Announced September 2018; in effect since January 1, 2021

Plan S is an initiative by cOAlition S (a group of research funders) requiring immediate open access to funded research.

**Key cOAlition S members:**
- Wellcome Trust
- UK Research and Innovation (UKRI)
- European Research Council (ERC)
- Bill & Melinda Gates Foundation
- 20+ European national funders

**Compliance routes involving PMC/Europe PMC (simplified):**
1. Publish OA in DOAJ-listed journal
2. Deposit accepted manuscript in Europe PMC/PMC immediately
3. Publish via transformative agreement (publisher deposits to PMC)

> This is a high-level summary. Funder policies specify detailed combinations of publisher agreements, third-party platforms, repository deposit, and licensing requirements. See [Wellcome's compliance guidance](https://wellcome.org/research-funding/guidance/open-access-guidance/complying-with-our-open-access-policy) for authoritative details.

**Sources:**
- [cOAlition S / Plan S](https://www.coalition-s.org/)
- [Plan S Wikipedia](https://en.wikipedia.org/wiki/Plan_S)

### Wellcome Trust

**Policy:** In effect since January 1, 2021 (Plan S-aligned); APC funding changes in effect January 1, 2025

| Requirement | Details |
|-------------|---------|
| **License** | CC BY required (CC BY-ND by exception) |
| **Timing** | Immediate upon publication |
| **Repository** | Must be freely available via Europe PMC and PMC |
| **APC funding** | Wellcome funds APCs only for fully OA journals/platforms (from Jan 2025); hybrid journal APCs and Plan S "transformative" journal support ended Dec 31, 2024 |
| **Data & software** | Underlying data and software/code must also be openly accessible with appropriate licenses |

> **Operational note:** Wellcome policy requires availability in Europe PMC/PMC, but the deposit pathway varies. Publishers with PMC agreements typically deposit to PMC first; Europe PMC then ingests this content automatically. Authors without publisher support can deposit directly via Europe PMC plus. The end result—availability in both systems—is what matters for compliance.
>
> **Beyond publications:** Wellcome's OA policy extends to research data and software. Data underlying publications must be deposited in appropriate repositories with open licenses. This is relevant for metadata systems tracking repository deposits beyond article full-text.

**Sources:**
- [Wellcome Open Access Policy](https://wellcome.org/research-funding/guidance/ending-a-grant/open-access-guidance/open-access-policy)
- [Depositing Wellcome-funded Research](https://wellcome.org/research-funding/guidance/open-access-guidance/depositing-your-wellcome-funded-research)
- [University of Sheffield: Wellcome Trust Policy Summary](https://sheffield.ac.uk/library/open-access/wellcome-trust-policy) (includes transformative journal end date)
- [University of Leicester: Wellcome Trust Policy Summary](https://le.ac.uk/library/research-support/open-research/funder-open-access-policies/wellcome-trust)

### Other Europe PMC Funders

| Funder | Country | Policy summary |
|--------|---------|----------------|
| **European Research Council (ERC)** | EU | Immediate OA required; repository deposit expected |
| **UK Research and Innovation (UKRI)** | UK | OA required; Europe PMC accepted but not exclusive; embargoes vary by discipline |
| **Cancer Research UK** | UK | OA with Europe PMC deposit typically expected for life sciences |
| **British Heart Foundation** | UK | OA with Europe PMC deposit typically expected |
| **Medical Research Council** | UK | Part of UKRI; follows UKRI policy |

> **Caution:** Funder policies vary by discipline, grant type, and policy version. Some distinguish between "platforms" and repositories, or allow embargoes for certain content types. The above is directionally correct but should not be used for automated logic assuming "funder X = always full text in PMC." Consult funder-specific guidance for authoritative requirements.

**Sources:**
- [Europe PMC Funders](https://europepmc.org/Funders)
- [University of Sussex: Research Funders OA Policies](https://www.sussex.ac.uk/library/open-research/open-access/research-funders)

---

## 7. Why This Matters for Journal Data

### The Gap Explained

| Source | Journals | What It Represents |
|--------|----------|-------------------|
| **PMC Journal List** (jlist.csv) | ~4,400 | Formal publisher deposit agreements (see methodology) |
| **EuropePMC bulk metadata** | ~20,800 | Journals with ≥1 full-text article in PMC (see methodology) |
| **Difference** | ~16,400 | Journals with PMC content not appearing in the formal participation list |

#### Methodology: How these figures were computed

**~4,400 journals (PMC Journal List)**

- **Source:** `jlist.csv` downloaded from `https://cdn.ncbi.nlm.nih.gov/pmc/home/jlist.csv`
- **Method:** Count of unique journals (rows) with at least one valid ISSN (print or electronic)
- **Date:** December 2024
- **What it includes:** Journals with formal PMC deposit agreements (full participation or selective deposit)
- **Verification:** The PMC Journal List web interface at https://pmc.ncbi.nlm.nih.gov/journals/ shows comparable counts

> **Caveat:** The PMC Journal List includes journals that have ceased publication or are no longer actively depositing to PMC. A journal appearing in `jlist.csv` means "has ever had a PMC deposit agreement," not "is currently an active PMC participant." For longitudinal or OA coverage analysis, this distinction matters.

**~20,800 journals (EuropePMC bulk metadata)**

- **Source:** `PMCLiteMetadata.tgz` downloaded from `https://europepmc.org/ftp/pmclitemetadata/`
- **Method:** Extract unique journal ISSNs from article-level XML metadata across all files in the archive
- **Date:** December 2024
- **What it includes:** Any journal with at least one full-text article archived in PMC (regardless of deposit pathway)
- **What it excludes:** PubMed abstracts, patents, Agricola records, and other Europe PMC content types that are not PMC full-text articles

> **Caveat:** We assume PMCLiteMetadata represents all journals with full-text articles in PMC. Europe PMC describes this as a PMC full-text metadata dump, but does not explicitly document it as complete. Some edge cases (embargoed content, recently added articles, technical issues) may not be captured.

#### Important limitations

Both figures are **cross-sectional snapshots** from December 2024, not longitudinal time series. They should not be used for:

- Tracking changes in PMC participation over time
- Measuring "current" OA-friendliness of journals
- Assuming active deposit relationships

Specifically:
- `has_pmc_agreement` (from jlist.csv) = "this journal has ever had a PMC deposit agreement," **not** "is actively depositing as of date X"
- `has_pmc_fulltext` (from PMCLiteMetadata) = "this journal has ≥1 article in PMC," which could be a single manuscript from 2008

### Likely Sources of Non-Agreement Content

The ~16,400 journals with PMC full-text content but no formal publisher agreement likely have content because of:

1. **NIH-funded authors** depositing manuscripts (mandatory since 2008)
2. **HHMI scientists** depositing manuscripts (mandatory since 2022)
3. **Gates Foundation grantees** depositing manuscripts (mandatory since 2017)
4. **Wellcome/UKRI/ERC grantees** depositing via Europe PMC (mandatory since 2021)
5. **Other federal agency grantees** (VA, CDC, EPA, etc.)
6. **Voluntary deposits** by authors choosing open access
7. **Historical content** digitized and added to PMC

> **Important caveats:**
>
> - We cannot directly verify deposit pathway from journal-level data. The above are plausible explanations for how journals acquire PMC content without formal agreements, not proven attributions.
>
> - **Funder mandates do not guarantee PMC content.** Compliance is imperfect—a journal may publish articles covered by funder OA policies yet have zero PMC deposits if authors or publishers fail to comply. Conversely, a journal with PMC content may have it from a single compliant author, not systematic funder-driven deposit.
>
> - **Journal-level PMC presence is only weakly correlated with funder mandates.** The relationship is mediated by compliance workflows (institutional support, library services), publisher policies (some facilitate deposit, others do not), and individual author behavior. Do not infer "Journal X publishes NIH-funded research → Journal X has PMC content" or vice versa.

### Implications for PMC-related Fields

#### Terminology note

The term "indexed" is overloaded and potentially confusing:

| Term | Meaning | Example |
|------|---------|---------|
| **PubMed indexed** | Journal's articles are discoverable via PubMed (abstracts/metadata) | MEDLINE journals |
| **PMC archived** | Journal has full-text content in PMC | Publisher agreement or author deposits |
| **PMC participation** | Journal has formal deposit agreement with PMC | PMC Journal List |

PMC itself uses "participation", "full participation", and "selective deposit"—not "indexed." The legacy field name `is_pmc_indexed` conflates these concepts.

#### Recommended field names

For clarity, consider replacing a single boolean with explicit fields:

| Field | Type | Source | Meaning |
|-------|------|--------|---------|
| `has_pmc_agreement` | boolean | PMC Journal List | Journal has (or has had) a formal publisher deposit agreement |
| `has_pmc_fulltext` | boolean | EuropePMC bulk | Journal has ≥1 full-text article in PMC |
| `pmc_article_count` | integer | EuropePMC bulk | Number of full-text articles (if computed) |

> **Caveat on `has_pmc_agreement`:** This field reflects agreement *history*, not current status. The PMC Journal List includes ceased journals and journals no longer actively depositing. Do not use this field alone to drive submission decisions or "good journal" filters without additional verification.

#### Current implementation

| Data Source | Coverage | Meaning |
|-------------|----------|---------|
| **PMC Journal List** (jlist.csv) | ~4,400 journals | Journal has formal PMC deposit agreement |
| **EuropePMC bulk metadata** (PMCLiteMetadata.tgz) | ~20,800 journals | Journal has ≥1 full-text article in PMC archive |

The sibils-journals database currently uses the PMC Journal List (mapped to `is_pmc_indexed`), which represents formal participation rather than comprehensive PMC content presence.

#### Limitations of a binary flag

A simple `is_pmc_indexed = true/false` conflates radically different situations:

| Scenario | is_pmc_indexed | Actual PMC coverage |
|----------|----------------|---------------------|
| Fully OA journal with publisher agreement | true | ~100% of articles |
| Subscription journal, one NIH manuscript from 2010 | true | <1% of articles |
| Journal with no PMC content | false | 0% |

For downstream analysis (coverage metrics, OA probability, repository discovery), gradated indicators would be more informative:

- **has_pmc_agreement**: Boolean from PMC Journal List (but see caveat above: reflects history, not current status)
- **pmc_article_count**: Number of full-text articles in PMC
- **pmc_coverage_ratio**: Share of articles with PMC full text (requires total article count)
- **pmc_last_deposit_year**: Recency of PMC activity

> **Caveat on `pmc_coverage_ratio`:** This metric is conceptually useful but treacherous to compute correctly. It requires a robust denominator (total article count by journal), which is difficult to obtain reliably. Journal scope changes, ISSN transfers, indexing gaps, and varying definitions of "article" (research articles vs. all content) can severely distort the ratio. Do not underestimate the complexity of implementing this field.

The current binary flag is useful for filtering but should not be interpreted as "this journal's content is comprehensively available in PMC."

---

## Summary

```
PMC Content Sources
│
├── Publisher Agreements (~4,400 journals)
│   ├── Full journal participation (Method A)
│   └── Selective deposit (hybrid OA, Method B)
│
├── US Federal Mandates
│   ├── NIH Public Access Policy (2008, updated 2024)
│   ├── OSTP Nelson Memo (2022) - all agencies by 2025
│   └── Agency partners: CDC, FDA, VA, EPA, DHS, NIST, etc.
│
├── Private Foundation Mandates
│   ├── HHMI (2022) - PMC designated
│   ├── Gates Foundation (2017) - PMC partnership
│   └── Health Research Alliance (20+ foundations)
│
└── International (via Europe PMC)
    ├── Plan S / cOAlition S (2021)
    ├── Wellcome Trust (2021)
    ├── UKRI, ERC, Cancer Research UK, etc.
    └── Content shared with PMC via PMCI network
```

---

## References

### PMC/NCBI
- [PubMed Central Home](https://pmc.ncbi.nlm.nih.gov/)
- [PMC Journal List](https://pmc.ncbi.nlm.nih.gov/journals/)
- [PMC Submission Methods](https://pmc.ncbi.nlm.nih.gov/about/submission-methods/)
- [PMC and Research Funder Policies](https://pmc.ncbi.nlm.nih.gov/about/public-access/)
- [PMC International](https://pmc.ncbi.nlm.nih.gov/about/pmci/)
- [VA in PMC](https://pmc.ncbi.nlm.nih.gov/funder/va/)

### NIH
- [NIH Public Access Policy](https://grants.nih.gov/policy-and-compliance/policy-topics/public-access)
- [Submitting to PMC](https://grants.nih.gov/policy-and-compliance/policy-topics/public-access/submitting-pubmed-central)
- [NIH Budget](https://www.nih.gov/about-nih/organization/budget)

### OSTP
- [2022 OSTP Public Access Memo (PDF)](https://bidenwhitehouse.archives.gov/wp-content/uploads/2022/08/08-2022-OSTP-Public-Access-Memo.pdf)
- [SPARC OSTP Guidance](https://sparcopen.org/our-work/2022-updated-ostp-policy-guidance/)

### Private Foundations
- [HHMI Open Access Policy](https://www.hhmi.org/news/hhmi-announces-open-access-publishing-policy)
- [Gates Open Access Policy](https://openaccess.gatesfoundation.org/)
- [Gates PMC Deposits](https://openaccess.gatesfoundation.org/how-to-comply/pubmed-central-deposits/)

### Europe PMC & Plan S
- [Europe PMC](https://europepmc.org/)
- [Europe PMC Funders](https://europepmc.org/Funders)
- [Europe PMC vs PubMed/PMC](https://europepmc.org/docs/Information_poster_Europe_PMC_vs_PubMed_and_PMC.pdf)
- [cOAlition S / Plan S](https://www.coalition-s.org/)
- [Wellcome Open Access Policy](https://wellcome.org/research-funding/guidance/ending-a-grant/open-access-guidance/open-access-policy)
