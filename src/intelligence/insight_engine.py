"""
Gemini-Powered Intelligence Insight Engine
===========================================

Provides cross-article analysis, situation briefs, trend analysis,
and strategic summaries using Gemini API.

This module operates on ALREADY RETRIEVED article sets — it never
queries the full database directly. The retrieval is done first
(keyword + semantic search), then Gemini synthesizes.

Functions:
    generate_daily_brief(articles)         — Today's strategic overview
    generate_situation_brief(topic, articles) — Topic/location brief
    generate_country_brief(pair, articles) — India-X bilateral brief
    generate_regional_brief(region, articles) — Regional brief
    detect_trends(articles, timeframe)     — Trend detection
    analyze_chat_response(query, articles) — RAG chat response

All outputs are clearly labeled as AI-generated analysis.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

GEMINI_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("LLM_MODEL", "gemini-flash-latest")

# Max total context characters to send to Gemini
MAX_CONTEXT_CHARS = 80000

# Max characters per article in context
MAX_ARTICLE_CHARS = 800

# Rate limiting
API_RATE_LIMIT_SECONDS = 0.5

_gemini_client = None


def _get_client():
    """Initialize Gemini client with model fallback chain."""
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
        logger.error("google-generativeai not installed.")
    return _gemini_client


# ============================================================================
# CONTEXT BUILDER
# ============================================================================

def _build_article_context(articles: list[dict]) -> str:
    """
    Build a compact context string from a list of articles.
    Each article is a short numbered entry.
    """

    context_parts = []
    total_chars = 0

    for i, article in enumerate(articles, 1):

        title = article.get("title") or "Untitled"
        source = article.get("source") or "Unknown"
        published = article.get("published_at") or ""
        summary = (
            article.get("ai_summary")
            or article.get("summary")
            or article.get("article_text", "")[:300]
        )
        threat = article.get("threat_level") or ""
        locations = ", ".join(
            (article.get("states") or [])
            + (article.get("cities") or [])
        ) if isinstance(article.get("states"), list) else ""

        entry = f"""[{i}] {title}
Source: {source} | Date: {published[:10] if published else 'N/A'}
Threat Level (AI Flag): {threat}
Locations: {locations or 'N/A'}
Summary: {summary[:MAX_ARTICLE_CHARS]}
"""

        if total_chars + len(entry) > MAX_CONTEXT_CHARS:
            logger.info("Context limit reached at article %d", i)
            break

        context_parts.append(entry)
        total_chars += len(entry)

    return "\n---\n".join(context_parts)


def _gemini_generate(system_prompt: str, user_prompt: str) -> str | None:
    """Single Gemini API call with error handling."""

    client = _get_client()

    if client is None:
        return "Gemini API not available. Check LLM_API_KEY in .env"

    try:
        response = client.generate_content(
            [system_prompt, user_prompt],
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": 2000,
            },
        )
        return response.text.strip()
    except Exception as e:
        logger.error("Gemini API error: %s", e)
        return f"Analysis unavailable: {str(e)[:100]}"


# ============================================================================
# DAILY STRATEGIC BRIEF
# ============================================================================

DAILY_BRIEF_SYSTEM = """You are an intelligence analyst producing a daily strategic brief for 
Indian Army leadership. Your brief covers defence, military, national security, and geopolitical 
developments that may affect India's security interests.

IMPORTANT:
- Base your analysis ONLY on the provided articles.
- Clearly distinguish reported facts from analytical assessment.
- All analysis is AI-generated. Label it as such.
- Be concise, structured, and professionally written.
- Do not fabricate information not in the provided articles."""


def generate_daily_brief(articles: list[dict]) -> str:
    """
    Generate a daily strategic intelligence brief from recent articles.
    """

    if not articles:
        return "No articles available for today's brief."

    context = _build_article_context(articles[:30])

    prompt = f"""Based on the following {len(articles)} recent news articles, produce a 
**Daily Strategic Intelligence Brief** with these sections:

## Executive Summary
(2-3 sentence overview of the most significant developments today)

## Major Defence Developments
(Key military, procurement, technology developments)

## Geopolitical Highlights
(International relations, diplomatic developments)

## National Security
(Internal security, border situation, terrorism)

## Emerging Situations
(Any developing situations requiring continued monitoring)

## Notable Entities
(Key individuals, organizations, countries mentioned)

---
ARTICLES:
{context}

