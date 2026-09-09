"""
Natural Language Query Engine (RAG Chatbot)
============================================

Processes natural language queries against the news database.

Architecture:
    User Query
        ↓
    Intent Detection (Gemini)
        ↓
    Filter Construction (SQL)
        ↓
    Keyword Search (FTS5)
        ↓
    Semantic Search (ChromaDB)
        ↓
    Merged & Re-ranked Results
        ↓
    Context Construction
        ↓
    Gemini Analysis & Synthesis
        ↓
    Structured Response
        ↓
    Supporting Articles

Supports queries like:
    - "What is happening in Manipur?"
    - "Show high-threat articles near India-China border"
    - "Show negative articles about NDA Pune"
    - "What defence developments happened this week?"
    - "Compare India-China and India-Pakistan developments"
"""

import json
import logging
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_FILE = PROJECT_ROOT / "data" / "database" / "news_pipeline.db"

GEMINI_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("LLM_MODEL", "gemini-flash-latest")

_gemini_client = None


def _get_gemini():
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client
    if not GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        candidates = [GEMINI_MODEL, "gemini-flash-latest", "gemini-pro-latest", "gemini-2.5-flash"]
        for model_name in candidates:
            try:
                _gemini_client = genai.GenerativeModel(model_name)
                break
            except Exception:
                continue
    except ImportError:
        pass
    return _gemini_client


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================================
# INTENT DETECTION
# ============================================================================

INTENT_SYSTEM = """You are a query intent analyzer for an Indian Army Defence Intelligence Platform.

Analyze the user's question and extract:
1. Main topic/subject
2. Specific locations mentioned (Indian states, cities, border areas)
3. Entities mentioned (people, organizations, countries, equipment)
4. Date range (e.g., "this week" = last 7 days, "this month" = last 30 days)
5. Threat level filter (if mentioned: HIGH, CRITICAL, etc.)
6. Sentiment filter (if "negative" or "critical" articles requested)
7. Monitoring filter (if monitoring-related)
8. Query type:
   - situation_brief: "What is happening in X?"
   - location_search: "Show news from Pune / Ladakh"
   - threat_search: "High-threat articles about X"
   - entity_search: "News about Rafale / INS Vikrant / Modi"
   - trend_analysis: "What trends in X over Y period?"
   - comparison: "Compare A and B"
   - country_brief: "India-China relations / India-Pakistan developments"
   - monitoring_query: "Which locations need monitoring?"
   - general_search: anything else

Return JSON only."""

INTENT_PROMPT = """Analyze this query and return JSON:
{
  "query_type": "situation_brief|location_search|threat_search|entity_search|trend_analysis|comparison|country_brief|monitoring_query|general_search",
  "topic": "main topic or null",
  "locations": ["location1", "location2"],
  "entities": ["entity1", "entity2"],
  "countries": ["country1", "country2"],
  "date_range_days": null or integer (e.g., 7 for "this week"),
  "threat_level_filter": null or "HIGH|CRITICAL|MODERATE",
  "sentiment_filter": null or "Negative|Positive|Escalatory|Critical",
  "monitoring_filter": null or true,
  "search_terms": ["keyword1", "keyword2"]
}

Query: """


def detect_intent(query: str) -> dict:
    """
    Use Gemini to understand user query intent.

    Falls back to simple keyword-based intent if Gemini unavailable.
    """

    client = _get_gemini()

    if client is None:
        return _fallback_intent(query)

    try:

        response = client.generate_content(
            [INTENT_SYSTEM, INTENT_PROMPT + query],
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 300,
            },
        )

        raw = response.text.strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            intent = json.loads(match.group(0))
        else:
            intent = _fallback_intent(query)

        logger.info(
            "Query intent: %s | locations: %s | entities: %s",
            intent.get("query_type"),
            intent.get("locations"),
            intent.get("entities"),
        )

        return intent

    except Exception as e:
        logger.warning("Intent detection failed: %s — using fallback", e)
        return _fallback_intent(query)


