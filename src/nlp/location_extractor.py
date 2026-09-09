"""
Granular Location Extractor
============================

Extracts and normalizes geographic entities from article text with
full Indian administrative hierarchy:

    Country → State/UT → Region → District → City/Town → Locality

Features:
    - spaCy GPE/LOC entity extraction
    - Indian geography knowledge base (states, cities, districts)
    - Strategic location recognition (border passes, military bases)
    - Location normalization (Bombay → Mumbai, Madras → Chennai)
    - Hierarchy inference (city → state → region → country)
    - Location type classification
    - Multi-location support per article
"""

import logging
import re
from typing import Any

from src.nlp.indian_geography import (
    CITY_TO_STATE,
    INDIAN_STATES,
    STRATEGIC_LOCATIONS,
    STATE_TO_REGION,
    KNOWN_COUNTRIES,
    normalize_location,
    get_state_for_city,
    get_region_for_state,
    get_strategic_info,
    is_indian_state,
)

logger = logging.getLogger(__name__)


# ============================================================================
# LOCATION TYPE CLASSIFICATION
# ============================================================================

LOCATION_TYPE_KEYWORDS: dict[str, list[str]] = {
    "border_area": [
        "border", "loc", "lac", "line of control", "line of actual control",
        "frontier", "boundary", "fencing",
    ],
    "military_installation": [
        "military base", "army base", "air force base", "naval base",
        "cantonment", "barracks", "garrison", "airfield", "airstrip",
        "military academy", "NDA", "IMA",
    ],
    "strategic_infrastructure": [
        "highway", "road", "bridge", "dam", "port", "harbour", "harbor",
        "pipeline", "power plant", "nuclear plant", "radar station",
        "satellite station",
    ],
    "conflict_zone": [
        "encounter", "operation", "exchange of fire", "gunfight",
        "bomb blast", "attack", "infiltration",
    ],
    "diplomatic_location": [
        "embassy", "consulate", "high commission", "summit venue",
        "bilateral meeting",
    ],
}


# ============================================================================
# SPACY NLP (shared instance via lazy import)
# ============================================================================

_nlp = None
_spacy_available = False
_spacy_attempted = False


def _load_spacy():
    """Load spaCy model lazily."""
    global _nlp, _spacy_available, _spacy_attempted

    if _spacy_attempted:
        return _nlp

    _spacy_attempted = True
    try:
        import spacy
        try:
            _nlp = spacy.load("en_core_web_lg")
            _spacy_available = True
        except Exception:
            try:
                _nlp = spacy.load("en_core_web_sm")
                _spacy_available = True
            except Exception:
                _spacy_available = False
    except BaseException as e:
        logger.warning(
            "spaCy unavailable (%s). Falling back to rule-based location extraction.", e
        )
        _spacy_available = False

    return _nlp


# ============================================================================
# MAIN LOCATION EXTRACTION
# ============================================================================

def extract_locations(text: str, title: str = "") -> dict[str, Any]:
    """
    Extract and structure location information from article text.

    Returns:
        {
            "countries": ["India", "China"],
            "states": ["Ladakh"],
            "regions": ["Western Himalayas"],
            "districts": [],
            "cities": ["Leh"],
            "localities": ["Galwan Valley"],
            "location_type": "border_area",
            "location_confidence": 0.85,
        }
    """

    combined_text = f"{title}\n{text}"

    if not combined_text.strip():
        return _empty_location_result()

    countries: set[str] = set()
    states: set[str] = set()
    cities: set[str] = set()
    localities: set[str] = set()
    districts: set[str] = set()
    regions: set[str] = set()

    # --- spaCy extraction ---
    nlp = _load_spacy()
    if _spacy_available and nlp:
        doc = nlp(combined_text[:8000])
        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC"):
                _classify_location(
                    ent.text.strip(),
                    countries, states, cities, districts,
                    localities, regions,
                )

    # --- Rule-based augmentation ---
    _rule_based_extraction(
        combined_text,
        countries, states, cities, districts, localities, regions,
    )

    # --- Hierarchy inference ---
    _infer_hierarchy(cities, states, regions)
    _infer_hierarchy_from_states(states, regions)

    # --- Location type ---
    location_type = _classify_location_type(combined_text, localities, states, cities)

    # --- Confidence ---
    confidence = _compute_confidence(countries, states, cities, localities)

    return {
        "countries": sorted(countries),
        "states": sorted(states),
        "regions": sorted(regions),
        "districts": sorted(districts),
        "cities": sorted(cities),
        "localities": sorted(localities),
        "location_type": location_type,
        "location_confidence": confidence,
    }


def _classify_location(
    location: str,
    countries: set,
    states: set,
    cities: set,
    districts: set,
    localities: set,
    regions: set,
) -> None:
    """Classify a single location string into the correct bucket."""

    # Normalize
    normalized = normalize_location(location)
    if not normalized or len(normalized) < 2:
        return

    # Check strategic locations
    strategic = get_strategic_info(normalized)
    if strategic:
        localities.add(normalized)
        if strategic.get("state"):
            states.add(strategic["state"])
        if strategic.get("country"):
            countries.add(strategic["country"])
        return

    # Check if it's a known country
    if normalized in KNOWN_COUNTRIES:
        # Special case: "India" is always the primary country
        countries.add(normalized)
        return

    # Check Indian states
    if is_indian_state(normalized):
        states.add(normalized)
        countries.add("India")
        return

    # Check known cities
    if normalized in CITY_TO_STATE:
        cities.add(normalized)
        state = CITY_TO_STATE[normalized]
        states.add(state)
        countries.add("India")
        return


