"""
Fast Article Summarizer (Local Extractive & Pipeline Processing)
================================================================

Extracts clean, concise article summaries at ingestion time without
calling external LLMs per article.

Full multi-article synthesis and topic-level LLM summarization
are performed on-demand in the AI Analyst chatbot and Reports page.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def extract_concise_summary(text: str, max_words: int = 60) -> str:
    """
    Extract a concise, clean summary from the initial sentences of article text.
    """
    if not text:
        return ""

    # Clean whitespace
    cleaned = re.sub(r'\s+', ' ', text).strip()

    # Split by sentence terminators
    sentences = re.split(r'(?<=[.!?])\s+', cleaned)
    selected = []
    word_count = 0

    for sent in sentences:
        s = sent.strip()
        if not s:
            continue
        # Skip datelines like "NEW DELHI: " or "PTI -- "
        s = re.sub(r'^[A-Z\s]{2,15}\s*[:-–—]\s*', '', s)
        words = s.split()
        if word_count + len(words) > max_words and selected:
            break
        selected.append(s)
        word_count += len(words)
        if word_count >= 30:
            break

    result = " ".join(selected)
    return result if result else cleaned[:250]


def summarize_article(article: dict[str, Any]) -> str:
    """
    Generate an ingestion summary for a single article using clean extractive text.
    """
    existing_summary = article.get("summary") or article.get("ai_summary") or ""
    if existing_summary and len(existing_summary.strip()) > 40:
        return existing_summary.strip()

    text = article.get("article_text") or article.get("text") or ""
    return extract_concise_summary(text)


def batch_summarize_articles(
    articles: list[dict[str, Any]],
    skip_processed: bool = True,
) -> list[dict[str, Any]]:
    """
    Process summaries for a batch of articles locally without external API latency.
    """
    for article in articles:
        if skip_processed and article.get("ai_summary"):
            continue

        summary = summarize_article(article)
        article["ai_summary"] = summary

    logger.info("Local article summarization complete for %d articles.", len(articles))
    return articles


def run_summarization(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Execute local summarization stage in pipeline.
    """
    logger.info("======================================================")
    logger.info("Intelligence Platform — Local Summarization Stage")
    logger.info("======================================================")

    articles = batch_summarize_articles(articles)
    return articles
