"""EuropePMC bulk XML metadata loader using chunked regex parsing."""

import gzip
import hashlib
import html
import json
import logging
import re
import tarfile
import tempfile
from pathlib import Path
from typing import IO, Iterator, Optional, get_type_hints

from tqdm import tqdm

from ..models import DataSource, JournalDict
from ..normalizers import normalize_issn, normalize_title
from .utils import deduplicate_journals

logger = logging.getLogger(__name__)

# Cache file name (gzip compressed for faster I/O)
CACHE_FILENAME = "journals_cache.json.gz"


def get_schema_hash() -> str:
    """Compute hash of JournalDict schema for cache validation.

    Uses field names and their string type representations.
    Hash changes when fields are added, removed, or their types change.
    """
    hints = get_type_hints(JournalDict)
    # Sort for deterministic order, stringify types for hashing
    schema_str = str(sorted((k, str(v)) for k, v in hints.items()))
    return hashlib.md5(schema_str.encode()).hexdigest()[:8]


# Chunk size for reading large XML files (10MB)
CHUNK_SIZE = 10 * 1024 * 1024

# Regex patterns for extracting journal info from articles
ARTICLE_PATTERN = re.compile(rb"<PMC_ARTICLE[^>]*>(.*?)</PMC_ARTICLE>", re.DOTALL)
JOURNAL_TITLE_PATTERN = re.compile(rb"<JournalTitle>([^<]*)</JournalTitle>")
JOURNAL_ISSN_PATTERN = re.compile(rb"<JournalIssn>([^<]*)</JournalIssn>")

# End tag for finding chunk boundaries
ARTICLE_END_TAG = b"</PMC_ARTICLE>"


def parse_europepmc_issn(issn_string: Optional[str]) -> Optional[str]:
    """
    Parse and normalize EuropePMC ISSN string.

    Returns normalized ISSN or None if invalid.
    """
    if not issn_string:
        return None

    issn = normalize_issn(issn_string.strip(), validate_checksum=False)
    return issn


def process_europepmc_record(issn: str, title: Optional[str] = None) -> JournalDict:
    """
    Transform EuropePMC data into a JournalDict.

    Args:
        issn: Normalized ISSN
        title: Optional normalized title

    Returns:
        JournalDict with source metadata
    """
    return {
        "title": title,
        "publisher": None,
        "issn_print": issn,
        "issn_electronic": None,
        "country": None,
        "source": DataSource.EUROPEPMC,
        "is_pmc_indexed": True,
    }


def extract_journals_from_data(data: bytes) -> Iterator[tuple[str, Optional[str]]]:
    """
    Extract journal info from article data using regex.

    Args:
        data: Bytes containing complete PMC_ARTICLE elements

    Yields:
        Tuple of (issn, title) for each article with valid ISSN
    """
    for article_match in ARTICLE_PATTERN.finditer(data):
        article_content = article_match.group(1)

        # Extract ISSN first (required)
        issn_match = JOURNAL_ISSN_PATTERN.search(article_content)
        if not issn_match:
            continue

        try:
            issn_text = issn_match.group(1).decode("utf-8", errors="replace")
            issn = parse_europepmc_issn(issn_text)
            if not issn:
                continue
        except Exception:
            continue

        # Extract journal title (optional)
        title = None
        title_match = JOURNAL_TITLE_PATTERN.search(article_content)
        if title_match:
            try:
                title_text = title_match.group(1).decode("utf-8", errors="replace")
                title_text = html.unescape(title_text)
                title = normalize_title(title_text)
            except Exception:
                pass

        yield issn, title


def iter_tar_xml_files(tgz_path: Path) -> Iterator[tuple[str, IO[bytes]]]:
    """
    Yield (member_name, file_object) for each XML file in tar archive.

    Handles corruption gracefully and shows progress bar based on compressed size.
    """
    total_size = tgz_path.stat().st_size
    last_pos = 0

    with open(tgz_path, "rb") as raw_file:
        with tarfile.open(fileobj=raw_file, mode="r:gz", errorlevel=0) as tar:
            pbar = tqdm(
                total=total_size,
                desc="EuropePMC",
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
            )
            try:
                for member in tar:
                    if not member.name.endswith(".xml"):
                        continue

                    f = tar.extractfile(member)
                    if f is None:
                        continue

                    yield member.name, f

                    # Update progress after caller processes file
                    current_pos = raw_file.tell()
                    pbar.update(current_pos - last_pos)
                    last_pos = current_pos

            except (EOFError, OSError, tarfile.ReadError) as e:
                logger.warning(f"  Archive corruption encountered: {e}")

            finally:
                pbar.close()


def iter_complete_articles(f: IO[bytes]) -> Iterator[bytes]:
    """
    Yield chunks containing only complete PMC_ARTICLE elements.

    Buffers incomplete articles across chunk boundaries.
    """
    buffer = b""

    while True:
        chunk = f.read(CHUNK_SIZE)
        if not chunk:
            break

        data = buffer + chunk

        # Find last complete article boundary
        last_end = data.rfind(ARTICLE_END_TAG)
        if last_end == -1:
            # No complete article yet, keep buffering
            buffer = data
            continue

        # Include the closing tag
        last_end += len(ARTICLE_END_TAG)

        yield data[:last_end]

        # Buffer incomplete remainder
        buffer = data[last_end:]

    # Yield any remaining data
    if buffer:
        yield buffer


