"""
ISSN Data Downloader

Downloads journal/ISSN data from multiple sources:
1. ISSN Official (ISSN-L table)
2. Crossref (REST API with cursor pagination)
3. OpenAlex (sources data)
4. PMC (PubMed Central journal list)
5. DOAJ (Directory of Open Access Journals)
6. NLM Catalog (Entrez journal list with abbreviations)

Usage:
    python -m sibils_journals download [--output-dir ./data/raw] [--sources all]
    python -m sibils_journals download --yes  # Non-interactive mode
"""

import argparse
import hashlib
import logging
import time
from pathlib import Path
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util.retry import Retry

from .config import (
    CONTACT_EMAIL,
    CROSSREF_API_URL,
    DEFAULT_RAW_DIR,
    DOAJ_CSV_URL,
    JSTAGE_URL,
    LSIOU_FILENAME,
    LSIOU_FTP_URL,
    NLM_CATALOG_URL,
    NLM_EUTILS_BASE,
    OPENALEX_S3_BUCKET,
    OPENALEX_S3_PREFIX,
    PMC_JLIST_URL,
    WIKIDATA_SPARQL_ENDPOINT,
    WIKIDATA_SPARQL_QUERY,
)

logger = logging.getLogger(__name__)

# Constants
CHUNK_SIZE = 8192
DOWNLOAD_TIMEOUT = 300  # 5 minutes for large files
CONNECT_TIMEOUT = 30
NLM_BATCH_SIZE = 200  # Max IDs per esummary request


