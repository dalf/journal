"""ISSN-L table loader."""

import logging
import zipfile
from pathlib import Path

from tqdm import tqdm

from ..normalizers import normalize_issn

logger = logging.getLogger(__name__)


def load_issn_l_table(input_dir: Path) -> dict[str, str]:
    """
    Load ISSN-L mapping table.

    Returns a dict mapping ISSN -> ISSN-L
    """
    issn_to_issn_l = {}
    issn_l_path = input_dir / "issn" / "issnltables.zip"

    if not issn_l_path.exists():
        logger.warning("ISSN-L table not found, skipping...")
        return issn_to_issn_l

    logger.info(f"Loading ISSN-L table from: {issn_l_path}")

    try:
        with zipfile.ZipFile(issn_l_path, "r") as zf:
            # Find the text file inside
            txt_files = [f for f in zf.namelist() if f.endswith(".txt") or "ISSN-to-ISSN-L" in f]
            if not txt_files:
                logger.error("No text file found in ISSN-L archive")
                return issn_to_issn_l

            # Get file size for progress bar
            file_info = zf.getinfo(txt_files[0])
            total_size = file_info.file_size

            with zf.open(txt_files[0]) as f:
                with tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    desc="ISSN-L table",
                ) as pbar:
                    for line in f:
                        pbar.update(len(line))
                        line = line.decode("utf-8", errors="ignore").strip()
                        if not line or line.startswith("#") or line.startswith("ISSN"):
                            continue

                        parts = line.split("\t")
                        if len(parts) >= 2:
                            # Don't validate checksum for ISSN-L table (trusted source)
                            issn = normalize_issn(parts[0], validate_checksum=False)
                            issn_l = normalize_issn(parts[1], validate_checksum=False)
                            if issn and issn_l:
                                issn_to_issn_l[issn] = issn_l

        logger.info(f"Loaded {len(issn_to_issn_l):,} ISSN-L mappings")
    except Exception as e:
        logger.error(f"Error loading ISSN-L table: {e}")

    return issn_to_issn_l
