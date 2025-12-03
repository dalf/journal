# Tracking Journal References from Articles

This document describes approaches to flag which journals are referenced by articles and quickly find referenced vs non-referenced journals.

## Context

- **Journals index**: Updated weekly
- **Articles index**: Separate pipeline, updated more frequently
- **Goal**: Know which journals have articles referencing them

## Options Overview

| Option | Approach | Coupling | Staleness | Query complexity |
|--------|----------|----------|-----------|------------------|
| A | Flag in journals index | High | Up to 1 week | Simple |
| B | Separate lookup index | Low | Near real-time | Medium |
| C | ES Transform | Low | Configurable | Medium |
| D | Terms lookup query | Low | Real-time | Medium |
| E | Pre-filter during unify | Low | At export time | None (filtered out) |

## Option C: ES Transform (Recommended)

A Transform continuously aggregates data from a source index into a destination index. It runs as a background job in Elasticsearch.

### How it works

```
articles index (source)
    ↓
Transform job (aggregates by ISSN)
    ↓
journal_references index (destination)
```

### Setup

**1. Create the transform:**

```json
PUT _transform/journal_references_transform
{
  "source": {
    "index": "articles"
  },
  "dest": {
    "index": "journal_references"
  },
  "pivot": {
    "group_by": {
      "issn": {"terms": {"field": "journal_issn"}}
    },
    "aggregations": {
      "article_count": {"value_count": {"field": "_id"}},
      "latest_article": {"max": {"field": "publication_date"}},
      "earliest_article": {"min": {"field": "publication_date"}}
    }
  },
  "frequency": "1h",
  "sync": {
    "time": {
      "field": "indexed_at",
      "delay": "60s"
    }
  }
}
```

**2. Start the transform:**

```json
POST _transform/journal_references_transform/_start
```

**3. Resulting destination index:**

```json
// journal_references index (auto-maintained)
{"issn": "1234-5678", "article_count": 42, "latest_article": "2025-01-15", "earliest_article": "2020-03-01"}
{"issn": "2807-2502", "article_count": 7, "latest_article": "2024-12-20", "earliest_article": "2023-06-15"}
```

### Query patterns

**Find referenced journals:**

```json
// Get all referenced ISSNs
GET journal_references/_search
{
  "query": {"match_all": {}},
  "_source": ["issn"]
}

// Then query journals with terms lookup or application-side join
```

### Pros

| Benefit | Description |
|---------|-------------|
| Automatic | Runs continuously, no cron jobs needed |
| Incremental | Only processes new/changed documents |
| Efficient | Uses ES-native aggregations |
| Metrics | Built-in stats, checkpointing, error handling |
| Free tier | Available in Basic license (free) |

### Cons

| Drawback | Description |
|----------|-------------|
| Resource usage | Consumes ES cluster resources |
| Sync field required | Source index needs a timestamp field for continuous mode |
| Cross-index query | Still need to join with journals (not automatic) |
| Complexity | More moving parts than simple flag |

### Continuous vs Batch

| Mode | Use case |
|------|----------|
| **Continuous** (`sync` config) | Real-time updates as articles are indexed |
| **Batch** (no `sync`) | Run once or on-demand, like a materialized view |

### Multiple source indices with different formats

When articles are spread across multiple indices with different field names:

**Option 1: Multiple transforms to same destination**

Create one transform per source index, all writing to the same destination:

```json
// Transform for index A (field: journal_issn)
PUT _transform/journal_refs_from_index_a
{
  "source": {"index": "articles_source_a"},
  "dest": {"index": "journal_references"},
  "pivot": {
    "group_by": {
      "issn": {"terms": {"field": "journal_issn"}}
    },
    "aggregations": {
      "article_count": {"value_count": {"field": "_id"}},
      "sources": {"terms": {"field": "_index"}}
    }
  }
}

// Transform for index B (field: issn)
PUT _transform/journal_refs_from_index_b
{
  "source": {"index": "articles_source_b"},
  "dest": {"index": "journal_references"},
  "pivot": {
    "group_by": {
      "issn": {"terms": {"field": "issn"}}
    },
    "aggregations": {
      "article_count": {"value_count": {"field": "_id"}},
      "sources": {"terms": {"field": "_index"}}
    }
  }
}
```

**Note:** Multiple transforms to same destination will create separate documents per source. Use a final aggregation query or another transform to merge.

**Option 2: Runtime field to normalize field names**

Use a runtime field to unify different field names into one:

```json
PUT _transform/journal_refs_unified
{
  "source": {
    "index": ["articles_source_a", "articles_source_b", "articles_source_c"],
    "runtime_mappings": {
      "normalized_issn": {
        "type": "keyword",
        "script": """
          if (doc.containsKey('journal_issn') && doc['journal_issn'].size() > 0) {
            emit(doc['journal_issn'].value);
          } else if (doc.containsKey('issn') && doc['issn'].size() > 0) {
            emit(doc['issn'].value);
          } else if (doc.containsKey('publication.issn') && doc['publication.issn'].size() > 0) {
            emit(doc['publication.issn'].value);
          }
        """
      }
    }
  },
  "dest": {"index": "journal_references"},
  "pivot": {
    "group_by": {
      "issn": {"terms": {"field": "normalized_issn"}}
    },
    "aggregations": {
      "article_count": {"value_count": {"field": "_id"}},
      "sources": {"terms": {"field": "_index", "size": 10}}
    }
  },
  "frequency": "1h",
  "sync": {
    "time": {
      "field": "indexed_at",
      "delay": "60s"
    }
  }
}
```

**Option 3: Ingest pipeline to normalize at index time**

Add a pipeline to each source that copies ISSN to a common field:

```json
PUT _ingest/pipeline/normalize_issn
{
  "processors": [
    {
      "set": {
        "if": "ctx.journal_issn != null",
        "field": "normalized_issn",
        "value": "{{journal_issn}}"
      }
    },
    {
      "set": {
        "if": "ctx.issn != null && ctx.normalized_issn == null",
        "field": "normalized_issn",
        "value": "{{issn}}"
      }
    }
  ]
}
```

Then use a single transform on `normalized_issn` field.

| Approach | Pros | Cons |
|----------|------|------|
| Multiple transforms | Simple, isolated | Multiple jobs, separate docs |
| Runtime field | Single transform, no reindex | Script overhead, complex |
| Ingest pipeline | Fast queries, clean | Requires reindex or new data |

## Alternative: Enrich Processor

If you want the data embedded in journals at index time:

```json
// 1. Create enrich policy from journal_references
PUT _enrich/policy/journal_article_counts
{
  "match": {
    "indices": "journal_references",
    "match_field": "issn",
    "enrich_fields": ["article_count", "latest_article"]
  }
}

// 2. Execute the policy (creates internal index)
POST _enrich/policy/journal_article_counts/_execute

// 3. Use in journals ingest pipeline
PUT _ingest/pipeline/enrich_journals
{
  "processors": [
    {
      "enrich": {
        "policy_name": "journal_article_counts",
        "field": "issn_l",
        "target_field": "article_stats",
        "max_matches": 1
      }
    }
  ]
}
```

This adds `article_stats.article_count` and `article_stats.latest_article` to each journal document at index time.

## Other Options

### Option A: Flag in journals index

Add `is_referenced: boolean` and/or `article_count: integer` directly to journals during weekly update.

```python
# During journal indexing
referenced_issns = get_referenced_issns_from_articles()
for journal in journals:
    journal["is_referenced"] = journal["issn_l"] in referenced_issns
```

**Pros:** Simple queries (`{"term": {"is_referenced": true}}`)
**Cons:** Coupling, staleness, requires querying articles during journal update

### Option B: Separate lookup index

Articles pipeline maintains a small index with just referenced ISSNs.

```json
// referenced_issns index
{"issn": "1234-5678", "article_count": 42, "last_seen": "2025-01-15"}
```

**Pros:** Decoupled pipelines
**Cons:** Cross-index query needed

### Option D: Terms lookup query

Store referenced ISSNs in a single document, use terms lookup.

```json
// Query journals that are referenced
GET journals/_search
{
  "query": {
    "terms": {
      "issn_l": {
        "index": "referenced_issns",
        "id": "all",
        "path": "issns"
      }
    }
  }
}
```

**Pros:** Fast, no index changes
**Cons:** Limited to 65k terms per lookup

### Option E: Pre-filter during unify

Dump referenced ISSNs from articles, then filter journals during the unify/export step. Only referenced journals are indexed.

**1. Dump ISSNs from articles index:**

```bash
curl -s "http://localhost:9200/articles/_search" -H "Content-Type: application/json" -d '
{
  "size": 0,
  "aggs": {
    "issns": {
      "terms": {"field": "journal_issn", "size": 100000}
    }
  }
}' | jq -r '.aggregations.issns.buckets[].key' > referenced_issns.txt
```

**2. Add filter to CLI/merger:**

```python
# In cli.py or merger.py
def load_referenced_issns(path: Path) -> set[str]:
    """Load set of ISSNs to keep."""
    with open(path) as f:
        return {line.strip() for line in f if line.strip()}

# Filter unified DataFrame
if referenced_issns_file:
    issns = load_referenced_issns(referenced_issns_file)
    df = df[
        df["issn_l"].isin(issns) |
        df["issn_print"].isin(issns) |
        df["issn_electronic"].isin(issns)
    ]
```

**3. CLI usage:**

```bash
python -m sibils_journals.cli --filter-issns referenced_issns.txt --es-url http://localhost:9200
```

**Pros:**
- Simple, no ES features needed
- Full control over filtering
- Works with existing pipeline
- Can version control the ISSN list
- Smaller index (only referenced journals)

**Cons:**
- Manual step (dump before run)
- Batch only, not continuous
- Need to regenerate file periodically
