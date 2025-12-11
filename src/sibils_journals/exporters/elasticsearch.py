"""Elasticsearch exporter for unified ISSN data.

Schema supports multiple search patterns:

1. AUTOCOMPLETE (edge ngram, partial word match):
   POST /journals/_search
   {
     "query": {
       "match": {"title.autocomplete": "biomed"}
     }
   }

2. ISSN COMPLETION (unified suggester for all ISSNs):
   POST /journals/_search
   {
     "suggest": {
       "issn": {
         "prefix": "0001",
         "completion": {"field": "issn_suggest", "size": 10}
       }
     }
   }

3. EXACT MATCH on ISSN:
   POST /journals/_search
   {
     "query": {
       "term": {"issn_l": "1234-5678"}
     }
   }

4. FULL-TEXT SEARCH:
   POST /journals/_search
   {
     "query": {
       "match": {"title": "molecular biology"}
     }
   }

5. URL SEARCH (path prefix matching):
   POST /journals/_search
   {
     "query": {
       "match": {"journal_url": "https://link.springer.com/journal/40256/articles"}
     }
   }
   Matches journals with URL "https://link.springer.com/journal/40256" because
   the query is tokenized into path prefixes by the url_analyzer.
"""

import logging
from typing import Any, Generator

import pandas as pd
from elasticsearch import Elasticsearch
from elasticsearch.helpers import streaming_bulk

from ..models import LIST_FIELDS

logger = logging.getLogger(__name__)

# Elasticsearch index mapping for journal records
# Designed for autocompletion and full-text search
INDEX_MAPPING = {
    "settings": {
        "analysis": {
            "tokenizer": {
                # For URL prefix matching (e.g., query with /articles suffix matches stored URL)
                "url_hierarchy": {
                    "type": "path_hierarchy",
                    "delimiter": "/",
                },
            },
            "analyzer": {
                # For partial matching (prefix search)
                "autocomplete": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "autocomplete_filter"],
                },
                "autocomplete_search": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase"],
                },
                # For URL search - tokenizes query into path prefixes
                "url_analyzer": {
                    "tokenizer": "url_hierarchy",
                },
            },
            "filter": {
                "autocomplete_filter": {
                    "type": "edge_ngram",
                    "min_gram": 2,
                    "max_gram": 20,
                },
            },
        },
    },
    "mappings": {
        "properties": {
            # ===== Core identifiers =====
            "unified_id": {"type": "keyword"},  # Unique identifier (ISSN-L, NLM-xxx, ISBN-xxx, OPENALEX-xxx, or TITLE-xxx)
            "issn_l": {"type": "keyword"},
            "issn_print": {"type": "keyword"},
            "issn_electronic": {"type": "keyword"},
            "nlm_id": {"type": "keyword"},  # NLM Catalog unique identifier
            "openalex_id": {"type": "keyword"},  # OpenAlex source identifier (e.g., S4306530189)
            "wikidata_id": {"type": "keyword"},  # Wikidata QID (e.g., Q180445)
            "is_medline_indexed": {"type": "boolean"},  # Currently indexed in MEDLINE
            "is_pmc_indexed": {"type": "boolean"},  # Has formal deposit agreement with PMC
            # PMC agreement details
            "pmc_agreement_status": {"type": "keyword"},  # "Active", "No longer participating", etc.
            "pmc_last_deposit_year": {"type": "integer"},  # Most recent deposit year
            "pmc_embargo_months": {"type": "integer"},  # Embargo period in months (0 = immediate)
            # Unified ISSN completion field for autocomplete
            "issn_suggest": {
                "type": "completion",
                "analyzer": "keyword",
                "preserve_separators": True,
                "preserve_position_increments": True,
                "max_input_length": 50,
            },
            # ===== Title fields =====
            "title": {
                "type": "text",
                "analyzer": "standard",
                "fields": {
                    "keyword": {"type": "keyword", "ignore_above": 512},
                    "autocomplete": {
                        "type": "text",
                        "analyzer": "autocomplete",
                        "search_analyzer": "autocomplete_search",
                    },
                },
            },
            "medline_abbreviation": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword", "ignore_above": 256},
                    "autocomplete": {
                        "type": "text",
                        "analyzer": "autocomplete",
                        "search_analyzer": "autocomplete_search",
                    },
                },
            },
            "alternative_titles": {
                "type": "text",
                "fields": {
                    "autocomplete": {
                        "type": "text",
                        "analyzer": "autocomplete",
                        "search_analyzer": "autocomplete_search",
                    },
                },
            },
            # ===== Publisher and organization =====
            "publisher": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword", "ignore_above": 256},
                    "autocomplete": {
                        "type": "text",
                        "analyzer": "autocomplete",
                        "search_analyzer": "autocomplete_search",
                    },
                },
            },
            "other_organisations": {"type": "text"},
            # ===== Classification =====
            "source_type": {"type": "keyword"},
            "subjects": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword", "ignore_above": 256},
                    "autocomplete": {
                        "type": "text",
                        "analyzer": "autocomplete",
                        "search_analyzer": "autocomplete_search",
                    },
                },
            },
            "subject_domain": {"type": "keyword"},  # Health Sciences, Physical Sciences, etc.
            "subject_field": {"type": "keyword"},  # Medicine, Engineering, etc.
            "subject_subfield": {"type": "keyword"},  # Health Informatics, etc.
            "language": {"type": "keyword"},
            "country": {"type": "keyword"},
            # ===== Open Access =====
            "is_oa": {"type": "boolean"},
            # ===== Licensing =====
            "license": {"type": "keyword"},
            "license_url": {"type": "keyword"},
            # ===== Editorial =====
            "review_process": {"type": "keyword"},
            "review_process_url": {"type": "keyword"},
            "plagiarism_screening": {"type": "boolean"},
            # ===== Preservation =====
            "preservation_services": {"type": "keyword"},
            # ===== Copyright =====
            "copyright_author": {"type": "boolean"},
            "copyright_url": {"type": "keyword"},
            "deposit_policy": {"type": "keyword"},
            # ===== APC =====
            "apc_amount": {"type": "float"},
            "apc_currency": {"type": "keyword"},
            # ===== URLs =====
            # URL field uses keyword analyzer at index time (stored as-is) and
            # url_analyzer at search time (tokenizes query into path prefixes).
            # This allows queries like "https://example.com/journal/123/articles"
            # to match stored URLs like "https://example.com/journal/123".
            "journal_url": {
                "type": "text",
                "analyzer": "keyword",
                "search_analyzer": "url_analyzer",
            },
            # ===== Metrics =====
            "works_count": {"type": "integer"},
            "cited_by_count": {"type": "integer"},
            "h_index": {"type": "integer"},
            # ===== Provenance =====
            "sources": {"type": "keyword"},
        }
    },
}


