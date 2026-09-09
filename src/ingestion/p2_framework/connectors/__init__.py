# src/ingestion/p2_framework/connectors/__init__.py
"""
Source connectors sub-package — Defence Intelligence Edition.

Connector → Source Type → Intelligence Domain
─────────────────────────────────────────────
GDELTConnector      CSV   Geopolitical events (GDELT DOC 2.0 API)
RSSConnector        JSON  Live defence news (6 RSS feeds)
WorldBankConnector  REST  Military expenditure for India + neighbours
SQLConnector        SQL   Strategic intelligence reference database

All connectors inherit from BaseConnector.
"""

from src.ingestion.p2_framework.connectors.base import BaseConnector
from src.ingestion.p2_framework.connectors.csv_connector import CSVConnector
from src.ingestion.p2_framework.connectors.json_connector import JSONConnector
from src.ingestion.p2_framework.connectors.rest_connector import RESTConnector
from src.ingestion.p2_framework.connectors.sql_connector import SQLConnector
from src.ingestion.p2_framework.connectors.gdelt_connector import GDELTConnector
from src.ingestion.p2_framework.connectors.rss_connector import RSSConnector
from src.ingestion.p2_framework.connectors.worldbank_connector import WorldBankConnector

__all__ = [
    "BaseConnector",
    "CSVConnector",
    "JSONConnector",
    "RESTConnector",
    "SQLConnector",
    "GDELTConnector",
    "RSSConnector",
    "WorldBankConnector",
]