def _fallback_intent(query: str) -> dict:
    """Simple keyword-based intent fallback with alias normalization and token cleaning."""
    import re
    from src.nlp.indian_geography import CITY_TO_STATE, INDIAN_STATES, LOCATION_ALIASES
    from src.search.keyword_search import STOPWORDS

    query_lower = query.lower()
    raw_tokens = re.findall(r"[a-zA-Z0-9]+", query_lower)

    locations = []
    entities = []
    threat_filter = None
    sentiment_filter = None
    query_type = "general_search"

    # Check state & city aliases first
    for t in raw_tokens:
        if t in LOCATION_ALIASES:
            loc = LOCATION_ALIASES[t]
            if loc not in locations:
                locations.append(loc)

    for state in INDIAN_STATES:
        if re.search(r'\b' + re.escape(state.lower()) + r'\b', query_lower):
            if state not in locations:
                locations.append(state)

    for city in CITY_TO_STATE:
        if re.search(r'\b' + re.escape(city.lower()) + r'\b', query_lower):
            if city not in locations:
                locations.append(city)

    # Search terms: filter stopwords and detected locations
    locs_lower = {l.lower() for l in locations} | {k.lower() for k in LOCATION_ALIASES if LOCATION_ALIASES[k] in locations}
    search_terms = []
    for t in raw_tokens:
        if len(t) >= 2 and t not in STOPWORDS and t not in locs_lower:
            search_terms.append(t)

    # Threat filter
    if any(w in query_lower for w in ["high threat", "high-threat", "critical"]):
        threat_filter = "HIGH"

    # Sentiment filter
    if "negative" in query_lower:
        sentiment_filter = "Negative"
    elif "escalat" in query_lower:
        sentiment_filter = "Escalatory"

    # Query type
    if locations:
        query_type = "location_search"
    if any(w in query_lower for w in ["what is happening", "current status", "situation"]):
        query_type = "situation_brief"
    if any(w in query_lower for w in ["trend", "over the last", "during the last"]):
        query_type = "trend_analysis"

    # Date range
    date_days = None
    if "week" in query_lower:
        date_days = 7
    elif "month" in query_lower or "30 day" in query_lower:
        date_days = 30
    elif "today" in query_lower:
        date_days = 1

    return {
        "query_type": query_type,
        "topic": query,
        "locations": locations,
        "entities": entities,
        "countries": [],
        "date_range_days": date_days,
        "threat_level_filter": threat_filter,
        "sentiment_filter": sentiment_filter,
        "monitoring_filter": None,
        "search_terms": search_terms,
    }


# ============================================================================
# ARTICLE RETRIEVAL
# ============================================================================

def retrieve_articles(
    intent: dict,
    query: str,
    max_articles: int = 15,
) -> list[dict]:
    """
    Retrieve relevant articles using keyword + semantic search.
    Merges and re-ranks results with strict relevance filtering.
    """
    from src.search.keyword_search import keyword_search, search_by_location
    from src.search.semantic_search import semantic_search

    filters = _build_filters(intent)

    # Build search query from intent
    search_query = _build_search_query(intent, query)

    # 1. Keyword search
    kw_results = []
    if search_query:
        kw_results = keyword_search(search_query, limit=20, filters=filters)

    # 2. Location-based search if locations detected
    loc_results = []
    target_locations = intent.get("locations") or []
    for location in target_locations[:2]:
        loc_articles = search_by_location(location, limit=15, filters=filters)
        loc_results.extend(loc_articles)

    # 3. Semantic search (using clean query representation)
    sem_query = search_query if search_query else query
    sem_results = semantic_search(sem_query, limit=15, filters=filters, min_similarity=0.35)

    # Get full article data for semantic results
    sem_article_ids = {r["article_id"] for r in sem_results}
    sem_full = _fetch_articles_by_ids(list(sem_article_ids)) if sem_article_ids else []

    # 4. Merge and re-rank
    merged = _merge_results(
        kw_results,
        loc_results,
        sem_full,
        sem_results,
        query_locations=target_locations,
        query_terms=intent.get("search_terms") or [],
    )

    return merged[:max_articles]


