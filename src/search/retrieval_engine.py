"""
Unified Retrieval Engine
========================

Combines:
1. SQLite FTS5 Full-Text Keyword Search
2. Location & Geographic Hierarchy Search
3. ChromaDB Semantic Vector Search
4. Reciprocal Rank Fusion & Score-based Re-ranking

Provides a unified querying interface for both the FastAPI endpoints
and the RAG Chatbot engine.
"""

import logging
from typing import Any
from src.search.keyword_search import keyword_search, search_by_location, search_by_entity
from src.search.semantic_search import semantic_search

logger = logging.getLogger(__name__)


class RetrievalEngine:
    """Unified multi-modal retrieval engine for news intelligence."""

    def __init__(self):
        pass

    def retrieve(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        enable_semantic: bool = True,
        enable_fts: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Execute hybrid search combining FTS5 and vector similarity.
        """
        results_map: dict[str, dict[str, Any]] = {}
        scores_map: dict[str, float] = {}

        # 1. FTS5 Search
        if enable_fts and query.strip():
            try:
                fts_results = keyword_search(query, limit=limit * 2, filters=filters)
                for rank, article in enumerate(fts_results):
                    aid = article.get("article_id")
                    if not aid:
                        continue
                    results_map[aid] = article
                    # RRF style scoring
                    scores_map[aid] = scores_map.get(aid, 0.0) + (1.0 / (60 + rank))
            except Exception as e:
                logger.warning("FTS search error in retrieval engine: %s", e)

        # 2. Semantic Search
        if enable_semantic and query.strip():
            try:
                sem_results = semantic_search(query, limit=limit, filters=filters)
                for rank, sem_item in enumerate(sem_results):
                    aid = sem_item.get("article_id")
                    if not aid:
                        continue
                    # If not in results_map from FTS, we will retain what we have
                    if aid not in results_map:
                        results_map[aid] = sem_item
                    sim = sem_item.get("semantic_score", 0.5)
                    scores_map[aid] = scores_map.get(aid, 0.0) + (sim * 1.5) + (1.0 / (60 + rank))
            except Exception as e:
                logger.warning("Semantic search error in retrieval engine: %s", e)

        # 3. Threat level weighting boost
        threat_weights = {
            "CRITICAL": 0.5,
            "HIGH": 0.3,
            "MODERATE": 0.1,
            "LOW": 0.0,
            "UNCLEAR": 0.0,
        }

        for aid, article in results_map.items():
            tl = (article.get("threat_level") or "UNCLEAR").upper()
            scores_map[aid] = scores_map.get(aid, 0.0) + threat_weights.get(tl, 0.0)

        # Sort articles by fused score
        ranked_ids = sorted(scores_map.keys(), key=lambda k: scores_map[k], reverse=True)
        ranked_articles = [results_map[aid] for aid in ranked_ids[:limit]]

        return ranked_articles


# Global singleton instance
retrieval_engine = RetrievalEngine()
