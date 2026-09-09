"""
src/ingestion/p2_framework/__init__.py
----------------------------------------
D-P2-21 Multi-Source Data Ingestion Framework
— integrated as an extensible sub-package of the Intelligence Platform.

Public API
----------
from src.ingestion.p2_framework import (
    IngestionEngine,
    UnifiedRecord,
    SourceType,
    DeadLetterQueue,
    SQLiteStore,
    ConnectorFactory,
    ConnectorRegistry,
    register_connector,
    load_sources_config,
    GDELTConnector,
    RSSConnector,
    WorldBankConnector,
    SQLConnector,
    CSVConnector,
    JSONConnector,
    RESTConnector,
    BaseConnector,
)
"""

from src.ingestion.p2_framework.schema import SourceType, UnifiedRecord
from src.ingestion.p2_framework.engine import IngestionEngine
from src.ingestion.p2_framework.error_handling.dlq import DeadLetterQueue
from src.ingestion.p2_framework.storage.sqlite_store import SQLiteStore
from src.ingestion.p2_framework.factory import (
    ConnectorFactory,
    ConnectorRegistry,
    register_connector,
)
from src.ingestion.p2_framework.p2_config import load_sources_config
from src.ingestion.p2_framework.connectors import (
    BaseConnector,
    CSVConnector,
    JSONConnector,
    RESTConnector,
    SQLConnector,
    GDELTConnector,
    RSSConnector,
    WorldBankConnector,
)

__all__ = [
    "IngestionEngine",
    "UnifiedRecord",
    "SourceType",
    "DeadLetterQueue",
    "SQLiteStore",
    "ConnectorFactory",
    "ConnectorRegistry",
    "register_connector",
    "load_sources_config",
    "BaseConnector",
    "CSVConnector",
    "JSONConnector",
    "RESTConnector",
    "SQLConnector",
    "GDELTConnector",
    "RSSConnector",
    "WorldBankConnector",
]
