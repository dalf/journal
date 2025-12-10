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
CROSSREF_TITLE_LIST_URL = "https://ftp.crossref.org/titlelist/titleFile.csv"
EUROPEPMC_BULK_URL = "https://europepmc.org/ftp/pmclitemetadata/PMCLiteMetadata.tgz"
DOAJ_CSV_URL = "https://doaj.org/csv"  # Redirects to S3, weekly updates
NLM_CATALOG_URL = "https://ftp.ncbi.nih.gov/pubmed/J_Entrez.txt"
NLM_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# LSIOU (List of Serials Indexed for Online Users) - MEDLINE journal list
# Contains all journals ever indexed for MEDLINE including historical/ceased titles
# See: https://www.nlm.nih.gov/tsd/serials/lsiou.html
# Note: 2024 is the final edition (application no longer maintained after 2024)
LSIOU_FTP_URL = "ftp://ftp.nlm.nih.gov/online/journals/lsi2024.xml"
LSIOU_FILENAME = "lsi2024.xml"

# OpenAlex S3 configuration (public bucket, no credentials needed)
OPENALEX_S3_BUCKET = "openalex"
OPENALEX_S3_PREFIX = "data/sources/"

# Runtime flags
SKIP_CHECKSUM_VALIDATION = False