def _generate_actions(df: pd.DataFrame, index_name: str) -> Generator[dict[str, Any], None, None]:
    """Generate bulk indexing actions from DataFrame."""
    for _, row in df.iterrows():
        doc = row.dropna().to_dict()

        # Split pipe-separated fields into arrays
        for field in LIST_FIELDS:
            if field in doc and isinstance(doc[field], str):
                doc[field] = [v.strip() for v in doc[field].split("|") if v.strip()]

        # Build unified ISSN completion field with all ISSNs
        issn_inputs = []
        for issn_field in ("issn_l", "issn_print", "issn_electronic"):
            if issn_field in doc and doc[issn_field]:
                issn_inputs.append(doc[issn_field])
        if issn_inputs:
            doc["issn_suggest"] = {"input": issn_inputs}

        # Use unified_id as document ID (always unique)
        doc_id = doc.get("unified_id")
        if doc_id:
            yield {
                "_index": index_name,
                "_id": doc_id,
                "_source": doc,
            }


def export_elasticsearch(
    df: pd.DataFrame,
    es_url: str = "http://localhost:9200",
    index_name: str = "journals",
    es_api_key: str | None = None,
    recreate_index: bool = False,
    chunk_size: int = 500,
    request_timeout: int = 120,
) -> int:
    """
    Export unified journal data to Elasticsearch.

    Args:
        df: DataFrame containing unified journal records
        es_url: Elasticsearch URL (e.g., https://user:pass@localhost:9200)
        index_name: Name of the Elasticsearch index
        es_api_key: API key for authentication (alternative to auth in URL)
        recreate_index: If True, delete and recreate index
        chunk_size: Number of documents per bulk request
        request_timeout: Request timeout in seconds

    Returns:
        Number of documents indexed
    """
    # Connect to Elasticsearch with extended timeout
    client_options = {
        "request_timeout": request_timeout,
        "retry_on_timeout": True,
        "max_retries": 3,
    }
    if es_api_key:
        es = Elasticsearch(es_url, api_key=es_api_key, **client_options)
    else:
        es = Elasticsearch(es_url, **client_options)

    with es:
        # Check connection
        if not es.ping():
            raise ConnectionError(f"Cannot connect to Elasticsearch at {es_url}")

        logger.info(f"Connected to Elasticsearch at {es_url}")

        # Handle index creation
        if es.indices.exists(index=index_name):
            if recreate_index:
                logger.info(f"Deleting existing index: {index_name}")
                es.indices.delete(index=index_name)
                es.indices.create(index=index_name, body=INDEX_MAPPING)
                logger.info(f"Created index: {index_name}")
        else:
            es.indices.create(index=index_name, body=INDEX_MAPPING)
            logger.info(f"Created index: {index_name}")

        # Bulk index documents
        logger.info(f"Indexing {len(df):,} documents...")

        success = 0
        failed = 0
        errors = []

        try:
            for ok, item in streaming_bulk(
                es,
                _generate_actions(df, index_name),
                chunk_size=chunk_size,
                raise_on_error=False,
                request_timeout=request_timeout,
            ):
                if ok:
                    success += 1
                else:
                    failed += 1
                    if len(errors) < 10:  # Keep first 10 errors for debugging
                        errors.append(item)

            if failed:
                logger.warning(f"Failed to index {failed:,} documents")
                for error in errors:
                    logger.error(f"  {error}")

            logger.info(f"Successfully indexed {success:,} documents to '{index_name}'")
            return success
        finally:
            # Refresh index to make documents searchable
            try:
                es.indices.refresh(index=index_name, request_timeout=request_timeout)
            except Exception as e:
                logger.warning(f"Index refresh failed: {e}")
