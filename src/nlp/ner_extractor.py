"""
Named Entity Recognition (NER) Extractor
==========================================

Extracts named entities from article text:
    - People (leaders, ministers, military officials, diplomats)
    - Organizations (Indian Army, Navy, IAF, MoD, NATO, UN, companies)
    - Countries
    - Military equipment (aircraft, missiles, ships, drones)

Uses spaCy for NER with a domain-specific entity list for
defence/military/geopolitical entities that spaCy may miss.

Falls back gracefully if spaCy models are not installed.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# DOMAIN-SPECIFIC ENTITY LISTS
# ============================================================================

KNOWN_ORGANIZATIONS: set[str] = {
    # Indian Armed Forces
    "Indian Army", "Indian Navy", "Indian Air Force", "IAF",
    "Coast Guard", "Indian Coast Guard",
    "CRPF", "BSF", "SSB", "ITBP", "CISF", "NSG", "SPG",
    "Para SF", "MARCOS", "Garud Commando Force",

    # Indian Government / Defence
    "Ministry of Defence", "MoD", "Ministry of External Affairs", "MEA",
    "Ministry of Home Affairs", "MHA",
    "DRDO", "HAL", "BEL", "BDL", "MDL", "GRSE", "BEML",
    "Hindustan Aeronautics Limited", "Bharat Electronics Limited",
    "Ordnance Factory Board", "OFB", "ISRO", "NSCS",
    "National Security Council", "RAW", "IB", "Intelligence Bureau",

    # International Organizations
    "NATO", "United Nations", "UN", "UN Security Council", "UNSC",
    "European Union", "EU", "SCO", "BRICS", "Quad", "AUKUS",
    "ASEAN", "SAARC",

    # Foreign Armed Forces
    "PLA", "People's Liberation Army", "US Army", "US Navy",
    "US Air Force", "USAF", "Pentagon", "CIA", "FBI",
    "Pakistan Army", "ISI", "MI6",

    # Defence Companies
    "Boeing", "Lockheed Martin", "Raytheon", "Northrop Grumman",
    "General Dynamics", "BAE Systems", "Dassault Aviation",
    "Thales", "MBDA", "Saab", "Leonardo", "Airbus",
    "Rosoboronexport", "Rostec", "Rafael", "Elbit Systems",
    "Israel Aerospace Industries", "IAI",

    # Think Tanks
    "ORF", "Observer Research Foundation", "IDSA", "VIF", "Gateway House",
    "IISS", "RAND Corporation", "Brookings Institution", "SIPRI",

    # Media / Official
    "PIB", "Press Information Bureau", "ANI",
}


KNOWN_EQUIPMENT: dict[str, list[str]] = {
    "fighter_aircraft": [
        "Rafale", "Tejas", "MiG-21", "MiG-29", "Su-30MKI", "Su-30",
        "Mirage 2000", "Jaguar", "F-16", "F-35", "F-18", "F/A-18",
        "J-20", "J-10", "JF-17", "HAL Tejas", "AMCA",
        "Advanced Medium Combat Aircraft",
    ],
    "missiles": [
        "BrahMos", "Agni", "Agni-I", "Agni-II", "Agni-III", "Agni-IV",
        "Agni-V", "Agni-VI", "Prithvi", "Aakash", "Nag", "Helina",
        "MRSAM", "LRSAM", "Barak", "S-400", "Patriot", "THAAD",
        "HIMARS", "ATACMS", "Tomahawk", "Spike", "Javelin",
        "PJ-10", "YJ-12",
    ],
    "naval_vessels": [
        "INS Vikrant", "INS Vikramaditya", "INS Arihant", "INS Arighat",
        "INS Vishal", "INS Chennai", "INS Kolkata", "INS Delhi",
        "INS Kamorta", "INS Kiltan", "INS Kadmatt",
        "aircraft carrier", "destroyer", "frigate", "corvette",
        "submarine", "nuclear submarine", "SSBN", "SSN",
    ],
    "drones_uav": [
        "MQ-9", "MQ-9B", "Predator", "Global Hawk",
        "Heron", "Searcher", "Rustom", "TAPAS", "Ghatak",
        "Wing Loong", "MALE UAV", "UCAV",
        "Drone", "UAV", "UAS", "Kamikaze drone", "Loitering munition",
    ],
    "tanks_armour": [
        "Arjun", "Arjun MBT", "T-72", "T-90", "T-90S", "BMP-2",
        "FICV", "M1 Abrams", "Leopard 2", "Type 99",
    ],
    "systems": [
        "S-400", "S-300", "Patriot", "Iron Dome", "Arrow",
        "NASAMS", "SPYDER", "Akash", "DRDO MRSAM",
    ],
}

# Flatten equipment to a set for quick lookup
ALL_EQUIPMENT: set[str] = set()
for category_items in KNOWN_EQUIPMENT.values():
    ALL_EQUIPMENT.update(category_items)


KNOWN_COUNTRIES: set[str] = {
    "India", "China", "Pakistan", "Russia", "United States", "USA",
    "France", "Israel", "Japan", "Australia", "United Kingdom", "UK",
    "Germany", "Italy", "Spain", "South Korea", "North Korea",
    "Iran", "Saudi Arabia", "UAE", "Turkey",
    "Bangladesh", "Nepal", "Sri Lanka", "Maldives", "Bhutan",
    "Myanmar", "Afghanistan",
    "Indonesia", "Vietnam", "Philippines", "Thailand", "Malaysia",
    "Singapore", "Taiwan",
}


# ============================================================================
# SPACY NER (with graceful fallback)
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
            logger.info("Loaded spaCy model: en_core_web_lg")
        except Exception:
            try:
                _nlp = spacy.load("en_core_web_sm")
                _spacy_available = True
                logger.info("Loaded spaCy model: en_core_web_sm (en_core_web_lg not found)")
            except Exception:
                logger.warning(
                    "spaCy model not loaded. Falling back to rule-based NER."
                )
                _spacy_available = False
    except BaseException as e:
        logger.warning(
            "spaCy unavailable (%s). Falling back to rule-based NER.", e
        )
        _spacy_available = False

    return _nlp


# ============================================================================
# ENTITY EXTRACTION
# ============================================================================

def extract_entities(text: str) -> dict[str, list[str]]:
    """
    Extract named entities from article text.

    Returns:
        {
            "people": [...],
            "organizations": [...],
            "countries": [...],
            "equipment": [...],
        }
    """

    if not text or len(text.strip()) < 50:
        return {
            "people": [],
            "organizations": [],
            "countries": [],
            "equipment": [],
        }

    # Truncate very long texts for efficiency
    text_for_ner = text[:8000]

    people = set()
    organizations = set()
    countries = set()

    # --- spaCy NER ---
    nlp = _load_spacy()

    if _spacy_available and nlp:

        doc = nlp(text_for_ner)

        for ent in doc.ents:

            name = ent.text.strip()

            if len(name) < 2:
                continue

            if ent.label_ in ("PERSON",):
                # Filter out very generic names
                if len(name.split()) >= 2:
                    people.add(name)

            elif ent.label_ in ("ORG",):
                organizations.add(name)

            elif ent.label_ in ("GPE", "LOC"):
                # Countries will be filtered later; locations in location_extractor
                if name in KNOWN_COUNTRIES:
                    countries.add(name)

    # --- Rule-based entity augmentation ---
    _augment_organizations(text, organizations)
    _augment_countries(text, countries)
    equipment = _extract_equipment(text)

    # Clean results
    people_list = _clean_entity_list(people)
    org_list = _clean_entity_list(organizations)
    country_list = sorted(countries)
    equipment_list = sorted(equipment)

    return {
        "people": people_list,
        "organizations": org_list,
        "countries": country_list,
        "equipment": equipment_list,
    }


def _augment_organizations(text: str, organizations: set) -> None:
    """Add known defence organizations found in text."""
    for org in KNOWN_ORGANIZATIONS:
        if len(org) <= 4:
            # Case-sensitive word boundary match for short acronyms (UN, IB, RAW, BSF, IAF, MoD, MEA, ANI, HAL, BEL, EU)
            pattern = r'\b' + re.escape(org) + r'\b'
            if re.search(pattern, text):
                organizations.add(org)
        else:
            pattern = r'\b' + re.escape(org.lower()) + r'\b'
            if re.search(pattern, text.lower()):
                organizations.add(org)


def _augment_countries(text: str, countries: set) -> None:
    """Add known countries found in text."""
    for country in KNOWN_COUNTRIES:
        # Use word boundary matching to avoid partial matches
        pattern = r'\b' + re.escape(country) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            countries.add(country)


def _extract_equipment(text: str) -> set[str]:
    """Extract military equipment mentions from text."""
    found = set()
    for item in ALL_EQUIPMENT:
        if len(item) <= 4:
            pattern = r'\b' + re.escape(item) + r'\b'
            if re.search(pattern, text):
                found.add(item)
        else:
            pattern = r'\b' + re.escape(item.lower()) + r'\b'
            if re.search(pattern, text.lower()):
                found.add(item)
    return found


def _clean_entity_list(entities: set) -> list[str]:
    """Clean, deduplicate, and sort an entity set."""
    cleaned = []
    for entity in entities:
        entity = entity.strip()
        # Remove very short or all-numeric entries
        if len(entity) < 2:
            continue
        if entity.isdigit():
            continue
        cleaned.append(entity)
    return sorted(set(cleaned))


# ============================================================================
# TOPIC / KEYWORD EXTRACTION
# ============================================================================

DEFENCE_KEYWORDS: list[str] = [
    "military", "defence", "defense", "army", "navy", "air force",
    "weapon", "missile", "aircraft", "fighter", "submarine",
    "border", "security", "terrorism", "insurgency", "counterterrorism",
    "strategic", "geopolitical", "diplomatic", "foreign policy",
    "LAC", "LOC", "line of control", "line of actual control",
    "exercise", "drill", "deployment", "patrol", "airstrike",
    "intelligence", "surveillance", "reconnaissance",
    "nuclear", "ballistic", "satellite", "cyber",
    "procurement", "contract", "deal", "acquisition",
    "general", "admiral", "marshal", "colonel", "brigadier",
    "minister", "ministry", "government",
]


def extract_keywords(text: str, title: str = "") -> list[str]:
    """
    Extract relevant keywords and topics from text.

    Uses a combination of:
    1. Known defence keyword matching
    2. TF-IDF-like frequency (simple implementation)
    """

    combined = f"{title} {text}"
    combined_lower = combined.lower()
    found_keywords = []

    for keyword in DEFENCE_KEYWORDS:
        if len(keyword) <= 4:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, combined):
                found_keywords.append(keyword)
        else:
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            if re.search(pattern, combined_lower):
                found_keywords.append(keyword)

    return found_keywords[:20]  # Limit to top 20


def extract_topics(entities: dict, keywords: list, text: str = "") -> list[str]:
    """
    Derive topic labels from entities and keywords.
    """

    topics = set()
    text_lower = text.lower()

    # Equipment-based topics
    if entities.get("equipment"):
        equip_text = " ".join(entities["equipment"]).lower()
        if any(f in equip_text for f in ["rafale", "tejas", "mig", "su-30", "amca"]):
            topics.add("Fighter Aircraft")
        if any(m in equip_text for m in ["brahmos", "agni", "prithvi", "aakash", "s-400"]):
            topics.add("Missiles & Air Defence")
        if any(n in equip_text for n in ["ins", "submarine", "aircraft carrier", "destroyer"]):
            topics.add("Naval Assets")
        if any(d in equip_text for d in ["drone", "uav", "predator", "heron"]):
            topics.add("Drones & UAVs")

    # Keyword-based topics
    if "border" in keywords or "lac" in keywords or "loc" in keywords:
        topics.add("Border Security")
    if "terrorism" in keywords or "insurgency" in keywords:
        topics.add("Terrorism & Insurgency")
    if "cyber" in keywords:
        topics.add("Cybersecurity")
    if "nuclear" in keywords:
        topics.add("Nuclear Affairs")
    if "exercise" in keywords or "drill" in keywords:
        topics.add("Military Exercises")
    if "procurement" in keywords or "contract" in keywords or "deal" in keywords:
        topics.add("Defence Procurement")
    if "diplomatic" in keywords or "foreign policy" in keywords:
        topics.add("Diplomatic Affairs")
    if "satellite" in keywords:
        topics.add("Space & Defence")

    # Country-based topics
    countries = entities.get("countries", [])
    if "China" in countries:
        topics.add("India-China Relations")
    if "Pakistan" in countries:
        topics.add("India-Pakistan Relations")
    if "Russia" in countries:
        topics.add("India-Russia Relations")
    if "United States" in countries or "USA" in countries:
        topics.add("India-US Relations")

    return sorted(topics)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def run_ner_extraction(article: dict[str, Any]) -> dict[str, Any]:
    """
    Run full NER and keyword extraction on a single article.

    Args:
        article: Article dict with 'article_text', 'title', 'summary' keys.

    Returns:
        Updated article dict with NER fields populated.
    """

    text = article.get("article_text") or article.get("summary") or ""
    title = article.get("title", "")

    # NER
    entities = extract_entities(f"{title}\n{text}")

    # Keywords
    keywords = extract_keywords(text, title)

    # Topics
    topics = extract_topics(entities, keywords, text)

    article["people"] = entities["people"]
    article["organizations"] = entities["organizations"]
    article["countries"] = entities["countries"]
    article["equipment"] = entities["equipment"]
    article["keywords"] = keywords
    article["topics"] = topics

    return article
