"""
Intelligence Data Store
=======================

High-level interface for querying and persisting intelligence-enriched articles,
analytical flags, structured events, and knowledge items.
"""

import logging
from typing import Any
from src.storage.database import (
    get_connection,
    initialize_database,
    upsert_article,
    store_articles,
    get_articles_by_threat_level,
    get_monitoring_queue,
    get_human_review_queue,
    get_kpi_counts,
    get_geographic_activity,
    get_unprocessed_articles,
    mark_nlp_processed,
    mark_ai_processed,
)

logger = logging.getLogger(__name__)


class IntelligenceStore:
    """Intelligence store wrapper over SQLite."""

    def __init__(self):
        initialize_database()

    def get_kpi_summary(self) -> dict[str, Any]:
        return get_kpi_counts()

    def get_monitoring_alerts(self, limit: int = 100) -> list[dict[str, Any]]:
        return get_monitoring_queue(limit=limit)

    def get_review_items(self, limit: int = 100) -> list[dict[str, Any]]:
        return get_human_review_queue(limit=limit)

    def get_threats_by_level(self, level: str, limit: int = 50) -> list[dict[str, Any]]:
        return get_articles_by_threat_level(level, limit=limit)

    def save_enriched_articles(self, articles: list[dict[str, Any]]) -> None:
        store_articles(articles)


intelligence_store = IntelligenceStore()