Note: This is an AI-generated analytical summary. Not an official intelligence assessment."""

    result = _gemini_generate(DAILY_BRIEF_SYSTEM, prompt)
    return result or "Daily brief generation failed."


# ============================================================================
# SITUATION BRIEF
# ============================================================================

SITUATION_BRIEF_SYSTEM = """You are an intelligence analyst producing a situation brief 
for Indian Army analysts. Your role is to synthesize multiple news reports into a 
coherent situational picture.

Base your analysis ONLY on the provided articles. 
Clearly state uncertainty where information is incomplete or conflicting.
This is AI-generated analytical content — not an official intelligence assessment."""


def _parse_json_list(val: Any) -> list[str]:
    """Safely parse JSON-stringified lists or list objects into clean strings without raw JSON tokens."""
    if not val:
        return []
    if isinstance(val, list):
        res = []
        for x in val:
            if isinstance(x, str) and (x.strip().startswith("[") or x.strip().startswith("{")):
                res.extend(_parse_json_list(x))
            elif x:
                clean = str(x).strip("[]'\"").strip()
                if clean and clean not in res:
                    res.append(clean)
        return res
    if isinstance(val, str):
        val = val.strip()
        if (val.startswith("[") and val.endswith("]")) or (val.startswith("{") and val.endswith("}")):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, (list, dict)):
                    return _parse_json_list(parsed)
            except Exception:
                pass
        # Clean string
        cleaned = val.strip("[]'\"").strip()
        return [cleaned] if cleaned else []
    return [str(val).strip()]


def _synthesize_local_response(query: str, articles: list[dict], topic: str | None = None) -> dict:
    """Local analytical synthesis fallback when Gemini API is offline or rate-limited."""
    if not articles:
        return {
            "question": query,
            "topic": topic or query,
            "current_assessment": f"No recent intelligence articles found in the database for '{query}'.",
            "recent_developments": [],
            "key_locations": [],
            "key_actors": [],
            "security_relevance": "Insufficient data in current intelligence feed.",
            "trend": "Unclear",
            "confidence": "Low",
            "confidence_reason": "No articles retrieved.",
            "supporting_articles": [],
            "disclaimer": "⚠️ AI-generated analysis. Not an official intelligence assessment.",
        }

    # Extract highlights from top relevant articles
    developments = []
    locations: list[str] = []
    actors: list[str] = []
    threats = []

    for a in articles[:6]:
        title = (a.get("title") or "").strip()
        if title and title not in developments:
            developments.append(title)

        for loc_field in ("cities", "states", "localities", "districts", "regions", "countries"):
            for loc in _parse_json_list(a.get(loc_field)):
                if loc and loc not in locations:
                    locations.append(loc)

        for actor_field in ("organizations", "people", "equipment"):
            for act in _parse_json_list(a.get(actor_field)):
                if act and act not in actors:
                    actors.append(act)

        if tl := a.get("threat_level"):
            threats.append(tl.upper())

    if "CRITICAL" in threats:
        primary_threat = "CRITICAL"
    elif "HIGH" in threats:
        primary_threat = "HIGH"
    elif "MODERATE" in threats:
        primary_threat = "MODERATE"
    else:
        primary_threat = "LOW"

    trend = "Escalating" if primary_threat in ("HIGH", "CRITICAL") else "Stable"

    # Coherent assessment focused on primary event
    primary_article = articles[0]
    lead_summary = (
        primary_article.get("ai_summary")
        or primary_article.get("summary")
        or primary_article.get("title")
        or ""
    ).strip()

    if len(articles) > 1:
        assessment = f"{lead_summary} Monitored intelligence includes {len(articles)} correlated reports."
    else:
        assessment = lead_summary

    if primary_threat == "CRITICAL":
        relevance = f"Critical security event requiring immediate operational tracking across {len(articles)} verified report(s)."
    elif primary_threat == "HIGH":
        relevance = f"High-priority security development under continuous military monitoring across {len(articles)} verified report(s)."
    else:
        relevance = f"Assessed at {primary_threat} threat level across {len(articles)} monitored intelligence reports."

    return {
        "question": query,
        "topic": topic or query,
        "current_assessment": assessment[:800],
        "recent_developments": developments[:5],
        "key_locations": locations[:6],
        "key_actors": actors[:6],
        "security_relevance": relevance,
        "trend": trend,
        "confidence": "High" if len(articles) >= 1 else "Medium",
        "confidence_reason": f"Synthesized from {len(articles)} verified news feed reports.",
        "supporting_articles": _format_supporting_articles(articles[:8]),
        "disclaimer": "⚠️ AI-generated analytical response based on collected news articles. Not an official intelligence assessment.",
    }


def generate_situation_brief(
    topic: str,
    articles: list[dict],
) -> dict:
    """
    Generate a situation brief for a specific topic, location, or issue.

    Returns structured dict suitable for the chatbot response format.
    """

    if not articles:
        return _synthesize_local_response(topic, [], topic=topic)

    context = _build_article_context(articles[:20])

    prompt = f"""Produce a situation brief about: "{topic}"