def _rule_based_extraction(
    text: str,
    countries: set, states: set, cities: set,
    districts: set, localities: set, regions: set,
) -> None:
    """
    Rule-based location extraction using known geography lists.
    Faster and more reliable than spaCy for known Indian locations.
    """

    text_lower = text.lower()

    # Check all known countries
    for country in KNOWN_COUNTRIES:
        if re.search(r'\b' + re.escape(country.lower()) + r'\b', text_lower):
            countries.add(country)

    # Check all Indian states
    for state in INDIAN_STATES:
        if re.search(r'\b' + re.escape(state.lower()) + r'\b', text_lower):
            states.add(state)
            countries.add("India")

    # Check all known cities
    for city, state in CITY_TO_STATE.items():
        if re.search(r'\b' + re.escape(city.lower()) + r'\b', text_lower):
            cities.add(city)
            states.add(state)
            countries.add("India")

    # Check strategic locations
    for location, info in STRATEGIC_LOCATIONS.items():
        loc_lower = location.lower()
        matched = False
        if loc_lower == "uri":
            # Avoid matching words containing uri like jurisdiction or during
            if re.search(r'\bUri\b', text) or re.search(r'\buri\s+(?:sector|attack|base|encounter|infiltration|loc)\b', text_lower):
                matched = True
        elif loc_lower == "hot springs":
            if re.search(r'\bhot\s+springs?\s+(?:sector|friction|lac|ladakh|patrol)\b', text_lower):
                matched = True
        else:
            if re.search(r'\b' + re.escape(loc_lower) + r'\b', text_lower):
                matched = True

        if matched:
            localities.add(location)
            if info.get("state"):
                states.add(info["state"])
                countries.add("India")
            if info.get("country"):
                countries.add(info["country"])

    # Check regional terms
    region_patterns = {
        "Northeast India": ["northeast india", "north east india", "northeastern india"],
        "Western Himalayas": ["western himalayas", "ladakh region"],
        "Eastern Himalayas": ["eastern himalayas", "eastern himalaya"],
        "Line of Actual Control": ["line of actual control", r"\blac\b"],
        "Line of Control": ["line of control", r"\bloc\b"],
        "Indo-Pacific": ["indo-pacific"],
        "Indian Ocean Region": ["indian ocean region", r"\bior\b"],
    }

    for region, patterns in region_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                regions.add(region)
                break


def _infer_hierarchy(cities: set, states: set, regions: set) -> None:
    """Infer state from city if state not already present."""
    for city in list(cities):
        state = get_state_for_city(city)
        if state:
            states.add(state)


def _infer_hierarchy_from_states(states: set, regions: set) -> None:
    """Infer region from state."""
    for state in list(states):
        region = get_region_for_state(state)
        if region:
            regions.add(region)


def _classify_location_type(
    text: str,
    localities: set,
    states: set,
    cities: set,
) -> str:
    """
    Classify the dominant location type for this article.
    """

    text_lower = text.lower()

    # Check strategic locations
    for locality in localities:
        info = get_strategic_info(locality)
        if info and info.get("type"):
            return info["type"]

    # Keyword-based classification
    for loc_type, keywords in LOCATION_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return loc_type

    # State-based classification
    border_states = {"Ladakh", "Jammu & Kashmir", "Arunachal Pradesh", "Sikkim",
                     "Punjab", "Rajasthan"}
    if states.intersection(border_states):
        return "border_area"

    if cities:
        return "city"

    if states:
        return "state"

    return "unknown"


def _compute_confidence(
    countries: set, states: set, cities: set, localities: set,
) -> float:
    """
    Compute a confidence score for location extraction.
    """
    score = 0.0

    if countries:
        score += 0.3
    if states:
        score += 0.3
    if cities:
        score += 0.2
    if localities:
        score += 0.2

    return min(score, 1.0)


def _empty_location_result() -> dict:
    return {
        "countries": [],
        "states": [],
        "regions": [],
        "districts": [],
        "cities": [],
        "localities": [],
        "location_type": "unknown",
        "location_confidence": 0.0,
    }


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def run_location_extraction(article: dict[str, Any]) -> dict[str, Any]:
    """
    Run location extraction on a single article.

    Args:
        article: Article dict.

    Returns:
        Updated article dict with location fields populated.
    """

    text = article.get("article_text") or article.get("summary") or ""
    title = article.get("title", "")

    location_data = extract_locations(text, title)

    article.update({
        "countries": location_data["countries"],
        "states": location_data["states"],
        "regions": location_data["regions"],
        "districts": location_data["districts"],
        "cities": location_data["cities"],
        "localities": location_data["localities"],
        "location_type": location_data["location_type"],
        "location_confidence": location_data["location_confidence"],
    })

    return article