def create_session_with_retries(
    retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: tuple = (500, 502, 503, 504),
) -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def setup_output_dir(output_dir: Path) -> dict[str, Path]:
    """Create output directory structure."""
    dirs = {
        "base": output_dir,
        "issn": output_dir / "issn",
        "crossref": output_dir / "crossref",
        "openalex": output_dir / "openalex",
        "pmc": output_dir / "pmc",
        "doaj": output_dir / "doaj",
        "nlm": output_dir / "nlm",
        "lsiou": output_dir / "lsiou",
        "jstage": output_dir / "jstage",
        "wikidata": output_dir / "wikidata",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def get_file_hash(filepath: Path, algorithm: str = "md5") -> Optional[str]:
    """Calculate hash of a file for verification."""
    if not filepath.exists():
        return None

    hash_obj = hashlib.new(algorithm)
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def download_file(
    url: str,
    output_path: Path,
    description: str = "Downloading",
    session: Optional[requests.Session] = None,
) -> bool:
    """
    Download a file with progress bar and integrity validation.

    Args:
        url: URL to download from
        output_path: Path to save the file
        description: Description for progress bar
        session: Optional requests session with retry logic

    Returns:
        True if download succeeded and validated, False otherwise
    """
    session = session or create_session_with_retries()

    try:
        response = session.get(
            url,
            stream=True,
            timeout=(CONNECT_TIMEOUT, DOWNLOAD_TIMEOUT),
        )
        response.raise_for_status()

        # Get expected size and ETag from headers
        expected_size = int(response.headers.get("content-length", 0))

        # Download with progress bar
        bytes_downloaded = 0
        with open(output_path, "wb") as f:
            with tqdm(
                total=expected_size,
                unit="B",
                unit_scale=True,
                desc=description,
                disable=expected_size == 0,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        pbar.update(len(chunk))

        # Validate file size
        actual_size = output_path.stat().st_size
        if expected_size > 0 and actual_size != expected_size:
            logger.error(f"Size mismatch: expected {expected_size:,} bytes, got {actual_size:,} bytes")
            output_path.unlink()  # Remove incomplete file
            return False

        logger.info(f"Downloaded {actual_size:,} bytes to: {output_path}")
        return True

    except requests.RequestException as e:
        logger.error(f"Error downloading {url}: {e}")
        if output_path.exists():
            output_path.unlink()  # Clean up partial file
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if output_path.exists():
            output_path.unlink()  # Clean up partial file
        return False


def prompt_user(message: str, default: bool = False, force_yes: bool = False) -> bool:
    """
    Prompt user for yes/no confirmation.

    Args:
        message: Message to display
        default: Default value if user just presses Enter
        force_yes: If True, skip prompt and return True

    Returns:
        User's choice as boolean
    """
    if force_yes:
        return True

    default_str = "[Y/n]" if default else "[y/N]"
    try:
        response = input(f"{message} {default_str}: ").strip().lower()
        if not response:
            return default
        return response in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()  # Newline after ^C
        return False


def download_issn_official(dirs: dict[str, Path], force_yes: bool = False) -> None:
    """
    Download ISSN official data.

    ISSN-L table requires registration at issn.org
    """
    logger.info("=" * 60)
    logger.info("ISSN Official Data")
    logger.info("=" * 60)

    # ISSN-L Table (requires registration)
    issn_l_path = dirs["issn"] / "issnltables.zip"
    logger.info("[ISSN-L Matching Table]")
    logger.info("  The ISSN-L table requires free registration at:")
    logger.info("  https://www.issn.org/services/online-services/access-to-issn-l-table/")
    logger.info("  After registration, download and place the file at:")
    logger.info(f"  {issn_l_path}")

    if issn_l_path.exists():
        file_hash = get_file_hash(issn_l_path)
        logger.info(f"  Found existing file: {issn_l_path} (MD5: {file_hash})")
    else:
        logger.warning("  File not found - please download manually.")


def download_crossref(dirs: dict[str, Path], force_yes: bool = False) -> None:
    """
    Download Crossref journal data via REST API.

    Uses cursor-based pagination to fetch all journals from the Crossref API.
    The API provides daily updates and richer data than the legacy CSV.

    See: https://api.crossref.org/
    See: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
    """
    import json

    logger.info("=" * 60)
    logger.info("Crossref REST API (Journals)")
    logger.info("=" * 60)

    output_path = dirs["crossref"] / "journals.json"

    if output_path.exists():
        file_size = output_path.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"  Found existing file: {output_path} ({file_size:.1f} MB)")
        if not prompt_user("  Re-download?", default=False, force_yes=force_yes):
            return

    logger.info(f"  Fetching from: {CROSSREF_API_URL}")
    logger.info("  Using cursor pagination (1000 journals per request)")

    session = create_session_with_retries()
    journals = []
    cursor = "*"
    rows_per_page = 1000
    total_results = None

    # Use mailto for polite pool (3 req/sec for list queries)
    # See: https://www.crossref.org/blog/announcing-changes-to-rest-api-rate-limits/
    params = {
        "rows": rows_per_page,
        "mailto": CONTACT_EMAIL,
    }

    # Rate limiting: polite pool allows 3 req/sec for list queries
    # Use 0.35s delay (~2.8 req/sec) to stay safely under limit
    request_delay = 0.35
    last_request_time = 0.0

    with tqdm(desc="Crossref journals", unit=" journals") as pbar:
        while True:
            params["cursor"] = cursor

            # Rate limiting
            elapsed = time.time() - last_request_time
            if elapsed < request_delay:
                time.sleep(request_delay - elapsed)

            try:
                last_request_time = time.time()
                response = session.get(
                    CROSSREF_API_URL,
                    params=params,
                    timeout=(CONNECT_TIMEOUT, DOWNLOAD_TIMEOUT),
                )

                # Handle rate limiting (429 Too Many Requests)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    logger.warning(f"  Rate limited, waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue

                # Handle cursor expiration (400 Bad Request)
                # Cursors expire after 5 minutes of inactivity
                if response.status_code == 400:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", "")
                        if isinstance(error_msg, dict):
                            error_msg = error_msg.get("error", "")
                    except Exception:
                        error_msg = response.text
                    if "cursor" in str(error_msg).lower():
                        logger.error(f"  Cursor expired after {len(journals):,} journals - please restart download")
                    else:
                        logger.error(f"  Bad request: {error_msg}")
                    break

                response.raise_for_status()
                data = response.json()
            except Exception as e:
                logger.error(f"  API request failed: {e}")
                break

            message = data.get("message", {})
            items = message.get("items", [])

            if total_results is None:
                total_results = message.get("total-results", 0)
                pbar.total = total_results
                logger.info(f"  Total journals available: {total_results:,}")

            journals.extend(items)
            pbar.update(len(items))

            # Stop if we got fewer items than requested (last page)
            if len(items) < rows_per_page:
                break

            # Get next cursor
            next_cursor = message.get("next-cursor")
            if not next_cursor:
                break
            cursor = next_cursor

    logger.info(f"  Downloaded {len(journals):,} journals")

    # Save as JSON
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(journals, f, ensure_ascii=False)
        file_size = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"  Saved to: {output_path} ({file_size:.1f} MB)")
    except Exception as e:
        logger.error(f"  Failed to save: {e}")


