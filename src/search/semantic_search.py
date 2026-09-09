"""
Semantic Search using ChromaDB + Sentence Transformers
=======================================================

Provides semantic similarity search for natural-language queries.

At ingestion time:
    - Generate embedding from title + ai_summary
    - Store in ChromaDB with article metadata

At query time:
    - Embed the user query
    - Retrieve top-K semantically similar articles
    - Return article IDs for merging with keyword results

Falls back gracefully if ChromaDB is not installed.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHROMA_DIR = PROJECT_ROOT / "data" / "vectorstore"
COLLECTION_NAME = "defence_intelligence_articles"

# Embedding model (already in requirements via sentence-transformers)
EMBED_MODEL = "all-MiniLM-L6-v2"

_chroma_client = None
_collection = None
_embed_model = None


# ============================================================================
# INITIALIZATION
# ============================================================================

def _get_chroma_collection():
    """Get or create ChromaDB collection."""

    global _chroma_client, _collection

    if _collection is not None:
        return _collection

    try:
        import chromadb
        from chromadb.config import Settings

        CHROMA_DIR.mkdir(parents=True, exist_ok=True)

        _chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
        )

        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(
            "ChromaDB collection ready: %s (%d items)",
            COLLECTION_NAME,
            _collection.count(),
        )

    except ImportError:
        logger.warning(
            "ChromaDB not installed. Run: pip install chromadb\n"
            "Semantic search will be disabled."
        )
        _collection = None

    except Exception as e:
        logger.error("ChromaDB initialization error: %s", e)
        _collection = None

    return _collection


def _get_embed_model():
    """Get sentence-transformers embedding model."""

    global _embed_model

    if _embed_model is not None:
        return _embed_model

    try:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer(EMBED_MODEL)
        logger.info("Embedding model loaded: %s", EMBED_MODEL)
    except Exception as e:
        logger.error("Failed to load embedding model: %s", e)
        _embed_model = None

    return _embed_model


def _build_document_text(article: dict) -> str:
    """
    Build the text to embed for an article.
    Uses title + ai_summary for compact but rich representation.
    """
    parts = []

    if title := article.get("title"):
        parts.append(title)

    if summary := article.get("ai_summary") or article.get("summary"):
        parts.append(summary[:500])

    if topics := article.get("topics"):
        if isinstance(topics, list):
            parts.append(" ".join(topics))
        elif isinstance(topics, str):
            parts.append(topics)

    return " ".join(parts)[:1000]


# ============================================================================
# INDEX ARTICLE
# ============================================================================

def index_article(article: dict[str, Any]) -> bool:
    """
    Add a single article to the ChromaDB vector store.

    Returns:
        True if indexed successfully, False otherwise.
    """

    collection = _get_chroma_collection()
    embed_model = _get_embed_model()

    if collection is None or embed_model is None:
        return False

    article_id = article.get("article_id")
    if not article_id:
        return False

    doc_text = _build_document_text(article)
    if not doc_text.strip():
        return False

    try:

        # Check if already indexed
        existing = collection.get(ids=[article_id])
        if existing["ids"]:
            return True  # Already indexed

        embedding = embed_model.encode(doc_text).tolist()

        # Build metadata (must be simple types for Chroma)
        metadata = {
            "title": (article.get("title") or "")[:200],
            "source": article.get("source") or "",
            "published_at": article.get("published_at") or "",
            "threat_level": article.get("threat_level") or "UNCLEAR",
            "article_type": article.get("article_type") or "",
            "sentiment": article.get("sentiment") or "",
            "army_monitoring_needed": article.get("army_monitoring_needed") or "UNCLEAR",
            "states": json.dumps(article.get("states") or [])[:200],
            "countries": json.dumps(article.get("countries") or [])[:200],
        }

        collection.add(
            ids=[article_id],
            embeddings=[embedding],
            documents=[doc_text],
            metadatas=[metadata],
        )

        return True

    except Exception as e:

        logger.error(
            "Failed to index article '%s': %s",
            article_id,
            e,
        )

        return False


def batch_index_articles(articles: list[dict[str, Any]], batch_size: int = 64) -> int:
    """
    Index multiple articles into ChromaDB in efficient batches.

    Returns:
        Number of articles indexed.
    """
    collection = _get_chroma_collection()
    embed_model = _get_embed_model()

    if collection is None or embed_model is None:
        logger.warning("ChromaDB not available. Skipping semantic indexing.")
        return 0

    total_indexed = 0

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        ids = []
        docs = []
        metadatas = []

        for a in batch:
            aid = a.get("article_id") or a.get("id")
            if not aid:
                continue
            doc_text = _build_document_text(a)
            if not doc_text.strip():
                continue

            metadata = {
                "title": (a.get("title") or "")[:200],
                "source": a.get("source") or "",
                "published_at": a.get("published_at") or "",
                "threat_level": a.get("threat_level") or "UNCLEAR",
                "article_type": a.get("article_type") or "",
                "sentiment": a.get("sentiment") or "",
                "army_monitoring_needed": a.get("army_monitoring_needed") or "UNCLEAR",
                "states": json.dumps(a.get("states") or []) if isinstance(a.get("states"), list) else (a.get("states") or "")[:200],
                "countries": json.dumps(a.get("countries") or []) if isinstance(a.get("countries"), list) else (a.get("countries") or "")[:200],
            }

            ids.append(str(aid))
            docs.append(doc_text)
            metadatas.append(metadata)

        if ids:
            try:
                embeddings = embed_model.encode(docs).tolist()
                collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=docs,
                    metadatas=metadatas,
                )
                total_indexed += len(ids)
            except Exception as e:
                logger.error("Batch index error: %s", e)

    logger.info("Semantic index: %d articles indexed/updated in ChromaDB.", total_indexed)
    return total_indexed


def index_all_articles_from_db() -> int:
    """Load all articles from SQLite and index into ChromaDB."""
    import sqlite3
    db_file = PROJECT_ROOT / "data" / "database" / "news_pipeline.db"
    if not db_file.exists():
        return 0
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM articles").fetchall()
        articles = [dict(r) for r in rows]
        conn.close()
        return batch_index_articles(articles)
    except Exception as e:
        logger.error("Failed to index articles from DB: %s", e)
        return 0


# ============================================================================
# SEMANTIC SEARCH
# ============================================================================

def semantic_search(
    query: str,
    limit: int = 15,
    filters: dict | None = None,
    min_similarity: float = 0.35,
) -> list[dict[str, Any]]:
    """
    Perform semantic similarity search with relevance cutoff.

    Args:
        query: Natural language query.
        limit: Max results.
        filters: Optional Chroma metadata filters.
        min_similarity: Minimum cosine similarity threshold (default 0.35).

    Returns:
        List of dicts with keys: article_id, title, source, score.
    """
    collection = _get_chroma_collection()
    embed_model = _get_embed_model()

    if collection is None or embed_model is None:
        logger.warning("Semantic search not available.")
        return []

    if not query or not query.strip():
        return []

    try:
        query_embedding = embed_model.encode(query).tolist()

        # Build Chroma where clause
        where = _build_chroma_where(filters)

        available_count = collection.count()
        if available_count == 0:
            return []

        query_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": min(limit * 2, available_count),
        }

        if where:
            query_kwargs["where"] = where

        results = collection.query(**query_kwargs)

        articles = []
        if results and results["ids"] and len(results["ids"]) > 0:
            for i, article_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i]
                distance = results["distances"][0][i]

                # Cosine distance to similarity
                similarity = 1.0 - distance

                if similarity < min_similarity:
                    continue

                articles.append({
                    "article_id": article_id,
                    "title": meta.get("title", ""),
                    "source": meta.get("source", ""),
                    "threat_level": meta.get("threat_level", ""),
                    "published_at": meta.get("published_at", ""),
                    "semantic_score": round(similarity, 4),
                })

                if len(articles) >= limit:
                    break

        return articles

    except Exception as e:
        logger.error("Semantic search error: %s", e)
        return []


def _build_chroma_where(filters: dict | None) -> dict | None:
    """Build ChromaDB where clause from filter dict."""

    if not filters:
        return None

    conditions = []

    if threat_level := filters.get("threat_level"):
        conditions.append({"threat_level": {"$eq": threat_level.upper()}})

    if monitoring := filters.get("army_monitoring_needed"):
        conditions.append({"army_monitoring_needed": {"$eq": monitoring.upper()}})

    if article_type := filters.get("article_type"):
        conditions.append({"article_type": {"$eq": article_type}})

    if not conditions:
        return None

    if len(conditions) == 1:
        return conditions[0]

    return {"$and": conditions}


# ============================================================================
# INDEX STATUS
# ============================================================================

def get_index_stats() -> dict:
    """Return ChromaDB index statistics."""

    collection = _get_chroma_collection()

    if collection is None:
        return {"available": False, "count": 0}

    return {
        "available": True,
        "count": collection.count(),
        "collection": COLLECTION_NAME,
    }
