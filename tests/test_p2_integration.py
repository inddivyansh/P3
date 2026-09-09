"""
tests/test_p2_integration.py
------------------------------
Integration tests for the D-P2-21 Multi-Source Ingestion Framework
as merged into the Intelligence Platform.

Tests verify:
1. All P2 sub-packages import correctly.
2. UnifiedRecord schema works end-to-end.
3. IngestionEngine can be instantiated with mocked connectors.
4. _unified_record_to_article() correctly converts all four source types.
5. P2 config paths resolve correctly within the project root.
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ──────────────────────────────────────────────────────────────────────────────
# Import Smoke Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestP2Imports:
    """Verify that all P2 sub-packages import without errors."""

    def test_schema_imports(self):
        from src.ingestion.p2_framework.schema import SourceType, UnifiedRecord
        assert SourceType.CSV.value == "CSV"
        assert SourceType.JSON.value == "JSON"
        assert SourceType.REST.value == "REST"
        assert SourceType.SQL.value == "SQL"

    def test_exceptions_import(self):
        from src.ingestion.p2_framework.error_handling.exceptions import (
            IngestionBaseError, FatalIngestionError, ValidationIngestionError,
            StructuralIngestionError, TransientIngestionError,
        )
        assert issubclass(FatalIngestionError, IngestionBaseError)

    def test_connector_imports(self):
        from src.ingestion.p2_framework.connectors import (
            BaseConnector, CSVConnector, JSONConnector, RESTConnector,
            SQLConnector, GDELTConnector, RSSConnector, WorldBankConnector,
        )

    def test_engine_import(self):
        from src.ingestion.p2_framework.engine import IngestionEngine

    def test_dlq_import(self):
        from src.ingestion.p2_framework.error_handling.dlq import DeadLetterQueue, DLQEntry

    def test_sqlite_store_import(self):
        from src.ingestion.p2_framework.storage.sqlite_store import SQLiteStore

    def test_top_level_package_import(self):
        from src.ingestion.p2_framework import (
            IngestionEngine, UnifiedRecord, SourceType,
            DeadLetterQueue, SQLiteStore,
            GDELTConnector, RSSConnector, WorldBankConnector, SQLConnector,
        )

    def test_p2_config_import(self):
        from src.ingestion.p2_framework.p2_config import (
            GDELT_QUERY_TOPICS, RSS_FEED_URLS, WORLD_BANK_COUNTRIES,
            WORLD_BANK_INDICATOR, WORLD_BANK_YEARS,
            OUTPUT_DB_URI, DLQ_FILE_PATH, INTEL_DB_PATH,
        )
        assert isinstance(GDELT_QUERY_TOPICS, list)
        assert len(GDELT_QUERY_TOPICS) > 0
        assert "Indian Army" in GDELT_QUERY_TOPICS


# ──────────────────────────────────────────────────────────────────────────────
# Config Path Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestP2Config:
    """Verify that p2_config paths resolve to a sensible project structure."""

    def test_project_root_resolves(self):
        from src.ingestion.p2_framework.p2_config import P2_PROJECT_ROOT
        # Should be the project root (4 levels up from p2_config.py)
        assert P2_PROJECT_ROOT.is_dir()
        assert (P2_PROJECT_ROOT / "src").is_dir()

    def test_output_db_path_in_project(self):
        from src.ingestion.p2_framework.p2_config import OUTPUT_DB_PATH, P2_PROJECT_ROOT
        assert str(P2_PROJECT_ROOT) in str(OUTPUT_DB_PATH)

    def test_dlq_path_in_project(self):
        from src.ingestion.p2_framework.p2_config import DLQ_FILE_PATH, P2_PROJECT_ROOT
        assert str(P2_PROJECT_ROOT) in str(DLQ_FILE_PATH)


# ──────────────────────────────────────────────────────────────────────────────
# UnifiedRecord Schema Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestUnifiedRecord:
    """Test the canonical UnifiedRecord Pydantic model."""

    def test_basic_construction(self):
        from src.ingestion.p2_framework.schema import UnifiedRecord, SourceType
        record = UnifiedRecord(
            source_type=SourceType.JSON,
            source_name="test_feed",
            entity_type="defence_news",
            entity_id="article-001",
            payload={"title": "Test article", "link": "https://example.com/1"},
        )
        assert record.source_type == SourceType.JSON
        assert record.entity_id == "article-001"
        assert record.checksum != ""   # Auto-computed

    def test_checksum_determinism(self):
        """Same payload must always produce the same checksum."""
        from src.ingestion.p2_framework.schema import UnifiedRecord, SourceType
        payload = {"title": "Stable", "value": 42}
        r1 = UnifiedRecord(source_type=SourceType.CSV, source_name="s", entity_type="e", entity_id="1", payload=payload)
        r2 = UnifiedRecord(source_type=SourceType.CSV, source_name="s", entity_type="e", entity_id="1", payload=payload)
        assert r1.checksum == r2.checksum

    def test_to_storage_dict(self):
        from src.ingestion.p2_framework.schema import UnifiedRecord, SourceType
        record = UnifiedRecord(
            source_type=SourceType.REST,
            source_name="api.worldbank.org",
            entity_type="military_expenditure",
            entity_id="IN-2023",
            payload={"country": "India", "year": "2023", "pct_gdp": 2.4},
        )
        d = record.to_storage_dict()
        assert "record_id" in d
        assert d["source_type"] == "REST"
        assert isinstance(d["payload"], str)  # JSON string

    def test_empty_payload_raises(self):
        from src.ingestion.p2_framework.schema import UnifiedRecord, SourceType
        with pytest.raises(Exception):
            UnifiedRecord(
                source_type=SourceType.SQL,
                source_name="db",
                entity_type="ref",
                entity_id="1",
                payload={},  # Empty — should fail
            )


# ──────────────────────────────────────────────────────────────────────────────
# Article Conversion Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestUnifiedRecordToArticle:
    """Test _unified_record_to_article() converter for all four source types."""

    def _make_record(self, source_type: str, entity_type: str, payload: dict) -> dict:
        """Helper to build a storage dict mimicking SQLiteStore.query_records() output."""
        return {
            "record_id":    "test-record-id",
            "source_type":  source_type,
            "source_name":  "test-source",
            "entity_type":  entity_type,
            "entity_id":    "test-entity-1",
            "ingested_at":  "2026-09-09T05:00:00+00:00",
            "payload":      payload,
            "checksum":     "abc123",
            "schema_version": "2.0",
        }

    def test_json_rss_record_conversion(self):
        from src.ingestion.feed_reader import _unified_record_to_article
        record = self._make_record("JSON", "defence_news", {
            "title": "India deploys additional troops to LAC",
            "link": "https://idrw.org/article-123",
            "summary": "Indian Army deploys 5000 additional troops...",
            "source_feed": "idrw.org",
            "published": "2026-09-08T12:00:00+00:00",
        })
        article = _unified_record_to_article(record)
        assert article is not None
        assert article["title"] == "India deploys additional troops to LAC"
        assert article["url"] == "https://idrw.org/article-123"
        assert article["source"] == "idrw.org"
        assert article["needs_extraction"] is True
        assert article["p2_source_type"] == "JSON"

    def test_csv_gdelt_record_conversion(self):
        from src.ingestion.feed_reader import _unified_record_to_article
        record = self._make_record("CSV", "geopolitical_event", {
            "url": "https://timesofindia.com/article-gdelt",
            "title": "China PLA increases presence along LAC",
            "domain": "timesofindia.com",
            "sourcecountry": "India",
            "seendate": "20260909T120000Z",
            "matched_topics": ["China PLA", "LAC border India"],
        })
        article = _unified_record_to_article(record)
        assert article is not None
        assert article["url"] == "https://timesofindia.com/article-gdelt"
        assert article["source"] == "timesofindia.com"
        assert article["source_category_hint"] == "Geopolitics"
        assert article["needs_extraction"] is True
        assert article["gdelt_topics"] == ["China PLA", "LAC border India"]

    def test_rest_worldbank_record_conversion(self):
        from src.ingestion.feed_reader import _unified_record_to_article
        record = self._make_record("REST", "military_expenditure", {
            "id": "CN-2023",
            "country_name": "China",
            "country_code": "CN",
            "year": "2023",
            "military_pct_gdp": 1.7,
            "military_usd_current": 293000000000,
            "threat_context": "HIGH",
            "data_source": "World Bank / SIPRI",
            "indicator_name": "Military expenditure (% of GDP)",
        })
        article = _unified_record_to_article(record)
        assert article is not None
        assert "China" in article["title"]
        assert "2023" in article["title"]
        assert "1.7% of GDP" in article["title"]
        assert article["needs_extraction"] is False
        assert article["full_text"] is not None
        assert "China" in article["full_text"]
        assert article["worldbank_data"]["threat_context"] == "HIGH"

    def test_sql_reference_record_conversion(self):
        from src.ingestion.feed_reader import _unified_record_to_article
        record = self._make_record("SQL", "strategic_reference", {
            "id": "PK",
            "country_name": "Pakistan",
            "region": "South Asia",
            "threat_level": "HIGH",
            "alliance_status": "ADVERSARY",
            "nuclear_power": 1,
            "active_disputes": "LoC,Siachen,Sir Creek,Kashmir",
        })
        article = _unified_record_to_article(record)
        assert article is not None
        assert "Pakistan" in article["title"]
        assert article["needs_extraction"] is False
        assert article["threat_level"] == "HIGH"
        assert "South Asia" in article["title"]

    def test_json_record_without_url_returns_none(self):
        from src.ingestion.feed_reader import _unified_record_to_article
        record = self._make_record("JSON", "defence_news", {
            "title": "Article with no URL",
            "link": "",  # Empty URL
        })
        result = _unified_record_to_article(record)
        assert result is None

    def test_payload_as_json_string(self):
        """Storage dicts sometimes have payload as a JSON string rather than dict."""
        from src.ingestion.feed_reader import _unified_record_to_article
        payload_dict = {"link": "https://example.com/str-payload", "title": "Str payload test"}
        record = self._make_record("JSON", "defence_news", json.dumps(payload_dict))
        article = _unified_record_to_article(record)
        assert article is not None
        assert article["url"] == "https://example.com/str-payload"


# ──────────────────────────────────────────────────────────────────────────────
# IngestionEngine Mock Test
# ──────────────────────────────────────────────────────────────────────────────

class TestIngestionEngine:
    """Test IngestionEngine with a mock connector."""

    def _build_mock_connector(self, source_type_val="JSON", records=None):
        from src.ingestion.p2_framework.schema import SourceType

        mock = MagicMock()
        mock.source_name = "mock_connector"
        mock.entity_type = "test_entity"
        mock.entity_id_field = "id"
        mock.get_source_type.return_value = SourceType(source_type_val)

        _records = records or [{"id": "1", "title": "Test", "link": "https://example.com"}]

        def extract_gen():
            yield from _records

        mock.extract.return_value = extract_gen()
        return mock

    def test_engine_instantiation(self):
        from src.ingestion.p2_framework.engine import IngestionEngine
        engine = IngestionEngine(batch_size=10)
        assert engine is not None

    def test_engine_register_connector(self):
        from src.ingestion.p2_framework.engine import IngestionEngine
        engine = IngestionEngine(batch_size=10)
        mock_connector = self._build_mock_connector()
        engine.register_connector(mock_connector)
        # No exception = pass

    def test_engine_report_returns_string(self, tmp_path):
        """Engine.report() should return a formatted string."""
        from src.ingestion.p2_framework.engine import IngestionEngine
        from src.ingestion.p2_framework.storage.sqlite_store import SQLiteStore
        from src.ingestion.p2_framework.error_handling.dlq import DeadLetterQueue

        db_path = tmp_path / "test_store.sqlite"
        dlq_path = tmp_path / "test_dlq.json"
        store = SQLiteStore(db_uri=f"sqlite:///{db_path}")
        dlq = DeadLetterQueue(file_path=dlq_path)

        engine = IngestionEngine(storage=store, dlq=dlq, batch_size=10)

        mock = self._build_mock_connector(records=[
            {"id": "1", "title": "T1", "link": "https://a.com/1"},
            {"id": "2", "title": "T2", "link": "https://a.com/2"},
        ])
        engine.register_connector(mock)
        engine.run()

        report = engine.report()
        assert isinstance(report, str)
        assert "MULTI-SOURCE" in report or "SOURCE" in report
        store.close()


# ──────────────────────────────────────────────────────────────────────────────
# DeadLetterQueue Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestDeadLetterQueue:
    """Test DLQ read/write operations."""

    def test_push_and_read_all(self, tmp_path):
        from src.ingestion.p2_framework.error_handling.dlq import DeadLetterQueue

        dlq_file = tmp_path / "test_dlq.json"
        dlq = DeadLetterQueue(file_path=dlq_file)

        error = ValueError("Test error")
        entry = dlq.push(
            source_type="JSON",
            source_name="test_feed",
            raw_record={"id": "bad-record"},
            error=error,
        )
        assert entry is not None
        assert dlq.session_count() == 1

        entries = dlq.read_all()
        assert len(entries) == 1
        assert entries[0]["error_type"] == "ValueError"
        assert entries[0]["source_name"] == "test_feed"

    def test_empty_dlq_returns_empty_list(self, tmp_path):
        from src.ingestion.p2_framework.error_handling.dlq import DeadLetterQueue
        dlq = DeadLetterQueue(file_path=tmp_path / "empty_dlq.json")
        assert dlq.read_all() == []
        assert dlq.session_count() == 0


# ──────────────────────────────────────────────────────────────────────────────
# Declarative Config & Factory Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestDeclarativeSourcesConfig:
    """Test loading and validation of declarative sources.yaml."""

    def test_sources_yaml_exists_and_loads(self):
        from src.ingestion.p2_framework.p2_config import load_sources_config, SOURCES_CONFIG_FILE
        assert SOURCES_CONFIG_FILE.exists(), f"sources.yaml must exist at {SOURCES_CONFIG_FILE}"
        cfg = load_sources_config(SOURCES_CONFIG_FILE)
        assert "sources" in cfg
        assert "gdelt" in cfg["sources"]
        assert "worldbank" in cfg["sources"]
        assert "sql" in cfg["sources"]
        assert "rss" in cfg["sources"]

    def test_gdelt_config_parameters(self):
        from src.ingestion.p2_framework.p2_config import load_sources_config
        cfg = load_sources_config()
        gdelt = cfg["sources"]["gdelt"]
        assert gdelt["enabled"] is True
        assert gdelt["max_records"] == 250
        assert len(gdelt["query_topics"]) > 5
        assert "Indian Army" in gdelt["query_topics"]

    def test_worldbank_config_parameters(self):
        from src.ingestion.p2_framework.p2_config import load_sources_config
        cfg = load_sources_config()
        wb = cfg["sources"]["worldbank"]
        assert wb["enabled"] is True
        assert "IN" in wb["countries"]
        assert wb["years"] >= 10

    def test_storage_and_error_policy_config(self):
        from src.ingestion.p2_framework.p2_config import load_sources_config
        cfg = load_sources_config()
        assert "storage" in cfg
        assert "error_policy" in cfg
        assert cfg["storage"].get("batch_size", 100) > 0


class TestConnectorFactory:
    """Test dynamic ConnectorRegistry and ConnectorFactory."""

    def test_registered_types_include_all_builtins(self):
        from src.ingestion.p2_framework.factory import ConnectorFactory
        types = ConnectorFactory.get_registered_types()
        for expected in ("gdelt", "worldbank", "sql", "rss", "csv", "json", "rest"):
            assert expected in types

    def test_create_connector_by_type(self):
        from src.ingestion.p2_framework.factory import ConnectorFactory
        from src.ingestion.p2_framework.connectors.worldbank_connector import WorldBankConnector
        conn = ConnectorFactory.create_connector("worldbank", countries="IN;CN", years=5)
        assert isinstance(conn, WorldBankConnector)
        assert conn._countries == "IN;CN"
        assert conn._years == 5

    def test_build_all_from_config_dict(self):
        from src.ingestion.p2_framework.factory import ConnectorFactory
        config = {
            "sources": {
                "gdelt": {
                    "enabled": True,
                    "max_records": 100,
                    "query_topics": ["Indian Army"],
                },
                "worldbank": {
                    "enabled": True,
                    "countries": "IN;PK",
                    "years": 10,
                },
                "disabled_source": {
                    "enabled": False,
                    "source_type": "rss",
                },
            }
        }
        connectors = ConnectorFactory.build_all_from_config(config)
        assert len(connectors) == 2
        names = [c.__class__.__name__ for c in connectors]
        assert "GDELTConnector" in names
        assert "WorldBankConnector" in names

    def test_custom_connector_registration(self):
        from src.ingestion.p2_framework.factory import ConnectorFactory, register_connector
        from src.ingestion.p2_framework.connectors.base import BaseConnector
        from src.ingestion.p2_framework.schema import SourceType

        @register_connector("mock_custom")
        class MockCustomConnector(BaseConnector):
            def __init__(self, custom_param="default", **kwargs):
                super().__init__(source_name="mock", entity_type="test", entity_id_field="id")
                self.custom_param = custom_param

            def connect(self): self._connected = True
            def extract(self): yield {"id": "1", "val": self.custom_param}
            def disconnect(self): self._connected = False
            def get_source_type(self): return SourceType.REST

        assert "mock_custom" in ConnectorFactory.get_registered_types()
        instance = ConnectorFactory.create_connector("mock_custom", custom_param="activated")
        assert isinstance(instance, MockCustomConnector)
        assert instance.custom_param == "activated"


class TestEngineFromConfig:
    """Test IngestionEngine.from_config() initialization."""

    def test_engine_from_config_instantiation(self, tmp_path):
        from src.ingestion.p2_framework.engine import IngestionEngine
        from src.ingestion.p2_framework.storage.sqlite_store import SQLiteStore
        from src.ingestion.p2_framework.error_handling.dlq import DeadLetterQueue

        db_path = tmp_path / "cfg_store.sqlite"
        dlq_path = tmp_path / "cfg_dlq.json"
        store = SQLiteStore(db_uri=f"sqlite:///{db_path}")
        dlq = DeadLetterQueue(file_path=dlq_path)

        config = {
            "storage": {"batch_size": 50},
            "sources": {
                "worldbank": {"enabled": True, "countries": "IN", "years": 2},
            },
        }

        engine = IngestionEngine.from_config(
            config=config,
            storage=store,
            dlq=dlq,
        )
        assert engine._batch_size == 50
        assert len(engine._connectors) == 1
        store.close()


class TestIngestionAPIEndpoints:
    """Test FastAPI ingestion endpoints."""

    def test_get_ingestion_config_endpoint(self):
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)

        response = client.get("/api/ingestion/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "sources" in data
        assert "registered_types" in data
        assert "gdelt" in data["sources"]
        assert "worldbank" in data["sources"]

    def test_get_ingestion_sources_endpoint(self):
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)

        response = client.get("/api/ingestion/sources")
        assert response.status_code == 200
        data = response.json()
        assert "connectors" in data
        assert isinstance(data["connectors"], list)
        assert "total_records" in data


class TestCombinedIngestion:
    """Test run_combined_ingestion with Article dataclass instances."""

    def test_run_combined_ingestion_with_article_dataclasses(self, monkeypatch, tmp_path):
        from src.ingestion.feed_reader import run_combined_ingestion, Article
        import src.ingestion.feed_reader as fr

        dummy_article = Article(
            article_id="test-1",
            title="Test Article",
            url="https://example.com/test-1",
            source="Test Source",
            source_category_hint=None,
            published_at="2026-09-09T00:00:00Z",
            summary="A test summary",
            fetched_at="2026-09-09T00:00:00Z",
        )

        monkeypatch.setattr(fr, "run_ingestion", lambda: [dummy_article])
        monkeypatch.setattr(fr, "RAW_DATA_DIR", tmp_path)

        result = run_combined_ingestion(skip_p2=True)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["url"] == "https://example.com/test-1"
        assert result[0]["title"] == "Test Article"