def download_openalex(dirs: dict[str, Path], force_yes: bool = False) -> None:
    """
    Download OpenAlex sources data from S3 using boto3.

    Uses boto3 with unsigned requests (no AWS credentials needed).
    The OpenAlex bucket is public and accessible without authentication.
    """
    try:
        import boto3
        from botocore import UNSIGNED
        from botocore.config import Config
    except ImportError:
        logger.error("  boto3 not installed. Install with: uv add boto3")
        return

    logger.info("=" * 60)
    logger.info("OpenAlex Sources Data")
    logger.info("=" * 60)

    output_path = dirs["openalex"]

    # Check existing files - use recursive glob for nested structure
    existing_files = list(output_path.glob("**/*.gz"))
    force_redownload = False
    if existing_files:
        logger.info(f"  Found {len(existing_files)} existing files in {output_path}")
        # Check if we have ETags for proper sync detection
        etag_files = list(output_path.glob("**/*.etag"))
        if etag_files:
            logger.info(f"  ({len(etag_files)} files have ETags for change detection)")
            if not prompt_user("  Re-sync from S3?", default=False, force_yes=force_yes):
                return
        else:
            logger.info("  (No ETags stored - cannot detect changes)")
            if not prompt_user("  Force re-download all files?", default=False, force_yes=force_yes):
                return
            force_redownload = True

    logger.info("  Downloading from S3 using boto3...")

    # Create unsigned S3 client (no credentials needed for public bucket)
    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
    bucket_name = OPENALEX_S3_BUCKET
    prefix = OPENALEX_S3_PREFIX

    try:
        # List all objects in the sources prefix
        logger.info("  Listing files in OpenAlex S3 bucket...")
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        # Collect all files to download with ETag for proper sync
        files_to_download = []
        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".gz"):
                    # ETag is the MD5 hash (for non-multipart uploads)
                    etag = obj.get("ETag", "").strip('"')
                    files_to_download.append((key, obj["Size"], etag))

        if not files_to_download:
            logger.warning("  No files found in OpenAlex sources bucket")
            return

        logger.info(f"  Found {len(files_to_download)} files to download")
        total_size = sum(size for _, size, _ in files_to_download)
        logger.info(f"  Total size: {total_size / (1024**3):.2f} GB")

        # Download each file with progress
        downloaded = 0
        skipped = 0
        for key, size, etag in tqdm(files_to_download, desc="OpenAlex files"):
            # Determine local path (preserve directory structure)
            relative_path = key[len(prefix) :]  # Remove prefix
            local_path = output_path / relative_path
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if file needs update using size and ETag
            if local_path.exists() and not force_redownload:
                local_size = local_path.stat().st_size
                if local_size == size:
                    # Size matches - check ETag if we have a stored one
                    etag_path = local_path.with_suffix(local_path.suffix + ".etag")
                    if etag_path.exists():
                        stored_etag = etag_path.read_text().strip()
                        if stored_etag == etag:
                            skipped += 1
                            continue
                    # No stored ETag but size matches - need to download to get ETag
                    # Fall through to download

            # Download file
            s3.download_file(bucket_name, key, str(local_path))
            downloaded += 1

            # Store ETag for future comparisons
            etag_path = local_path.with_suffix(local_path.suffix + ".etag")
            etag_path.write_text(etag)

        logger.info(f"  Downloaded {downloaded} files, skipped {skipped} (up to date)")
        final_files = list(output_path.glob("**/*.gz"))
        logger.info(f"  Synced to: {output_path}")
        logger.info(f"  Total files: {len(final_files)}")

    except Exception as e:
        logger.error(f"  Error downloading OpenAlex data: {e}")
        import traceback

        logger.debug(traceback.format_exc())


