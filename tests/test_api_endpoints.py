"""
FastAPI Intelligence Endpoint Tests
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "version" in data
    assert "disclaimer" in data


def test_kpis_endpoint():
    response = client.get("/intelligence/kpis")
    assert response.status_code == 200
    data = response.json()
    assert "total_articles" in data
    assert "threat_distribution" in data
    assert "disclaimer" in data


def test_intelligence_articles_endpoint():
    response = client.get("/intelligence/articles?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "articles" in data
    assert "total" in data


def test_threat_dashboard_endpoint():
    response = client.get("/intelligence/threats?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "threat_distribution" in data
    assert "articles" in data


def test_monitoring_queue_endpoint():
    response = client.get("/intelligence/monitoring?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "articles" in data
    assert "disclaimer" in data


def test_geographic_intelligence_endpoint():
    response = client.get("/intelligence/locations")
    assert response.status_code == 200
    data = response.json()
    assert "states" in data
    assert "cities" in data
    assert "countries" in data


def test_entity_analysis_endpoint():
    response = client.get("/intelligence/entities?entity_type=organizations&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "entities" in data
    assert data["entity_type"] == "organizations"


def test_topic_trends_endpoint():
    response = client.get("/intelligence/trends?days=30")
    assert response.status_code == 200
    data = response.json()
    assert "top_categories" in data
    assert "daily_totals" in data


def test_sources_endpoint():
    response = client.get("/intelligence/sources")
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert "total_sources" in data


def test_live_map_endpoint():
    response = client.get("/intelligence/map")
    assert response.status_code == 200
    data = response.json()
    assert "locations" in data
    assert "total_locations" in data