Based on the provided articles, generate a JSON response with EXACTLY this structure:
{{
  "current_assessment": "2-3 sentence current assessment",
  "recent_developments": ["Development 1", "Development 2", "Development 3"],
  "key_locations": ["Location 1", "Location 2"],
  "key_actors": ["Actor 1", "Actor 2"],
  "security_relevance": "Assessment of security/defence implications",
  "trend": "Escalating|Stable|De-escalating|Unclear",
  "confidence": "Low|Medium|High"
}}

ARTICLES:
{context}

Return ONLY valid JSON. No markdown, no code blocks."""

    response = _gemini_generate(SITUATION_BRIEF_SYSTEM, prompt)

    # Try to parse as JSON
    brief_data = None
    if response and not response.startswith("Gemini API not available") and not response.startswith("Analysis unavailable"):
        try:
            import re
            response_clean = re.sub(r'```(?:json)?\s*', '', response).strip()
            response_clean = re.sub(r'```\s*$', '', response_clean).strip()
            brief_data = json.loads(response_clean)
        except (json.JSONDecodeError, TypeError):
            brief_data = None

    if not brief_data or not isinstance(brief_data, dict) or not brief_data.get("current_assessment"):
        brief_data = _synthesize_local_response(topic, articles, topic=topic)
    else:
        brief_data["topic"] = topic
        brief_data["question"] = topic
        brief_data["supporting_articles"] = _format_supporting_articles(articles[:8])
        brief_data["disclaimer"] = "⚠️ AI-generated situation analysis. Not an official assessment."

    return brief_data


# ============================================================================
# COUNTRY BRIEF
# ============================================================================

def generate_country_brief(
    country_pair: str,
    articles: list[dict],
) -> str:
    """
    Generate an India-X bilateral relations brief.

    Args:
        country_pair: e.g., "India-China", "India-Pakistan"
        articles: Relevant articles.
    """

    if not articles:
        return f"No recent articles found for {country_pair} relations."

    context = _build_article_context(articles[:25])

    prompt = f"""Produce a bilateral relations brief for: {country_pair}

Cover:
## Current Status
## Diplomatic Activity
## Military/Defence Activity
## Border/Security Developments (if applicable)
## Economic Security Dimensions
## Recent Trend (Improving/Stable/Deteriorating/Unclear)
## Key Supporting Evidence

Based on these articles:
{context}

Note: AI-generated analytical brief. Not an official assessment."""

    return _gemini_generate(SITUATION_BRIEF_SYSTEM, prompt) or "Brief unavailable."


# ============================================================================
# TREND ANALYSIS
# ============================================================================

TREND_SYSTEM = """You are an intelligence analyst identifying trends in defence and 
geopolitical news. Focus on patterns, repetition, escalation/de-escalation indicators,
and emerging themes across multiple articles.

Be evidence-based. Note uncertainty. Label all analysis as AI-generated."""


def detect_trends(
    articles: list[dict],
    timeframe: str = "last 30 days",
) -> str:
    """
    Identify trends across a set of articles.
    """

    if not articles:
        return "No articles available for trend analysis."

    context = _build_article_context(articles[:40])

    prompt = f"""Analyze these {len(articles)} articles from {timeframe} and identify key trends.

## Major Trends
(List 3-5 most significant trends with evidence)

## Escalation Patterns
(Any topics showing increasing activity or tension)

## De-escalation Patterns
(Any topics showing reduced tensions)

## Geographic Hotspots
(Locations appearing most frequently with security relevance)

## Recurring Actors
(Organizations, countries, individuals appearing frequently)

## Emerging Situations
(New developments that may require monitoring)

ARTICLES:
{context}

Note: AI-generated trend analysis based on available articles only."""

    return _gemini_generate(TREND_SYSTEM, prompt) or "Trend analysis unavailable."


# ============================================================================
# CHAT / RAG RESPONSE
# ============================================================================

CHAT_SYSTEM = """You are an AI intelligence analyst assistant for Indian Army analysts.
You answer questions about defence, military affairs, national security, and geopolitics
using ONLY the provided news articles as your evidence base.

