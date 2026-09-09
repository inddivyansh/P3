"""
D-P1-22 — News Feed to Digest Pipeline
=======================================

Public interface for the categorisation engine.

The actual model implementation is in zero_shot.py.
"""

from __future__ import annotations

from typing import Any

from .zero_shot import (
    CATEGORIES,
    TAXONOMY,
    classify_article,
    classify_articles,
    load_classifier,
    run_categorization,
)


def categorize_article(
    article: dict[str, Any],
) -> dict[str, Any]:
    """
    Categorize one article.
    """

    return classify_article(
        article
    )


def categorize_articles(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Categorize multiple articles.

    Uses the CUDA-optimized batch implementation.
    """

    return classify_articles(
        articles
    )


__all__ = [
    "CATEGORIES",
    "TAXONOMY",
    "load_classifier",
    "categorize_article",
    "categorize_articles",
    "run_categorization",
]