def download_pmc(
    dirs: dict[str, Path],
    force_yes: bool = False,
) -> None:
    """
    Download PMC (PubMed Central) journal list CSV.

    Downloads the official list of journals with PMC deposit agreements
    from NCBI. This is a lightweight file (~1.1 MB) that provides
    authoritative PMC indexing status plus publisher and embargo info.

    See: https://pmc.ncbi.nlm.nih.gov/journals/
    """
    logger.info("=" * 60)
    logger.info("PMC Journal List")
    logger.info("=" * 60)

    output_path = dirs["pmc"] / "jlist.csv"

    if output_path.exists():
        file_size = output_path.stat().st_size / 1024  # KB
        logger.info(f"  Found existing file: {output_path} ({file_size:.1f} KB)")
        if not prompt_user("  Re-download?", default=False, force_yes=force_yes):
            return

    logger.info(f"  Downloading from: {PMC_JLIST_URL}")

    session = create_session_with_retries()
    success = download_file(
        PMC_JLIST_URL,
        output_path,
        "PMC Journal List",
        session,
    )

    if success:
        file_size = output_path.stat().st_size / 1024
        logger.info(f"  Downloaded {file_size:.1f} KB to: {output_path}")
    else:
        logger.error("  Download failed.")


def download_doaj(dirs: dict[str, Path], force_yes: bool = False) -> None:
    """
    Download DOAJ (Directory of Open Access Journals) CSV.

    Downloads the journal metadata CSV from DOAJ, which contains
    comprehensive information about open access journals including
    ISSN, title, publisher, country, APC info, and more.

    See: https://doaj.org/docs/public-data-dump/
    License: CC BY-SA 4.0
    """
    logger.info("=" * 60)
    logger.info("DOAJ (Directory of Open Access Journals)")
    logger.info("=" * 60)

    output_path = dirs["doaj"] / "journals.csv"

    if output_path.exists():
        file_size = output_path.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"  Found existing file: {output_path} ({file_size:.1f} MB)")
        if not prompt_user("  Re-download?", default=False, force_yes=force_yes):
            return

    logger.info(f"  Downloading from: {DOAJ_CSV_URL}")
    logger.info("  Note: URL redirects to S3, this may take a moment...")

    session = create_session_with_retries()
    success = download_file(
        DOAJ_CSV_URL,
        output_path,
        "DOAJ CSV",
        session,
    )

    if success:
        file_size = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"  Downloaded {file_size:.1f} MB to: {output_path}")
    else:
        logger.error("  Download failed.")


def download_nlm(dirs: dict[str, Path], force_yes: bool = False) -> None:
    """
    Download NLM Catalog journal list (J_Entrez.txt).

    Downloads the Entrez journal list from NCBI, which contains journal titles,
    MEDLINE abbreviations (MedAbbr), ISO abbreviations, ISSNs, and NLM IDs.

    Why J_Entrez.txt instead of J_Medline.txt?
    ------------------------------------------
    NCBI provides two journal list files:

    - J_Medline.txt (~35k records): Only journals currently indexed for MEDLINE
    - J_Entrez.txt (~41k records): All journals in any NCBI Entrez database,
      including MEDLINE + PMC (PubMed Central) + historical journals

    J_Entrez.txt is more comprehensive and includes major journals like
    "The Journal of Biological Chemistry" (ISSN 0021-9258) that became
    open-access via PMC and may not appear in J_Medline.txt.

    See: https://www.nlm.nih.gov/bsd/serfile_addedinfo.html
    See: https://www.nlm.nih.gov/bsd/difference.html
    """
    logger.info("=" * 60)
    logger.info("NLM Catalog (Entrez Journal List)")
    logger.info("=" * 60)

    output_path = dirs["nlm"] / "J_Entrez.txt"

    if output_path.exists():
        file_size = output_path.stat().st_size / 1024  # KB
        logger.info(f"  Found existing file: {output_path} ({file_size:.1f} KB)")
        if not prompt_user("  Re-download?", default=False, force_yes=force_yes):
            return

    logger.info(f"  Downloading from: {NLM_CATALOG_URL}")

    session = create_session_with_retries()
    success = download_file(
        NLM_CATALOG_URL,
        output_path,
        "NLM Catalog",
        session,
    )

    if success:
        file_size = output_path.stat().st_size / 1024
        logger.info(f"  Downloaded {file_size:.1f} KB to: {output_path}")
    else:
        logger.error("  Download failed.")


