"""Text cleaning and metadata normalisation."""
"""
D-P1-22 — News Feed to Digest Pipeline

Article text cleaning and preprocessing module.

Responsibilities:
    1. Load extracted articles
    2. Remove unwanted HTML / whitespace artefacts
    3. Normalize article text
    4. Remove obviously unusable articles
    5. Create classifier-ready text
    6. Save cleaned articles

This module does NOT:
    - classify articles
    - perform semantic deduplication
    - generate the digest
"""

import json
import logging
import re
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "articles.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "cleaned_articles.json"
)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_articles(
    input_path: Path = INPUT_FILE,
) -> list[dict[str, Any]]:
    """Load articles produced by article_fetcher."""

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}\n"
            "Run article_fetcher.py first."
        )

    with input_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    articles = data.get("articles", [])

    if not isinstance(articles, list):
        raise ValueError(
            "Invalid articles.json format."
        )

    logger.info(
        "Loaded %d article(s)",
        len(articles),
    )

    return articles


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def remove_html(text: str) -> str:
    """
    Remove basic HTML tags.

    Trafilatura normally returns clean text, but this protects the
    downstream pipeline if HTML fragments remain.
    """

    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    return text


def normalize_whitespace(text: str) -> str:
    """
    Normalize spaces, tabs and excessive line breaks.
    """

    text = text.replace(
        "\xa0",
        " ",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def remove_url_fragments(text: str) -> str:
    """
    Remove obvious standalone URLs from article text.

    URLs are not useful for the text classifier and can introduce
    unnecessary noise.
    """

    text = re.sub(
        r"https?://\S+",
        " ",
        text,
    )

    text = re.sub(
        r"www\.\S+",
        " ",
        text,
    )

    return text


def clean_text(text: str | None) -> str:
    """
    Apply the complete text-cleaning pipeline.
    """

    if not text:
        return ""

    text = remove_html(text)

    text = remove_url_fragments(text)

    text = normalize_whitespace(text)

    return text


# ---------------------------------------------------------------------------
# Article validation
# ---------------------------------------------------------------------------

MIN_ARTICLE_LENGTH = 200


def is_valid_article(
    article: dict[str, Any],
) -> bool:
    """
    Determine whether an article contains enough text
    to be useful for downstream NLP processing.
    """

    article_text = article.get(
        "article_text"
    )

    if not article_text:
        return False

    if len(article_text.strip()) < MIN_ARTICLE_LENGTH:
        return False

    return True


# ---------------------------------------------------------------------------
# Classifier text construction
# ---------------------------------------------------------------------------

def build_classifier_text(
    article: dict[str, Any],
) -> str:
    """
    Construct the text that will be supplied to the categorisation model.

    Title is deliberately included because news headlines contain
    important topical information.

    Structure:

        TITLE
        ARTICLE BODY
    """

    title = clean_text(
        article.get("title")
    )

    body = clean_text(
        article.get("article_text")
    )

    if title and body:
        return f"{title}. {body}"

    return title or body


# ---------------------------------------------------------------------------
# Process articles
# ---------------------------------------------------------------------------

def process_articles(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Clean and validate all articles.
    """

    cleaned_articles = []

    removed = 0

    for index, article in enumerate(
        articles,
        start=1,
    ):

        title = clean_text(
            article.get("title")
        )

        article_text = clean_text(
            article.get("article_text")
        )

        cleaned_article = dict(article)

        cleaned_article["title"] = title
        cleaned_article["article_text"] = article_text

        if not is_valid_article(
            cleaned_article
        ):
            removed += 1

            logger.warning(
                "[%d/%d] Removing unusable article: %s",
                index,
                len(articles),
                title or "Untitled",
            )

            continue

        classifier_text = build_classifier_text(
            cleaned_article
        )

        cleaned_article[
            "classifier_text"
        ] = classifier_text

        cleaned_article[
            "text_length"
        ] = len(article_text)

        cleaned_articles.append(
            cleaned_article
        )

    logger.info(
        "Cleaning complete | kept=%d | removed=%d",
        len(cleaned_articles),
        removed,
    )

    return cleaned_articles


# ---------------------------------------------------------------------------
# Save data
# ---------------------------------------------------------------------------

def save_articles(
    articles: list[dict[str, Any]],
    output_path: Path = OUTPUT_FILE,
) -> None:
    """Save cleaned articles."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "article_count": len(articles),
        "articles": articles,
    }

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            payload,
            file,
            indent=2,
            ensure_ascii=False,
        )

    logger.info(
        "Saved %d cleaned article(s) to %s",
        len(articles),
        output_path,
    )


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------

def run_cleaning() -> list[dict[str, Any]]:
    """Run the complete text-cleaning stage."""

    articles = load_articles()

    cleaned_articles = process_articles(
        articles
    )

    save_articles(
        cleaned_articles
    )

    return cleaned_articles


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_cleaning()