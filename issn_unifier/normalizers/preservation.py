"""Normalization for digital preservation services."""

from typing import Optional

from ..models import PreservationService
from .utils import partial_match

# Canonical names for digital preservation services
_PRESERVATION_SERVICE_MAPPINGS: dict[str, PreservationService] = {
    # LOCKSS (Lots of Copies Keep Stuff Safe)
    "lockss": PreservationService.LOCKSS,
    "lots of copies keep stuff safe": PreservationService.LOCKSS,
    # CLOCKSS (Controlled LOCKSS)
    "clockss": PreservationService.CLOCKSS,
    "controlled lockss": PreservationService.CLOCKSS,
    # Portico
    "portico": PreservationService.PORTICO,
    # PKP PN (PKP Preservation Network)
    "pkp pn": PreservationService.PKP_PN,
    "pkp preservation network": PreservationService.PKP_PN,
    "pkp": PreservationService.PKP_PN,
    "pkp pln": PreservationService.PKP_PN,
    "public knowledge project pln": PreservationService.PKP_PN,
    # Internet Archive (removed "ia" - too short, causes false matches with "Cariniana" etc.)
    "internet archive": PreservationService.INTERNET_ARCHIVE,
    "archive.org": PreservationService.INTERNET_ARCHIVE,
    # PMC (PubMed Central)
    "pmc": PreservationService.PMC,
    "pubmed central": PreservationService.PMC,
    "europe pmc": PreservationService.EUROPE_PMC,
    "europepmc": PreservationService.EUROPE_PMC,
    "pmc/europe pmc": PreservationService.PMC,
    # JSTOR
    "jstor": PreservationService.JSTOR,
    # Scholars Portal
    "scholars portal": PreservationService.SCHOLARS_PORTAL,
    "scholar's portal": PreservationService.SCHOLARS_PORTAL,
    "scholars' portal": PreservationService.SCHOLARS_PORTAL,
    # Merritt (UC Curation Center)
    "merritt": PreservationService.MERRITT,
    "uc3 merritt": PreservationService.MERRITT,
    # HathiTrust
    "hathitrust": PreservationService.HATHITRUST,
    "hathi trust": PreservationService.HATHITRUST,
    # CINES
    "cines": PreservationService.CINES,
    # British Library
    "british library": PreservationService.BRITISH_LIBRARY,
    # Library of Congress
    "library of congress": PreservationService.LIBRARY_OF_CONGRESS,
    # Koninklijke Bibliotheek (Dutch National Library)
    "kb": PreservationService.KB,
    "koninklijke bibliotheek": PreservationService.KB,
    # Deutsche Nationalbibliothek
    "dnb": PreservationService.DNB,
    "deutsche nationalbibliothek": PreservationService.DNB,
    # Bibliothèque nationale de France
    "bnf": PreservationService.BNF,
    "bibliothèque nationale de france": PreservationService.BNF,
    # National Library of Australia
    "nla": PreservationService.NLA,
    "national library of australia": PreservationService.NLA,
    # Cariniana (Brazilian network)
    "cariniana": PreservationService.CARINIANA,
    "rede cariniana": PreservationService.CARINIANA,
    "cariniana network": PreservationService.CARINIANA,
    "rede brasileira de serviços de preservação digital": PreservationService.CARINIANA,
    # eLIBRARY.RU (Russian)
    "elibrary.ru": PreservationService.ELIBRARY_RU,
    "elibrary": PreservationService.ELIBRARY_RU,
    "e-library": PreservationService.ELIBRARY_RU,
    "e-library.ru": PreservationService.ELIBRARY_RU,
    # Hrčak (Croatian)
    "hrčak": PreservationService.HRCAK,
    "hrcak": PreservationService.HRCAK,
    "hrčak - portal of scientific journals of croatia": PreservationService.HRCAK,
    # NDPP China
    "ndpp": PreservationService.NDPP_CHINA,
    "ndpp china": PreservationService.NDPP_CHINA,
    "china national digital preservation program": PreservationService.NDPP_CHINA,
    "national digital preservation program": PreservationService.NDPP_CHINA,
    # Magiran (Iranian)
    "magiran": PreservationService.MAGIRAN,
    # Noormags (Iranian)
    "noormags": PreservationService.NOORMAGS,
    "noormag": PreservationService.NOORMAGS,
    "noormages": PreservationService.NOORMAGS,
    # PHAIDRA (Austrian)
    "phaidra": PreservationService.PHAIDRA,
    # Zenodo (CERN)
    "zenodo": PreservationService.ZENODO,
    # Science Central (Korean)
    "science central": PreservationService.SCIENCE_CENTRAL,
    "sciencecentral": PreservationService.SCIENCE_CENTRAL,
    # KoreaMed Synapse (Korean medical)
    "koreamedsynapse": PreservationService.KOREAMEDSYNAPSE,
    "koreamedsynapse (koreamed)": PreservationService.KOREAMEDSYNAPSE,
    "koreamed": PreservationService.KOREAMEDSYNAPSE,
    "koreamed synapse": PreservationService.KOREAMEDSYNAPSE,
    "korea med": PreservationService.KOREAMEDSYNAPSE,
    # CEEOL (Central/Eastern European)
    "ceeol": PreservationService.CEEOL,
    "central and eastern european online library": PreservationService.CEEOL,
    # Garuda (Indonesian)
    "garuda": PreservationService.GARUDA,
    "portal garuda": PreservationService.GARUDA,
    # SCIndeks (Serbian)
    "scindeks": PreservationService.SCINDEKS,
    "serbian citation index": PreservationService.SCINDEKS,
    # SID (Iranian)
    "sid": PreservationService.SID,
    "scientific information database": PreservationService.SID,
    # ISC (Iranian)
    "isc": PreservationService.ISC,
    "islamic world science citation center": PreservationService.ISC,
    "islamic world science citation database": PreservationService.ISC,
    "islamic science citation": PreservationService.ISC,
    # RACO (Catalan)
    "raco": PreservationService.RACO,
    "revistes catalanes amb accés obert": PreservationService.RACO,
}

# Cache for preservation service lookups
_preservation_cache: dict[str, Optional[PreservationService]] = {}


def normalize_preservation_service(
    service: Optional[str],
) -> Optional[PreservationService]:
    """
    Normalize preservation service name to PreservationService enum.

    Handles:
    - Case variations: "lockss" -> PreservationService.LOCKSS
    - Common variations: "PKP Preservation Network" -> PreservationService.PKP_PN
    - Unknown services: returns None (only enum values are valid)

    Args:
        service: Preservation service name

    Returns:
        PreservationService enum value or None if not recognized
    """
    if not service:
        return None

    service = str(service).strip()
    if not service:
        return None

    # Check cache first
    cache_key = service.lower()
    if cache_key in _preservation_cache:
        return _preservation_cache[cache_key]

    # Look up canonical name
    service_lower = service.lower().strip()

    # Check exact mapping first
    if service_lower in _PRESERVATION_SERVICE_MAPPINGS:
        result = _PRESERVATION_SERVICE_MAPPINGS[service_lower]
    else:
        # Check for partial matches using word boundaries, preferring longer matches
        result = partial_match(service_lower, _PRESERVATION_SERVICE_MAPPINGS)

    _preservation_cache[cache_key] = result
    return result