def _build_filters(intent: dict) -> dict:
    """Convert intent to search filter dict."""

    filters = {}

    if tl := intent.get("threat_level_filter"):
        filters["threat_level"] = tl

    if sm := intent.get("sentiment_filter"):
        filters["sentiment"] = sm

    if intent.get("monitoring_filter"):
        filters["army_monitoring_needed"] = "YES"

    if days := intent.get("date_range_days"):
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        filters["published_after"] = cutoff.strftime("%Y-%m-%d")

    return filters


def _build_search_query(intent: dict, original_query: str) -> str:
    """Build a search query from intent components."""

    parts = []

    if locs := intent.get("locations"):
        parts.extend(locs)

    if terms := intent.get("search_terms"):
        parts.extend(terms)

    if entities := intent.get("entities"):
        parts.extend(entities)

    if countries := intent.get("countries"):
        parts.extend(countries)

    if not parts:
        from src.search.keyword_search import _extract_query_tokens
        parts = _extract_query_tokens(original_query)

    # Deduplicate preserving order
    seen = set()
    clean_parts = []
    for p in parts:
        p_str = str(p).strip()
        if p_str and p_str.lower() not in seen:
            seen.add(p_str.lower())
            clean_parts.append(p_str)

    return " ".join(clean_parts)[:200]


def _fetch_articles_by_ids(article_ids: list[str]) -> list[dict]:
    """Fetch full article records by IDs."""

    if not article_ids:
        return []

    try:
        conn = _get_db()
        cursor = conn.cursor()

        placeholders = ",".join("?" * len(article_ids))
        cursor.execute(
            f"SELECT * FROM articles WHERE article_id IN ({placeholders})",
            article_ids,
        )
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    except Exception as e:
        logger.error("DB fetch error: %s", e)
        return []


def _merge_results(
    keyword_results: list[dict],
    location_results: list[dict],
    semantic_results: list[dict],
    sem_scores: list[dict],
    query_locations: list[str] | None = None,
    query_terms: list[str] | None = None,
) -> list[dict]:
    """
    Merge and deduplicate results from different search methods.
    Calculates composite relevance score:
      - Keyword / phrase match in title / summary
      - Location match
      - Semantic similarity score (only above threshold)
      - Small threat multiplier only for confirmed relevant articles
    Drops articles below relevance threshold to prevent irrelevant noise.
    """
    query_locations = query_locations or []
    query_terms = query_terms or []

    id_to_article: dict[str, dict] = {}
    id_to_score: dict[str, float] = {}

    sem_score_map = {s.get("article_id"): s.get("semantic_score", 0.0) for s in sem_scores}

    for a in keyword_results:
        aid = a.get("article_id") or a.get("id") or ""
        if aid:
            id_to_article[aid] = a
            id_to_score[aid] = id_to_score.get(aid, 0.0) + 3.0

    for a in location_results:
        aid = a.get("article_id") or a.get("id") or ""
        if aid:
            id_to_article[aid] = a
            id_to_score[aid] = id_to_score.get(aid, 0.0) + 2.0

    for a in semantic_results:
        aid = a.get("article_id") or a.get("id") or ""
        if aid:
            id_to_article[aid] = a
            sim = sem_score_map.get(aid, 0.0)
            id_to_score[aid] = id_to_score.get(aid, 0.0) + (sim * 4.0 if sim >= 0.40 else 0.0)

    # Detailed relevance evaluation for each candidate
    for aid, article in list(id_to_article.items()):
        title = (article.get("title") or "").lower()
        summary = (article.get("ai_summary") or article.get("summary") or "").lower()
        text = (article.get("article_text") or "").lower()
        states = (article.get("states") or "").lower()
        cities = (article.get("cities") or "").lower()

        # Query search terms matching
        term_matched = False
        term_score = 0.0
        for term in query_terms:
            t_low = term.lower()
            if len(t_low) < 2:
                continue
            pattern = r'\b' + re.escape(t_low) + r'\b'
            if re.search(pattern, title):
                term_score += 5.0
                term_matched = True
            elif re.search(pattern, summary):
                term_score += 3.0
                term_matched = True
            elif re.search(pattern, text):
                term_score += 0.5
                term_matched = True

        id_to_score[aid] += term_score

        # If user searched for specific topic terms and article matched NO terms AND has low semantic score, drop it
        sim = sem_score_map.get(aid, 0.0)
        if query_terms and not term_matched and sim < 0.45:
            id_to_score[aid] -= 10.0

        # Query location matching & penalty
        if query_locations:
            loc_matched = False
            for ql in query_locations:
                ql_low = ql.lower()
                if ql_low in states or ql_low in cities or ql_low in title or ql_low in summary:
                    loc_matched = True
                    break
            if loc_matched:
                id_to_score[aid] += 4.0
            else:
                # If a specific location was queried, strictly penalize articles with no location match
                id_to_score[aid] -= 6.0

        # Threat bonus only for confirmed relevant articles
        if id_to_score[aid] >= 3.0:
            tl = (article.get("threat_level") or "").upper()
            threat_bonus = {"CRITICAL": 1.5, "HIGH": 1.0, "MODERATE": 0.5, "LOW": 0.0}
            id_to_score[aid] += threat_bonus.get(tl, 0.0)

    # Filter out articles below relevance threshold
    min_score = 4.0 if (query_terms and query_locations) else 3.0
    valid_articles = []
    sorted_ids = sorted(id_to_score.keys(), key=lambda x: id_to_score[x], reverse=True)

    for aid in sorted_ids:
        score = id_to_score[aid]
        if score >= min_score and aid in id_to_article:
            valid_articles.append(id_to_article[aid])

    return valid_articles


