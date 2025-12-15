# Data Quality Issues

Known data quality issues in source datasets that affect journal unification.

## Crossref

### Wrong Electronic ISSN: Rheumatology / British Journal of Rheumatology

**Issue:** Crossref incorrectly lists `1460-2172` as the electronic ISSN for "Rheumatology (Oxford)", but this ISSN actually belongs to "British Journal of Rheumatology".

**Impact:** During ISSN-based merging, both journals get incorrectly linked because they share the same ISSN. This causes:
- British J Rheum's NLM ID (`8302415`) to be merged into Rheumatology's record
- Rheumatology's correct NLM ID (`100883501`) to be lost or overwritten

**The journals:**

| Journal | Years | Print ISSN | Electronic ISSN | NLM ID |
|---------|-------|------------|-----------------|--------|
| British Journal of Rheumatology | 1982-1998 | 0263-7103 | 1460-2172 | 8302415 |
| Rheumatology (Oxford) | 1999-present | 1462-0324 | 1462-0332 | 100883501 |

**Crossref error:**
```
title: Rheumatology (Oxford)
issn_print: 1462-0324     <- correct
issn_electronic: 1460-2172  <- WRONG (belongs to British J Rheum)
```

**Status:** Upstream data issue in Crossref. Cannot be fixed without manual curation.

---

## Crossref Quality Summary

Analysis of Crossref title file (`titleFile.csv`):

| Metric | Value |
|--------|-------|
| Total records | 129,649 |
| Title coverage | 100% |
| Publisher coverage | 100% |
| Print ISSN coverage | 69.1% |
| Electronic ISSN coverage | 83.0% |

**Known issues:**
- **116 duplicate electronic ISSNs** - same e-ISSN assigned to multiple journals
- **9,797 ISSNs used as both print and electronic** - same ISSN appears as print for one journal and electronic for another
- **No language, subjects, or source_type data** available in the title file