CRITICAL RULES:
1. Base your answer ONLY on the provided articles. Do not use pretrained knowledge as primary source.
2. Clearly distinguish: Reported Facts vs AI Analysis vs Uncertainty.
3. If the articles don't contain enough information, say so clearly.
4. When sources conflict, mention "Reports differ on..."
5. All analysis is AI-generated and NOT an official intelligence assessment.
6. Provide a structured response — not a single paragraph.

Response format:
- Current Assessment: [factual summary from articles]
- Recent Developments: [bullet points]
- Key Locations: [if relevant]
- Key Actors: [if relevant]
- Security Relevance: [analytical assessment — labeled as AI-generated]
- Trend: [Escalating|Stable|De-escalating|Unclear]
- Confidence: [Low|Medium|High] with brief reason
- Supporting Evidence: [cite article numbers]"""


def generate_chat_response(
    query: str,
    articles: list[dict],
    intent: dict | None = None,
) -> dict:
    """
    Generate a structured chat response using retrieved articles.

    Args:
        query: User's natural language query.
        articles: Retrieved relevant articles (pre-filtered).
        intent: Optional intent/entity dict from query analysis.

    Returns:
        Structured response dict.
    """

    if not articles:
        return {
            "question": query,
            "current_assessment": (
                "No relevant articles found in the database for this query. "
                "Try running the pipeline to collect more news."
            ),
            "recent_developments": [],
            "key_locations": [],
            "key_actors": [],
            "security_relevance": "Insufficient data.",
            "trend": "Unclear",
            "confidence": "Low",
            "confidence_reason": "No articles retrieved.",
            "supporting_articles": [],
            "disclaimer": "AI-generated response. Not an official intelligence assessment.",
        }

    context = _build_article_context(articles)

    prompt = f"""Question: {query}

Based on the following {len(articles)} retrieved articles, provide a structured response.
Return a JSON object with these fields:
{{
  "current_assessment": "2-3 sentence factual summary",
  "recent_developments": ["point 1", "point 2", "point 3"],
  "key_locations": ["location 1", "location 2"],
  "key_actors": ["actor 1", "actor 2"],
  "security_relevance": "AI-generated security relevance assessment",
  "trend": "Escalating|Stable|De-escalating|Unclear",
  "confidence": "Low|Medium|High",
  "confidence_reason": "Why this confidence level"
}}

RETRIEVED ARTICLES:
{context}

Return ONLY valid JSON. No markdown, no code blocks."""

    response = _gemini_generate(CHAT_SYSTEM, prompt)

    response_data = None
    if response and not response.startswith("Gemini API not available") and not response.startswith("Analysis unavailable"):
        try:
            import re
            response_clean = re.sub(r'```(?:json)?\s*', '', response).strip()
            response_clean = re.sub(r'```\s*$', '', response_clean).strip()
            response_data = json.loads(response_clean)
        except (json.JSONDecodeError, TypeError):
            response_data = None

    if not response_data or not isinstance(response_data, dict) or not response_data.get("current_assessment"):
        response_data = _synthesize_local_response(query, articles)
    else:
        response_data["question"] = query
        response_data["supporting_articles"] = _format_supporting_articles(articles[:8])
        response_data["disclaimer"] = (
            "⚠️ AI-generated analytical response based on collected news articles. "
            "Not an official intelligence assessment."
        )

    return response_data


# ============================================================================
# REGIONAL BRIEF
# ============================================================================

def generate_regional_brief(
    region: str,
    articles: list[dict],
) -> str:
    """Generate a regional situation brief."""

    if not articles:
        return f"No recent articles for region: {region}"

    context = _build_article_context(articles[:20])

    prompt = f"""Produce a regional brief for: {region}

## Current Situation
## Recent Developments  
## Key Locations in Focus
## Major Actors
## Security/Threat Overview (AI-generated flag)
## Monitoring Considerations
## Confidence Level

ARTICLES:
{context}

Note: AI-generated analytical brief."""

    return _gemini_generate(SITUATION_BRIEF_SYSTEM, prompt) or "Brief unavailable."


# ============================================================================
# HELPERS
# ============================================================================

def _format_supporting_articles(articles: list[dict]) -> list[dict]:
    """Format articles for supporting evidence display."""

    result = []

    for article in articles:
        result.append({
            "article_id": article.get("article_id") or article.get("id", ""),
            "title": article.get("title") or "Untitled",
            "source": article.get("source") or "Unknown",
            "published_at": (article.get("published_at") or "")[:10],
            "url": article.get("url") or "",
            "threat_level": article.get("threat_level") or "UNCLEAR",
            "summary": (
                article.get("ai_summary")
                or article.get("summary")
                or ""
            )[:300],
        })

    return result
