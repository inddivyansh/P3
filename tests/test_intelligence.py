"""
Unit Tests for Defence Intelligence Platform
"""

import pytest
from src.nlp.indian_geography import (
    normalize_location,
    get_state_for_city,
    get_strategic_info,
    is_indian_state,
)
from src.nlp.ner_extractor import extract_entities, extract_keywords
from src.nlp.location_extractor import extract_locations
from src.nlp.event_extractor import extract_events
from src.nlp.threat_analyzer import DEFAULT_THREAT_RESULT
from src.storage.database import get_connection, initialize_database, get_kpi_counts
from src.search.keyword_search import keyword_search


def test_location_normalization():
    assert normalize_location("bombay") == "Mumbai"
    assert normalize_location("madras") == "Chennai"
    assert normalize_location("poona") == "Pune"
    assert normalize_location("loc") == "Line of Control"


def test_city_to_state_mapping():
    assert get_state_for_city("Pune") == "Maharashtra"
    assert get_state_for_city("Leh") == "Ladakh"
    assert get_state_for_city("Tawang") == "Arunachal Pradesh"
    assert is_indian_state("Ladakh")
    assert is_indian_state("Sikkim")


def test_strategic_locations():
    galwan = get_strategic_info("Galwan Valley")
    assert galwan is not None
    assert galwan["state"] == "Ladakh"

    pokhran = get_strategic_info("Pokhran")
    assert pokhran is not None
    assert pokhran["type"] == "military_test_range"


def test_location_extractor():
    text = "Indian Army troops conducted a patrol near Galwan Valley in Ladakh."
    locations = extract_locations(text, "Border Patrol Update")
    assert "India" in locations["countries"]
    assert "Ladakh" in locations["states"]
    assert "Galwan Valley" in locations["localities"]


def test_ner_extractor():
    text = "Defence Minister visited DRDO headquarters to review the Rafale fighter aircraft and BrahMos missile readiness."
    entities = extract_entities(text)
    assert "DRDO" in entities["organizations"]
    assert "Rafale" in entities["equipment"]
    assert "BrahMos" in entities["equipment"]


def test_event_extractor():
    text = "The Indian Navy and US Navy commenced a bilateral naval exercise in the Indian Ocean."
    events = extract_events(text, "Naval Exercise Begins", {"organizations": ["Indian Navy", "US Navy"]})
    assert len(events) > 0
    assert any(e["event_type"] == "Military Exercise" for e in events)


def test_threat_schema_defaults():
    assert "threat_level" in DEFAULT_THREAT_RESULT
    assert "potential_threat" in DEFAULT_THREAT_RESULT
    assert "army_monitoring_needed" in DEFAULT_THREAT_RESULT
    assert "escalation_risk" in DEFAULT_THREAT_RESULT
    assert DEFAULT_THREAT_RESULT["threat_level"] == "UNCLEAR"


def test_database_and_kpis():
    initialize_database()
    kpis = get_kpi_counts()
    assert "total_articles" in kpis
    assert "threat_distribution" in kpis
    assert isinstance(kpis["total_articles"], int)


def test_fts5_search():
    results = keyword_search("India", limit=5)
    assert isinstance(results, list)