def load_cache(cache_path: Path, tgz_path: Path) -> list[JournalDict] | None:
    """
    Load journals from cache if valid.

    Returns cached journals if cache exists and is newer than source file.
    Returns None if cache is invalid or missing.
    """
    if not cache_path.exists():
        return None

    # Check if cache is newer than source
    cache_mtime = cache_path.stat().st_mtime
    source_mtime = tgz_path.stat().st_mtime

    if cache_mtime < source_mtime:
        logger.info("  Cache is older than source, will re-extract")
        return None

    # Compute schema hash once (used for validation)
    expected_hash = get_schema_hash()

    try:
        with gzip.open(cache_path, "rt", encoding="utf-8") as f:
            cache_data = json.load(f)

        # Schema hash check
        cached_hash = cache_data.get("schema_hash")
        if cached_hash != expected_hash:
            logger.info(f"  Schema changed (cache={cached_hash}, current={expected_hash}), re-extracting")
            return None

        # Validate and convert cached items to JournalDict
        journals = []
        skipped = 0
        for item in cache_data.get("journals", []):
            # Validate required fields for EuropePMC records
            if "issn_print" not in item or "is_pmc_indexed" not in item:
                skipped += 1
                continue
            # Create JournalDict with source (not stored in cache since it's always EUROPEPMC)
            journals.append({**item, "source": DataSource.EUROPEPMC})

        if skipped:
            logger.warning(f"  Skipped {skipped} invalid cache entries (missing required fields)")

        logger.info(f"  Loaded {len(journals):,} journals from cache")
        return journals

    except (json.JSONDecodeError, KeyError, gzip.BadGzipFile, OSError) as e:
        logger.warning(f"  Cache corrupted, will re-extract: {e}")
        return None


def save_cache(cache_path: Path, journals: list[JournalDict]) -> None:
    """Save journals to cache file with atomic write.

    Uses a temporary file and rename to prevent corruption if interrupted.
    """
    tmp_path: Path | None = None
    try:
        # Convert to JSON-serializable format
        # Exclude 'source' field since it's always EUROPEPMC for this loader
        data = []
        for j in journals:
            item = {k: v for k, v in j.items() if k != "source"}
            data.append(item)

        cache_data = {
            "schema_hash": get_schema_hash(),
            "journals": data,
        }

        # Atomic write: write to temp file, then rename
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=cache_path.parent,
            prefix=".cache_",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)
            with gzip.open(tmp, "wt", encoding="utf-8") as gz:
                json.dump(cache_data, gz)

        # Atomic rename (on POSIX systems)
        tmp_path.rename(cache_path)
        logger.info(f"  Saved {len(journals):,} journals to cache")

    except (IOError, OSError) as e:
        logger.warning(f"  Failed to save cache: {e}")
        # Clean up temp file if it exists
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()


def load_europepmc_data(input_dir: Path) -> list[JournalDict]:
    """
    Load EuropePMC journal data from bulk XML metadata dump.

    Uses caching to avoid re-parsing unchanged data. Cache is invalidated
    when the source tgz file is newer than the cache.

    Uses chunked regex parsing for memory efficiency and corruption resilience.
    Extracts unique journals from article metadata.

    See: https://europepmc.org/downloads
    """
    europepmc_dir = input_dir / "europepmc"
    tgz_path = europepmc_dir / "PMCLiteMetadata.tgz"
    cache_path = europepmc_dir / CACHE_FILENAME

    if not tgz_path.exists():
        logger.warning(f"EuropePMC data not found at {tgz_path}, skipping...")
        return []

    logger.info(f"Loading EuropePMC data from: {tgz_path}")

    # Try to load from cache first
    cached = load_cache(cache_path, tgz_path)
    if cached is not None:
        return cached

    logger.info("  Extracting unique journals using chunked regex parsing...")

    journals_dict: dict[str, dict] = {}
    files_processed = 0
    articles_found = 0
    extraction_complete = False

    try:
        for filename, f in iter_tar_xml_files(tgz_path):
            try:
                for data in iter_complete_articles(f):
                    for issn, title in extract_journals_from_data(data):
                        articles_found += 1
                        if issn not in journals_dict:
                            journals_dict[issn] = process_europepmc_record(issn, title)
                        elif title and not journals_dict[issn].get("title"):
                            journals_dict[issn]["title"] = title
                files_processed += 1
            except Exception as e:
                logger.debug(f"  Error processing {filename}: {e}")

        logger.info(f"  Processed {files_processed} XML files, {articles_found:,} articles")
        logger.info(f"  Extracted {len(journals_dict):,} unique journals from EuropePMC")
        extraction_complete = True

    except Exception as e:
        logger.error(f"Error loading EuropePMC data: {e}")
        import traceback

        logger.debug(traceback.format_exc())
        if journals_dict:
            logger.warning(f"  Recovered {len(journals_dict):,} journals before error")

    # Deduplicate within source (dict already prevents duplicates, but for consistency)
    journals = deduplicate_journals(list(journals_dict.values()), "EuropePMC")

    # Only save to cache if extraction completed successfully
    if extraction_complete:
        save_cache(cache_path, journals)

    return journals