def download_nlm_indexed(dirs: dict[str, Path], force_yes: bool = False) -> None:
    """
    Download currently indexed journal ISSNs from NLM Catalog API.

    Uses NCBI E-utilities to fetch the list of journals currently indexed
    in MEDLINE, then extracts their ISSNs into a simple text file for
    efficient lookup during the unification step.

    See: https://www.ncbi.nlm.nih.gov/books/NBK25500/
    """
    import time

    logger.info("=" * 60)
    logger.info("NLM Catalog API (Currently Indexed Journals)")
    logger.info("=" * 60)

    output_path = dirs["nlm"] / "currently_indexed_issns.txt"

    if output_path.exists():
        with open(output_path) as f:
            line_count = sum(1 for _ in f)
        logger.info(f"  Found existing file: {output_path} ({line_count:,} ISSNs)")
        if not prompt_user("  Re-download from API?", default=False, force_yes=force_yes):
            return

    session = create_session_with_retries()

    # Step 1: Search for all currently indexed journal IDs
    logger.info("  Querying NLM Catalog for currently indexed journals...")
    search_url = f"{NLM_EUTILS_BASE}/esearch.fcgi"
    search_params = {
        "db": "nlmcatalog",
        "term": "currentlyindexed",
        "retmax": 10000,  # Get all IDs at once
        "retmode": "json",
        "email": CONTACT_EMAIL,
    }

    try:
        resp = session.get(search_url, params=search_params, timeout=60)
        resp.raise_for_status()
        search_data = resp.json()
        ids = search_data.get("esearchresult", {}).get("idlist", [])
        total_count = int(search_data.get("esearchresult", {}).get("count", 0))

        if not ids:
            logger.error("  No journals found!")
            return

        logger.info(f"  Found {total_count:,} currently indexed journals")

        if total_count > len(ids):
            logger.warning(f"  Only retrieved {len(ids):,} of {total_count:,} IDs - increase retmax or add pagination!")

        # Step 2: Fetch summaries in batches and extract ISSNs
        all_issns: set[str] = set()
        batches = [ids[i : i + NLM_BATCH_SIZE] for i in range(0, len(ids), NLM_BATCH_SIZE)]

        logger.info(f"  Fetching ISSNs in {len(batches)} batches...")
        summary_url = f"{NLM_EUTILS_BASE}/esummary.fcgi"

        for batch in tqdm(batches, desc="NLM API"):
            summary_params = {
                "db": "nlmcatalog",
                "id": ",".join(batch),
                "retmode": "json",
                "email": CONTACT_EMAIL,
            }

            resp = session.get(summary_url, params=summary_params, timeout=120)
            resp.raise_for_status()

            result = resp.json().get("result", {})
            for uid in result.get("uids", []):
                record = result.get(uid, {})
                issn_list = record.get("issnlist", [])

                for issn_entry in issn_list:
                    issn = issn_entry.get("issn", "").strip().upper()
                    if issn:
                        all_issns.add(issn)

            # Rate limit: NCBI allows 3 requests/sec without API key
            # See: https://www.ncbi.nlm.nih.gov/books/NBK25497/
            time.sleep(0.35)

        # Step 3: Write ISSNs to file
        sorted_issns = sorted(all_issns)
        with open(output_path, "w") as f:
            for issn in sorted_issns:
                f.write(f"{issn}\n")

        logger.info(f"  Extracted {len(sorted_issns):,} unique ISSNs")
        logger.info(f"  Saved to: {output_path}")

    except requests.RequestException as e:
        logger.error(f"  API request failed: {e}")
    except Exception as e:
        logger.error(f"  Error: {e}")
        import traceback

        logger.debug(traceback.format_exc())