# ============================================================================
# MAIN QUERY HANDLER
# ============================================================================

def process_query(query: str) -> dict:
    """
    Main entry point for natural language queries.

    Args:
        query: User's natural language question.

    Returns:
        Structured response dict.
    """

    logger.info("Processing query: %s", query[:80])

    # 1. Detect intent
    intent = detect_intent(query)

    # 2. Retrieve relevant articles
    articles = retrieve_articles(intent, query)

    logger.info(
        "Retrieved %d articles for: '%s'",
        len(articles),
        query[:60],
    )

    # 3. Generate response via Gemini
    from src.intelligence.insight_engine import (
        generate_situation_brief,
        generate_country_brief,
        detect_trends,
        generate_chat_response,
    )

    query_type = intent.get("query_type", "general_search")

    if query_type == "situation_brief":
        topic = (
            intent.get("topic")
            or (intent.get("locations") or ["the situation"])[0]
        )
        response = generate_situation_brief(topic, articles)

    elif query_type == "country_brief":
        countries = intent.get("countries") or []
        pair = " - ".join(countries[:2]) if countries else "India relations"
        text_response = generate_country_brief(pair, articles)
        response = {
            "question": query,
            "current_assessment": text_response,
            "recent_developments": [],
            "key_locations": intent.get("locations") or [],
            "key_actors": intent.get("entities") or [],
            "security_relevance": "See assessment above.",
            "trend": "Unclear",
            "confidence": "Medium",
            "supporting_articles": _format_articles_brief(articles[:5]),
            "disclaimer": "⚠️ AI-generated analysis. Not an official assessment.",
        }

    elif query_type == "trend_analysis":
        days = intent.get("date_range_days") or 30
        text_response = detect_trends(articles, f"last {days} days")
        response = {
            "question": query,
            "current_assessment": text_response,
            "recent_developments": [],
            "key_locations": [],
            "key_actors": [],
            "security_relevance": "See trend analysis above.",
            "trend": "See analysis",
            "confidence": "Medium",
            "supporting_articles": _format_articles_brief(articles[:5]),
            "disclaimer": "⚠️ AI-generated trend analysis. Not an official assessment.",
        }

    else:
        # General chat response (RAG)
        response = generate_chat_response(query, articles, intent)

    # Always ensure question is in response
    response["question"] = query

    return response


def _format_articles_brief(articles: list[dict]) -> list[dict]:
    """Quick format of articles for response."""
    return [
        {
            "article_id": a.get("article_id") or a.get("id", ""),
            "title": a.get("title") or "Untitled",
            "source": a.get("source") or "Unknown",
            "published_at": (a.get("published_at") or "")[:10],
            "url": a.get("url") or "",
            "threat_level": a.get("threat_level") or "UNCLEAR",
        }
        for a in articles
    ]
