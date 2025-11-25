"""
ISSN Data Downloader

Downloads journal/ISSN data from multiple sources:
1. ISSN Official (ISSN-L table)
2. Crossref (title list CSV)
3. OpenAlex (sources data)
4. EuropePMC (bulk metadata dump)
5. DOAJ (Directory of Open Access Journals)
6. NLM Catalog (Entrez journal list with abbreviations)

Usage:
    python -m issn_unifier download [--output-dir ./data/raw] [--sources all]
    python -m issn_unifier download --yes  # Non-interactive mode
"""

import argparse
import hashlib
import logging
from pathlib import Path
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util.retry import Retry

from .config import (
    CROSSREF_TITLE_LIST_URL,
    DEFAULT_RAW_DIR,
    DOAJ_CSV_URL,
    EUROPEPMC_BULK_URL,
    NLM_CATALOG_URL,
    NLM_EUTILS_BASE,
    OPENALEX_S3_BUCKET,
    OPENALEX_S3_PREFIX,
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
        "europepmc": output_dir / "europepmc",
        "doaj": output_dir / "doaj",
        "nlm": output_dir / "nlm",
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
    """Download Crossref journal title list CSV."""
    logger.info("=" * 60)
    logger.info("Crossref Title List")
    logger.info("=" * 60)

    output_path = dirs["crossref"] / "titleFile.csv"

    if output_path.exists():
        file_size = output_path.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"  Found existing file: {output_path} ({file_size:.1f} MB)")
        if not prompt_user("  Re-download?", default=False, force_yes=force_yes):
            return

    logger.info(f"  Downloading from: {CROSSREF_TITLE_LIST_URL}")
    session = create_session_with_retries()
    download_file(CROSSREF_TITLE_LIST_URL, output_path, "Crossref CSV", session)


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
    if existing_files:
        logger.info(f"  Found {len(existing_files)} existing files in {output_path}")
        if not prompt_user("  Re-sync from S3?", default=False, force_yes=force_yes):
            return

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

        # Collect all files to download
        files_to_download = []
        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".gz"):
                    files_to_download.append((key, obj["Size"]))

        if not files_to_download:
            logger.warning("  No files found in OpenAlex sources bucket")
            return

        logger.info(f"  Found {len(files_to_download)} files to download")
        total_size = sum(size for _, size in files_to_download)
        logger.info(f"  Total size: {total_size / (1024**3):.2f} GB")

        # Download each file with progress
        downloaded = 0
        skipped = 0
        for key, size in tqdm(files_to_download, desc="OpenAlex files"):
            # Determine local path (preserve directory structure)
            relative_path = key[len(prefix) :]  # Remove prefix
            local_path = output_path / relative_path
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Skip if file exists and has same size
            if local_path.exists() and local_path.stat().st_size == size:
                skipped += 1
                continue

            # Download file
            s3.download_file(bucket_name, key, str(local_path))
            downloaded += 1

        logger.info(f"  Downloaded {downloaded} files, skipped {skipped} (already exist)")
        final_files = list(output_path.glob("**/*.gz"))
        logger.info(f"  Synced to: {output_path}")
        logger.info(f"  Total files: {len(final_files)}")

    except Exception as e:
        logger.error(f"  Error downloading OpenAlex data: {e}")
        import traceback

        logger.debug(traceback.format_exc())


def download_europepmc(
    dirs: dict[str, Path],
    force_yes: bool = False,
) -> None:
    """
    Download EuropePMC bulk metadata dump.

    Downloads the weekly PMCLiteMetadata.tgz file containing XML metadata
    for all full-text articles in Europe PMC. Journal information is
    extracted during the unification step.

    See: https://europepmc.org/downloads
    """
    logger.info("=" * 60)
    logger.info("EuropePMC Bulk Metadata")
    logger.info("=" * 60)

    output_path = dirs["europepmc"] / "PMCLiteMetadata.tgz"
    download_url = EUROPEPMC_BULK_URL

    if output_path.exists():
        file_size = output_path.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"  Found existing file: {output_path} ({file_size:.1f} MB)")
        if not prompt_user("  Re-download?", default=False, force_yes=force_yes):
            return

    logger.info(f"  Downloading from: {download_url}")
    logger.info("  Note: This is a large file (~1.5 GB), download may take a while...")

    session = create_session_with_retries()
    success = download_file(
        download_url,
        output_path,
        "EuropePMC Metadata",
        session,
    )

    if success:
        file_size = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"  Downloaded {file_size:.1f} MB to: {output_path}")
    else:
        logger.error("  Download failed. You can retry to download again.")


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
        help="Sources to download: all, issn, crossref, openalex, europepmc, doaj, nlm (comma-separated)",
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
    valid_sources = {"issn", "crossref", "openalex", "europepmc", "doaj", "nlm"}
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

    if "europepmc" in sources:
        download_europepmc(dirs, force_yes=args.yes)

    if "doaj" in sources:
        download_doaj(dirs, force_yes=args.yes)

    if "nlm" in sources:
        download_nlm(dirs, force_yes=args.yes)
        download_nlm_indexed(dirs, force_yes=args.yes)

    logger.info("=" * 60)
    logger.info("Download Complete!")
    logger.info("=" * 60)
    logger.info(f"Data saved to: {args.output_dir}")
    logger.info("Next step: Run 'python -m issn_unifier unify' to merge the data")

    return 0


if __name__ == "__main__":
    exit(main() or 0)