def download_lsiou(dirs: dict[str, Path], force_yes: bool = False) -> None:
    """
    Download LSIOU (List of Serials Indexed for Online Users) XML from NLM FTP.

    LSIOU contains all journals ever indexed for MEDLINE, including currently
    indexed, historical, and ceased titles. This is the most authoritative
    source for MEDLINE journal metadata.

    Key features:
    - 15,473 titles (2024 edition)
    - Native ISSN-L (ISSNLinking) field
    - Includes ~5,294 currently indexed + ~10,000 historical titles
    - Structured XML format

    See: https://www.nlm.nih.gov/tsd/serials/lsiou.html
    """
    import ftplib
    import tempfile

    logger.info("=" * 60)
    logger.info("LSIOU (List of Serials Indexed for Online Users)")
    logger.info("=" * 60)

    output_path = dirs["lsiou"] / LSIOU_FILENAME

    if output_path.exists():
        file_size = output_path.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"  Found existing file: {output_path} ({file_size:.1f} MB)")
        if not prompt_user("  Re-download?", default=False, force_yes=force_yes):
            return

    logger.info(f"  Downloading from: {LSIOU_FTP_URL}")
    logger.info("  Note: Using FTP protocol for NLM server...")

    try:
        # Parse FTP URL
        # ftp://ftp.nlm.nih.gov/online/journals/lsi2025.xml
        ftp_host = "ftp.nlm.nih.gov"
        ftp_path = "/online/journals/"

        # Connect to FTP server
        logger.info(f"  Connecting to {ftp_host}...")
        ftp = ftplib.FTP(ftp_host, timeout=60)
        ftp.login()  # Anonymous login

        # Switch to binary mode (required for SIZE command)
        ftp.voidcmd("TYPE I")

        # Navigate to directory
        ftp.cwd(ftp_path)

        # Get file size for progress bar
        file_size = ftp.size(LSIOU_FILENAME)
        logger.info(f"  File size: {file_size / (1024 * 1024):.1f} MB")

        # Download to temp file first, then move
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)

            bytes_downloaded = [0]  # Use list to allow modification in callback

            def write_callback(data):
                tmp_file.write(data)
                bytes_downloaded[0] += len(data)

            with tqdm(
                total=file_size,
                unit="B",
                unit_scale=True,
                desc="LSIOU XML",
            ) as pbar:

                def progress_callback(data):
                    write_callback(data)
                    pbar.update(len(data))

                ftp.retrbinary(f"RETR {LSIOU_FILENAME}", progress_callback, blocksize=8192)

        ftp.quit()

        # Move temp file to final location
        import shutil

        shutil.move(tmp_path, output_path)

        actual_size = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"  Downloaded {actual_size:.1f} MB to: {output_path}")

    except ftplib.all_errors as e:
        logger.error(f"  FTP error: {e}")
        if output_path.exists():
            output_path.unlink()
    except Exception as e:
        logger.error(f"  Error downloading LSIOU: {e}")
        import traceback

        logger.debug(traceback.format_exc())
        if output_path.exists():
            output_path.unlink()


def download_jstage(dirs: dict[str, Path], force_yes: bool = False) -> None:
    """
    Download J-STAGE journal list.

    J-STAGE (Japan Science and Technology Information Aggregator, Electronic)
    is Japan's largest platform for academic e-journals, operated by the
    Japan Science and Technology Agency (JST).

    Downloads a ZIP file containing a tab-separated journal list with
    ISSNs, titles, publishers, and open access status.

    See: https://www.jstage.jst.go.jp/
    """
    import zipfile

    logger.info("=" * 60)
    logger.info("J-STAGE (Japan Science and Technology)")
    logger.info("=" * 60)

    output_path = dirs["jstage"] / "journals_list_en.txt"
    zip_path = dirs["jstage"] / "journals_list_en.zip"

    if output_path.exists():
        file_size = output_path.stat().st_size / 1024  # KB
        logger.info(f"  Found existing file: {output_path} ({file_size:.1f} KB)")
        if not prompt_user("  Re-download?", default=False, force_yes=force_yes):
            return

    logger.info(f"  Downloading from: {JSTAGE_URL}")

    session = create_session_with_retries()
    success = download_file(
        JSTAGE_URL,
        zip_path,
        "J-STAGE ZIP",
        session,
    )

    if success:
        # Extract the ZIP file
        logger.info("  Extracting ZIP file...")
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(dirs["jstage"])
            zip_path.unlink()  # Remove ZIP after extraction

            if output_path.exists():
                file_size = output_path.stat().st_size / 1024
                logger.info(f"  Extracted {file_size:.1f} KB to: {output_path}")
            else:
                logger.error("  Extraction failed: expected file not found")
        except zipfile.BadZipFile as e:
            logger.error(f"  Invalid ZIP file: {e}")
            if zip_path.exists():
                zip_path.unlink()
    else:
        logger.error("  Download failed.")


