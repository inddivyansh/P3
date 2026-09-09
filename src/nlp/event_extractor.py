"""
Structured Event Extractor
===========================

Extracts structured defence, security, and geopolitical events from article text:
    - Event Type (Military Exercise, Border Incident, Missile Test, Diplomatic Summit,
                  Defence Procurement, Counter-Terrorism Operation, etc.)
    - Key Actors involved
    - Target / Counterparty
    - Locations
    - Date / Timeframe
    - Equipment involved
    - Strategic significance

Uses rule-based pattern matching and keyword heuristics, with optional
Gemini refinement for high-threat or complex events.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

EVENT_PATTERNS: dict[str, list[str]] = {
    "Military Exercise": [
        r"\b(?:joint|bilateral|multilateral|naval|air|army|tri-service)\s+exercise\b",
        r"\bexercise\s+(?:yudh abhyas|malabar|varuna|garuda|indradhanush|sampriti|mitra shakti|shakti|dustlik|kazind|surya kiran|nomadic elephant)\b",
        r"\bmilitary drill\b",
        r"\bwar games?\b",
        r"\bfield training exercise\b",
    ],
    "Border Incident": [
        r"\b(?:border|lac|loc)\s+(?:clash|skirmish|standoff|face-off|transgression|incursion|friction)\b",
        r"\bceasefire violation\b",
        r"\bcross-border (?:firing|shelling)\b",
        r"\bunprovoked firing\b",
    ],
    "Counter-Terrorism Operation": [
        r"\b(?:encounter|anti-terror|cordon and search|combing)\s+operation\b",
        r"\bterrorists?\s+(?:neutralized|killed|apprehended|arrested)\b",
        r"\bgunfight broke out\b",
        r"\binfiltration bid (?:foiled|thwarted)\b",
    ],
    "Missile / Weapon Test": [
        r"\b(?:successful|flight)\s+test(?:ed|-fired)?\s+(?:of\s+)?(?:missile|torpedo|rocket|weapon system)\b",
        r"\btest-fired from\b",
        r"\buser trial (?:of|conducted)\b",
        r"\bflight-tested from (?:chandipur|abdul kalam island|itr|pokhran)\b",
    ],
    "Defence Procurement / Contract": [
        r"\b(?:dac|defence acquisition council|cabinet committee on security|ccs)\s+(?:approved|cleared)\b",
        r"\b(?:contract|deal|procurement|agreement|mou)\s+(?:signed|worth|valued at|inked)\b",
        r"\bacquisition of\s+(?:fighter|aircraft|missile|tank|drone|submarine|vessel|radar)\b",
        r"\bmake in india defence\b",
        r"\bindigenous development\b",
    ],
    "Diplomatic Meeting / Summit": [
        r"\b(?:bilateral|2\+2|quad|brics|sco|g20|summit|dialogue|talks)\s+(?:meeting|held|concluded)\b",
        r"\bforeign minister(?:s)?\s+meet(?:ing)?\b",
        r"\bdefence minister(?:s)?\s+meet(?:ing)?\b",
        r"\bdelegation level talks\b",
    ],
    "Troop / Asset Deployment": [
        r"\b(?:troops|forces|squadron|battalion|warship|submarine|jets)\s+(?:deployed|stationed|inducted|commissioned)\b",
        r"\bcommissioning of\s+ins\b",
        r"\binduction of\b",
    ],
    "Strategic Policy Announcement": [
        r"\b(?:national security|defence|foreign)\s+policy\s+(?:announced|unveiled|revised)\b",
        r"\bdefence budget (?:increased|allocated|presented)\b",
        r"\bstrategic partnership agreement\b",
    ],
}


def extract_events(text: str, title: str = "", metadata: dict | None = None) -> list[dict[str, Any]]:
    """
    Extract structured events from an article.

    Returns:
        List of event dictionaries:
        [{
            "event_type": "Military Exercise",
            "matched_phrases": ["bilateral exercise", "Malabar"],
            "locations": ["Visakhapatnam"],
            "actors": ["Indian Navy", "US Navy"],
            "equipment": ["INS Vikrant"],
        }]
    """
    combined_text = f"{title}\n{text}"
    events = []

    for event_type, patterns in EVENT_PATTERNS.items():
        matched_phrases = []
        for pattern in patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            if matches:
                matched_phrases.extend(matches)

        if matched_phrases:
            event_obj = {
                "event_type": event_type,
                "matched_phrases": list(set(matched_phrases))[:3],
            }

            if metadata:
                if metadata.get("locations"):
                    event_obj["locations"] = metadata["locations"][:3]
                elif metadata.get("states") or metadata.get("cities"):
                    event_obj["locations"] = (metadata.get("cities", []) + metadata.get("states", []))[:3]

                if metadata.get("organizations"):
                    event_obj["actors"] = metadata["organizations"][:3]
                elif metadata.get("people"):
                    event_obj["actors"] = metadata["people"][:3]

                if metadata.get("equipment"):
                    event_obj["equipment"] = metadata["equipment"][:3]

            events.append(event_obj)

    return events


def run_event_extraction(article: dict[str, Any]) -> dict[str, Any]:
    """
    Run event extraction on a single article dictionary and update the 'events' key.
    """
    text = article.get("article_text") or article.get("summary") or ""
    title = article.get("title", "")

    metadata = {
        "states": article.get("states", []),
        "cities": article.get("cities", []),
        "organizations": article.get("organizations", []),
        "people": article.get("people", []),
        "equipment": article.get("equipment", []),
    }

    events = extract_events(text, title, metadata)
    article["events"] = events
    return article
