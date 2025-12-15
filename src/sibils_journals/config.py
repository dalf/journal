"""Configuration constants for SIBiLS journals."""

from pathlib import Path

# Default directories
DEFAULT_RAW_DIR = Path("data/raw")
DEFAULT_OUTPUT_DIR = Path("data/unified")
DEFAULT_SIBILS_DIR = Path("data/sibils")

# SIBiLS Elasticsearch configuration
SIBILS_ES_URL = "http://sibils-es.lan.text-analytics.ch:9200/"
DEFAULT_SIBILS_VERSION = "5.0.5.8"

# Data source URLs
CROSSREF_API_URL = "https://api.crossref.org/journals"  # REST API with cursor pagination
PMC_JLIST_URL = "https://cdn.ncbi.nlm.nih.gov/pmc/home/jlist.csv"  # PMC journal list (~1.1 MB)
DOAJ_CSV_URL = "https://doaj.org/csv"  # Redirects to S3, weekly updates
NLM_CATALOG_URL = "https://ftp.ncbi.nih.gov/pubmed/J_Entrez.txt"
NLM_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# J-STAGE (Japan Science and Technology Information Aggregator, Electronic)
# Japan's largest platform for academic e-journals, operated by JST
# See: https://www.jstage.jst.go.jp/
JSTAGE_URL = "https://www.jstage.jst.go.jp/pub/jnllist/journals_list_en.zip"

# LSIOU (List of Serials Indexed for Online Users) - MEDLINE journal list
# Contains all journals ever indexed for MEDLINE including historical/ceased titles
# See: https://www.nlm.nih.gov/tsd/serials/lsiou.html
# Note: 2024 is the final edition (application no longer maintained after 2024)
LSIOU_FTP_URL = "ftp://ftp.nlm.nih.gov/online/journals/lsi2024.xml"
LSIOU_FILENAME = "lsi2024.xml"

# OpenAlex S3 configuration (public bucket, no credentials needed)
OPENALEX_S3_BUCKET = "openalex"
OPENALEX_S3_PREFIX = "data/sources/"

# Wikidata SPARQL configuration
# Query fetches journals (Q5633421) with ISSN-L but WITHOUT IDs from major sources
# This fills gaps in coverage - excludes journals already in NLM, OpenAlex, or Crossref
WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
WIKIDATA_SPARQL_QUERY = """
SELECT ?item ?issn ?issnl ?itemLabel ?countryCode2 ?publisherLabel WHERE {
  ?item wdt:P31 wd:Q5633421 ;
        wdt:P7363 ?issnl .

  OPTIONAL { ?item wdt:P236 ?issn . }

  OPTIONAL {
    ?item wdt:P123 ?publisher .
    ?publisher rdfs:label ?publisherLabel .
    FILTER(LANG(?publisherLabel) = "en")
  }

  # Exclude journals already covered by major sources
  FILTER NOT EXISTS { ?item wdt:P1055 ?nlmId . }       # NLM Unique ID
  FILTER NOT EXISTS { ?item wdt:P10283 ?openalexId . } # OpenAlex ID
  FILTER NOT EXISTS { ?item wdt:P8375 ?crossrefId . }  # Crossref journal ID

  # Country of origin (P495) -> ISO 3166-1 alpha-2 (P297) when available
  OPTIONAL {
    ?item wdt:P495 ?country .
    OPTIONAL { ?country wdt:P297 ?countryCode2 . }
  }

  {
    ?item rdfs:label ?itemLabel .
    FILTER(LANG(?itemLabel) = "en")
  }
  UNION
  {
    FILTER NOT EXISTS {
      ?item rdfs:label ?lEn .
      FILTER(LANG(?lEn) = "en")
    }
    ?item rdfs:label ?itemLabel .
  }
}
""".strip()

# Contact email for API identification (Crossref, NCBI E-utilities)
CONTACT_EMAIL = "contact@sibils.org"

# Runtime flags
SKIP_CHECKSUM_VALIDATION = False