def download_wikidata(dirs: dict[str, Path], force_yes: bool = False) -> None:
    """
    Download Wikidata journal data via SPARQL query.

    Executes a SPARQL query against the Wikidata Query Service to fetch
    journals that have ISSN-L but do NOT have NLM or OpenAlex IDs.
    This fills gaps in coverage from other sources.

    See: https://query.wikidata.org/
    """
    import json

    logger.info("=" * 60)
    logger.info("Wikidata SPARQL (Gap-filling journals)")
    logger.info("=" * 60)

    output_path = dirs["wikidata"] / "sparql_results.json"

    if output_path.exists():
        file_size = output_path.stat().st_size / 1024  # KB
        logger.info(f"  Found existing file: {output_path} ({file_size:.1f} KB)")
        if not prompt_user("  Re-download?", default=False, force_yes=force_yes):
            return

    logger.info(f"  Querying: {WIKIDATA_SPARQL_ENDPOINT}")
    logger.info("  Note: Fetching journals without NLM/OpenAlex IDs...")

    session = create_session_with_retries()

    try:
        response = session.post(
            WIKIDATA_SPARQL_ENDPOINT,
            data={"query": WIKIDATA_SPARQL_QUERY},
            headers={
                "Accept": "application/json",
                "User-Agent": f"SIBiLS-Journals/1.0 ({CONTACT_EMAIL})",
            },
            timeout=(CONNECT_TIMEOUT, DOWNLOAD_TIMEOUT),
        )
        response.raise_for_status()

        # Parse JSON to validate and get stats
        data = response.json()
        results = data.get("results", {}).get("bindings", [])

        # Count unique items
        items = set()
        for row in results:
            item_uri = row.get("item", {}).get("value", "")
            if item_uri:
                items.add(item_uri)

        logger.info(f"  Retrieved {len(results):,} rows ({len(items):,} unique journals)")

        # Save to file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        file_size = output_path.stat().st_size / 1024
        logger.info(f"  Saved {file_size:.1f} KB to: {output_path}")

    except requests.RequestException as e:
        logger.error(f"  SPARQL query failed: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"  Invalid JSON response: {e}")
    except Exception as e:
        logger.error(f"  Error: {e}")
        import traceback

        logger.debug(traceback.format_exc())


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="Download ISSN data from multiple sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Interactive mode, all sources
  %(prog)s --yes                    # Non-interactive, skip prompts
  %(prog)s --sources crossref,openalex  # Specific sources only
        """,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help=f"Output directory (default: {DEFAULT_RAW_DIR})",
    )
    parser.add_argument(
        "--sources",
        type=str,
        default="all",
        help="Sources to download: all, issn, crossref, openalex, pmc, doaj, nlm, lsiou, jstage, wikidata (comma-separated)",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Non-interactive mode: answer yes to all prompts",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose/debug logging",
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse sources
    valid_sources = {"issn", "crossref", "openalex", "pmc", "doaj", "nlm", "lsiou", "jstage", "wikidata"}
    if args.sources.lower() == "all":
        sources = valid_sources.copy()
    else:
        sources = {s.strip().lower() for s in args.sources.split(",")}
        invalid = sources - valid_sources
        if invalid:
            logger.error(f"Invalid sources: {invalid}. Valid: {valid_sources}")
            return 1

    logger.info("ISSN Data Downloader")
    logger.info("=" * 60)
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Sources: {', '.join(sorted(sources))}")
    logger.info(f"Interactive mode: {'No' if args.yes else 'Yes'}")

    # Setup directories
    dirs = setup_output_dir(args.output_dir)

    # Download each source
    if "issn" in sources:
        download_issn_official(dirs, force_yes=args.yes)

    if "crossref" in sources:
        download_crossref(dirs, force_yes=args.yes)

    if "openalex" in sources:
        download_openalex(dirs, force_yes=args.yes)

    if "pmc" in sources:
        download_pmc(dirs, force_yes=args.yes)

    if "doaj" in sources:
        download_doaj(dirs, force_yes=args.yes)

    if "nlm" in sources:
        download_nlm(dirs, force_yes=args.yes)
        download_nlm_indexed(dirs, force_yes=args.yes)

    if "lsiou" in sources:
        download_lsiou(dirs, force_yes=args.yes)

    if "jstage" in sources:
        download_jstage(dirs, force_yes=args.yes)

    if "wikidata" in sources:
        download_wikidata(dirs, force_yes=args.yes)

    logger.info("=" * 60)
    logger.info("Download Complete!")
    logger.info("=" * 60)
    logger.info(f"Data saved to: {args.output_dir}")
    logger.info("Next step: Run 'python -m sibils_journals unify' to merge the data")

    return 0


if __name__ == "__main__":
    exit(main() or 0)
