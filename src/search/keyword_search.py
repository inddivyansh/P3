"""
Keyword Search using SQLite FTS5
==================================

Provides fast full-text keyword search across:
    - title
    - ai_summary
    - article_text
    - people, organizations
    - countries, states, cities
    - topics, keywords, tags

Uses SQLite FTS5 virtual table created in database.py.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_FILE = PROJECT_ROOT / "data" / "database" / "news_pipeline.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


STOPWORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "what", "where", "when", "who", "which", "how", "why", "show", "me", "tell",
    "about", "current", "situation", "status", "news", "articles", "happening",
    "this", "that", "these", "those", "and", "or", "not", "please", "some",
    "updates", "update", "latest", "recent", "report", "reports", "today",
    "yesterday", "live", "highlights", "summary", "information", "details",
    "brief", "article", "regarding", "find", "get", "give", "overview",
}


def _extract_query_tokens(query: str) -> list[str]:
    """Extract and normalize meaningful tokens from query string."""
    import re
    from src.nlp.indian_geography import LOCATION_ALIASES

    tokens = re.findall(r"[a-zA-Z0-9]+", query)
    meaningful = []
    for t in tokens:
        t_low = t.lower()
        if len(t_low) >= 2 and t_low not in STOPWORDS:
            norm = LOCATION_ALIASES.get(t_low, t_low).lower()
            if norm not in meaningful:
                meaningful.append(norm)
    return meaningful or [t.lower() for t in tokens if len(t) >= 2] or [query.strip().lower()]


def _prepare_fts_query(query: str, use_and: bool = True) -> str:
    """
    Prepare an FTS5-compatible query from user input.
    Cleans special characters, removes stopwords, and escapes terms to prevent syntax errors.
    """
    meaningful = _extract_query_tokens(query)
    if not meaningful:
        return ""

    if use_and and len(meaningful) > 1:
        return " AND ".join(f'"{t}"' for t in meaningful)
    return " OR ".join(f'"{t}"' for t in meaningful)


def keyword_search(
    query: str,
    limit: int = 30,
    filters: dict | None = None,
) -> list[dict[str, Any]]:
    """
    Search articles using FTS5 full-text search with precision fallback.
    """
    if not query or not query.strip():
        return []

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='articles_fts'"
        )

        if not cursor.fetchone():
            return _like_search(conn, query, limit, filters)

        where_clauses, params = _build_filter_clauses(filters)
        where_sql = f"AND {' AND '.join(where_clauses)}" if where_clauses else ""

        tokens = _extract_query_tokens(query)

        # 1. Try high-precision AND matching first if multiple tokens
        if len(tokens) > 1:
            fts_query_and = _prepare_fts_query(query, use_and=True)
            sql_and = f"""
                SELECT a.*, fts.rank
                FROM articles_fts fts
                JOIN articles a ON fts.article_id = a.article_id
                WHERE articles_fts MATCH ?
                {where_sql}
                ORDER BY fts.rank
                LIMIT ?
            """
            cursor.execute(sql_and, [fts_query_and] + params + [limit])
            and_rows = [dict(row) for row in cursor.fetchall()]
            if and_rows:
                return and_rows

        # 2. Fallback to ranked OR matching
        fts_query_or = _prepare_fts_query(query, use_and=False)
        sql_or = f"""
            SELECT a.*, fts.rank
            FROM articles_fts fts
            JOIN articles a ON fts.article_id = a.article_id
            WHERE articles_fts MATCH ?
            {where_sql}
            ORDER BY fts.rank
            LIMIT ?
        """
        cursor.execute(sql_or, [fts_query_or] + params + [limit])
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    except Exception as e:
        logger.error("FTS search error: %s", e)
        return _like_search(conn, query, limit, filters)

    finally:
        conn.close()


def _build_filter_clauses(
    filters: dict | None,
) -> tuple[list[str], list[Any]]:
    """Build SQL WHERE clauses from filter dict."""

    if not filters:
        return [], []

    clauses = []
    params = []

    if threat_level := filters.get("threat_level"):
        clauses.append("a.threat_level = ?")
        params.append(threat_level.upper())

    if monitoring := filters.get("army_monitoring_needed"):
        clauses.append("a.army_monitoring_needed = ?")
        params.append(monitoring.upper())

    if sentiment := filters.get("sentiment"):
        clauses.append("a.sentiment = ?")
        params.append(sentiment)

    if article_type := filters.get("article_type"):
        clauses.append("a.article_type LIKE ?")
        params.append(f"%{article_type}%")

    if published_after := filters.get("published_after"):
        clauses.append("a.published_at >= ?")
        params.append(published_after)

    if published_before := filters.get("published_before"):
        clauses.append("a.published_at <= ?")
        params.append(published_before)

    if state := filters.get("state"):
        clauses.append("a.states LIKE ?")
        params.append(f"%{state}%")

    if city := filters.get("city"):
        clauses.append("a.cities LIKE ?")
        params.append(f"%{city}%")

    if country := filters.get("country"):
        clauses.append("a.countries LIKE ?")
        params.append(f"%{country}%")

    return clauses, params


def _like_search(
    conn: sqlite3.Connection,
    query: str,
    limit: int,
    filters: dict | None,
) -> list[dict[str, Any]]:
    """
    Fallback search using SQL LIKE with AND logic across meaningful tokens.
    """
    meaningful = _extract_query_tokens(query)
    where_clauses, params = _build_filter_clauses(filters)

    # Require all meaningful tokens (AND)
    token_conditions = []
    base_params = []
    for token in meaningful[:5]:
        term = f"%{token}%"
        token_conditions.append("(title LIKE ? OR ai_summary LIKE ? OR article_text LIKE ? OR topics LIKE ? OR keywords LIKE ?)")
        base_params.extend([term, term, term, term, term])

    if not token_conditions:
        term = f"%{query.strip()}%"
        token_conditions.append("(title LIKE ? OR ai_summary LIKE ? OR article_text LIKE ?)")
        base_params.extend([term, term, term])

    sql_where = " AND ".join(token_conditions)
    if where_clauses:
        sql_where = f"({sql_where}) AND " + " AND ".join(where_clauses)

    all_params = base_params + params + [limit]

    sql = f"""
        SELECT *
        FROM articles a
        WHERE {sql_where}
        ORDER BY published_at DESC
        LIMIT ?
    """

    cursor = conn.cursor()
    cursor.execute(sql, all_params)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def search_by_location(
    location: str,
    limit: int = 30,
    filters: dict | None = None,
) -> list[dict[str, Any]]:
    """
    Search articles by location (state, city, country, or locality).
    """

    conn = get_connection()

    try:

        where_clauses, params = _build_filter_clauses(filters)

        location_condition = """
            (countries LIKE ? OR states LIKE ? OR cities LIKE ?
             OR localities LIKE ? OR districts LIKE ? OR regions LIKE ?)
        """

        loc_params = [f"%{location}%"] * 6

        all_conditions = [location_condition] + where_clauses
        all_params = loc_params + params + [limit]

        sql = f"""
            SELECT *
            FROM articles
            WHERE {' AND '.join(all_conditions)}
            ORDER BY
                CASE threat_level
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MODERATE' THEN 3
                    ELSE 4
                END,
                published_at DESC
            LIMIT ?
        """

        cursor = conn.cursor()
        cursor.execute(sql, all_params)

        return [dict(row) for row in cursor.fetchall()]

    finally:
        conn.close()


def search_by_entity(
    entity: str,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """
    Search articles by named entity (person, organization, country, equipment).
    """

    conn = get_connection()

    try:

        search_term = f"%{entity}%"

        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM articles
            WHERE people LIKE ?
               OR organizations LIKE ?
               OR countries LIKE ?
               OR equipment LIKE ?
               OR title LIKE ?
            ORDER BY published_at DESC
            LIMIT ?
            """,
            (search_term,) * 5 + (limit,),
        )

        return [dict(row) for row in cursor.fetchall()]

    finally:
        conn.close()
