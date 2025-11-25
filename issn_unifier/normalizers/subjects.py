"""Subject taxonomy mapping and normalization."""

from typing import Optional

# Map DOAJ LCC categories to OpenAlex taxonomy
# Format: LCC Category -> (OpenAlex Domain, OpenAlex Field)
#
# Notes:
# - Domain mapping is reliable (4 broad categories)
# - Field mapping is approximate (some LCC categories don't map cleanly)
# - Field is None when LCC category is too broad or mixed to pick one field
# - "Science" requires subcategory parsing (see _map_science_subcategory)
LCC_TO_OPENALEX: dict[str, tuple[str | None, str | None]] = {
    "Medicine": ("Health Sciences", "Medicine"),
    "Science": (
        None,
        None,
    ),  # Requires subcategory parsing - see _map_science_subcategory
    "Technology": ("Physical Sciences", "Engineering"),
    "Agriculture": ("Life Sciences", "Agricultural and Biological Sciences"),
    "Social Sciences": ("Social Sciences", "Social Sciences"),
    "Education": ("Social Sciences", "Social Sciences"),  # Education is a subfield
    "Law": ("Social Sciences", "Social Sciences"),  # Law is a subfield
    "Philosophy. Psychology. Religion": (
        "Social Sciences",
        None,
    ),  # Mixed: can't pick one field
    "Language and Literature": ("Social Sciences", "Arts and Humanities"),
    "Fine Arts": ("Social Sciences", "Arts and Humanities"),
    "Geography. Anthropology. Recreation": (
        "Social Sciences",
        "Social Sciences",
    ),  # Anthropology → Social Sciences
    "History (General) and history of Europe": (
        "Social Sciences",
        "Arts and Humanities",
    ),
    "Political science": ("Social Sciences", "Social Sciences"),
    "Military Science": ("Social Sciences", "Social Sciences"),
    "Naval Science": (
        "Social Sciences",
        "Social Sciences",
    ),  # Consistent with Military Science
    "Bibliography. Library science. Information resources": (
        "Social Sciences",
        "Social Sciences",
    ),
    "General Works": (None, None),
    "Auxiliary sciences of history": ("Social Sciences", "Arts and Humanities"),
    "History America": ("Social Sciences", "Arts and Humanities"),
    "Music and books on Music": ("Social Sciences", "Arts and Humanities"),
}

# Subcategories of "Science" that belong to Life Sciences domain
_LIFE_SCIENCE_SUBCATEGORIES = {
    "biology",
    "botany",
    "zoology",
    "microbiology",
    "physiology",
    "natural history",
    "ecology",
    "genetics",
    "cytology",
    "anatomy",
}


def _map_science_subcategory(subcategory: Optional[str]) -> tuple[str, str | None]:
    """
    Map "Science" subcategory to appropriate OpenAlex domain/field.

    Args:
        subcategory: The subcategory after "Science:" (e.g., "Biology (General)")

    Returns:
        Tuple of (domain, field)
    """
    if not subcategory:
        return ("Physical Sciences", None)

    sub_lower = subcategory.lower()

    # Check if it's a life science
    for life_sci in _LIFE_SCIENCE_SUBCATEGORIES:
        if life_sci in sub_lower:
            return ("Life Sciences", "Agricultural and Biological Sciences")

    # Check for specific physical sciences
    if "mathematic" in sub_lower:
        return ("Physical Sciences", "Mathematics")
    if "physics" in sub_lower:
        return ("Physical Sciences", "Physics and Astronomy")
    if "chemistry" in sub_lower:
        return ("Physical Sciences", "Chemistry")
    if "geology" in sub_lower or "earth" in sub_lower:
        return ("Physical Sciences", "Earth and Planetary Sciences")
    if "astronomy" in sub_lower:
        return ("Physical Sciences", "Physics and Astronomy")

    # Default for other Science subcategories
    return ("Physical Sciences", None)


def map_lcc_to_domain(lcc_category: str, subcategory: Optional[str] = None) -> Optional[str]:
    """
    Map LCC top-level category to OpenAlex domain.

    Args:
        lcc_category: Library of Congress Classification top-level category
        subcategory: Optional subcategory for refined mapping (used for "Science")

    Returns:
        OpenAlex domain name or None if not mapped
    """
    # Special handling for "Science" - requires subcategory parsing
    if lcc_category == "Science":
        domain, _ = _map_science_subcategory(subcategory)
        return domain

    mapping = LCC_TO_OPENALEX.get(lcc_category)
    return mapping[0] if mapping else None


def map_lcc_to_field(lcc_category: str, subcategory: Optional[str] = None) -> Optional[str]:
    """
    Map LCC top-level category to OpenAlex field.

    Args:
        lcc_category: Library of Congress Classification top-level category
        subcategory: Optional subcategory for refined mapping (used for "Science")

    Returns:
        OpenAlex field name or None if not mapped
    """
    # Special handling for "Science" - requires subcategory parsing
    if lcc_category == "Science":
        _, field = _map_science_subcategory(subcategory)
        return field

    mapping = LCC_TO_OPENALEX.get(lcc_category)
    return mapping[1] if mapping else None
