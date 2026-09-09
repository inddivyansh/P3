"""Categorised digest generation and grounded summarisation."""
"""
D-P1-22 — News Feed to Digest Pipeline

Categorised news digest generator.

Purpose:
    Convert categorised article records into a readable digest.

Current implementation:
    - SQLite as data source
    - One representative article per story
    - Group stories by category
    - Generate short extractive summaries
    - Produce Markdown and HTML output

Future extension:
    Replace the extractive summary function with an LLM-based
    grounded summarisation function without changing the rest
    of the pipeline.
"""

import html
import logging
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ============================================================================
# PATHS
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_FILE = (
    PROJECT_ROOT
    / "data"
    / "database"
    / "news_pipeline.db"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "digests"
)

MARKDOWN_OUTPUT = (
    OUTPUT_DIR
    / "latest_digest.md"
)

HTML_OUTPUT = (
    OUTPUT_DIR
    / "latest_digest.html"
)


# ============================================================================
# CONFIGURATION
# ============================================================================

# Number of stories displayed per category.
MAX_STORIES_PER_CATEGORY = 10

# Number of sentences used for the baseline summary.
SUMMARY_SENTENCES = 3

# Categories appear in this order in the final digest.
CATEGORY_ORDER = [
    "Defence & Security",
    "National Affairs",
    "International Affairs",
    "Economy & Industry",
    "Science & Technology",
    "Society & Public Policy",
    "Sports & Culture",
]


# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================================
# DATABASE
# ============================================================================

def get_connection() -> sqlite3.Connection:
    """Open the project SQLite database."""

    if not DATABASE_FILE.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_FILE}\n"
            "Run the storage stage first."
        )

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    connection.row_factory = sqlite3.Row

    return connection


def load_stories() -> list[dict[str, Any]]:
    """
    Load story representatives from the database.

    Only representative articles are used because multiple sources
    may belong to the same story cluster.
    """

    connection = get_connection()

    try:

        cursor = connection.execute(
            """
            SELECT
                article_id,
                title,
                url,
                source,
                published_at,
                article_text,
                summary,
                story_cluster_id,
                category,
                category_confidence
            FROM articles
            WHERE
                is_cluster_representative = 1
                AND category IS NOT NULL
            ORDER BY
                published_at DESC
            """
        )

        rows = cursor.fetchall()

    finally:

        connection.close()

    stories = [
        dict(row)
        for row in rows
    ]

    logger.info(
        "Loaded %d categorized stories.",
        len(stories),
    )

    return stories


# ============================================================================
# TEXT PROCESSING
# ============================================================================

def clean_sentence(
    sentence: str,
) -> str:
    """Normalize a sentence for digest display."""

    sentence = re.sub(
        r"\s+",
        " ",
        sentence,
    )

    return sentence.strip()


def split_sentences(
    text: str,
) -> list[str]:
    """
    Split article text into approximate sentences.

    This is intentionally lightweight. The digest baseline does not
    require another NLP dependency.
    """

    if not text:
        return []

    text = text.strip()

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text,
    )

    cleaned = [
        clean_sentence(sentence)
        for sentence in sentences
        if sentence.strip()
    ]

    return cleaned


def extractive_summary(
    article_text: str | None,
    sentence_count: int = SUMMARY_SENTENCES,
) -> str:
    """
    Generate a simple extractive summary.

    The first few meaningful sentences are selected.

    This is our no-API fallback and provides a deterministic
    baseline against which a future LLM summarizer can be compared.
    """

    if not article_text:
        return "Summary unavailable."

    sentences = split_sentences(
        article_text
    )

    if not sentences:
        return "Summary unavailable."

    selected = sentences[
        :sentence_count
    ]

    return " ".join(selected)


# ============================================================================
# STORY FORMAT
# ============================================================================

def format_story_markdown(
    story: dict[str, Any],
) -> str:
    """Format one story for Markdown."""

    title = story.get(
        "title",
        "Untitled",
    )

    source = story.get(
        "source",
        "Unknown source",
    )

    url = story.get(
        "url",
        "",
    )

    confidence = float(
        story.get(
            "category_confidence",
            0.0,
        )
        or 0.0
    )

    summary = extractive_summary(
        story.get(
            "article_text"
        )
    )

    confidence_percent = (
        confidence * 100
    )

    return (
        f"### {title}\n\n"
        f"**Source:** {source}  \n"
        f"**Classification confidence:** "
        f"{confidence_percent:.1f}%  \n\n"
        f"{summary}\n\n"
        f"[Read original article]({url})\n"
    )


# ============================================================================
# GROUP STORIES
# ============================================================================

def group_by_category(
    stories: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group stories according to their predicted category."""

    grouped = defaultdict(list)

    for story in stories:

        category = story.get(
            "category"
        )

        if category:
            grouped[category].append(
                story
            )

    return dict(grouped)


# ============================================================================
# MARKDOWN DIGEST
# ============================================================================

def generate_markdown_digest(
    stories: list[dict[str, Any]],
) -> str:
    """
    Generate the complete Markdown digest.
    """

    grouped = group_by_category(
        stories
    )

    generated_at = datetime.now(
        timezone.utc
    ).strftime(
        "%d %B %Y, %H:%M UTC"
    )

    total_stories = sum(
        len(items)
        for items in grouped.values()
    )

    lines = []

    lines.append(
        "# D-P1-22 — News Intelligence Digest"
    )

    lines.append("")

    lines.append(
        f"**Generated:** {generated_at}"
    )

    lines.append("")

    lines.append(
        f"**Stories:** {total_stories}"
    )

    lines.append("")

    lines.append(
        "---"
    )

    lines.append("")

    for category in CATEGORY_ORDER:

        category_stories = grouped.get(
            category,
            [],
        )

        if not category_stories:
            continue

        lines.append(
            f"## {category}"
        )

        lines.append("")

        for story in category_stories[
            :MAX_STORIES_PER_CATEGORY
        ]:

            lines.append(
                format_story_markdown(
                    story
                )
            )

            lines.append(
                "---"
            )

            lines.append("")

    # Include unexpected categories if the taxonomy
    # changes in the future.
    known_categories = set(
        CATEGORY_ORDER
    )

    unexpected_categories = [
        category
        for category in grouped
        if category not in known_categories
    ]

    for category in sorted(
        unexpected_categories
    ):

        lines.append(
            f"## {category}"
        )

        lines.append("")

        for story in grouped[
            category
        ][
            :MAX_STORIES_PER_CATEGORY
        ]:

            lines.append(
                format_story_markdown(
                    story
                )
            )

            lines.append(
                "---"
            )

            lines.append("")

    return "\n".join(
        lines
    )


# ============================================================================
# HTML
# ============================================================================

def markdown_story_to_html(
    story: dict[str, Any],
) -> str:
    """Generate HTML for one story."""

    title = html.escape(
        story.get(
            "title",
            "Untitled",
        )
    )

    source = html.escape(
        story.get(
            "source",
            "Unknown source",
        )
    )

    url = html.escape(
        story.get(
            "url",
            "#",
        ),
        quote=True,
    )

    confidence = float(
        story.get(
            "category_confidence",
            0.0,
        )
        or 0.0
    )

    summary = html.escape(
        extractive_summary(
            story.get(
                "article_text"
            )
        )
    )

    return f"""
<article class="story">
    <h3>{title}</h3>

    <div class="metadata">
        <span>Source: {source}</span>
        <span>
            Classification confidence:
            {confidence * 100:.1f}%
        </span>
    </div>

    <p>{summary}</p>

    <a
        href="{url}"
        target="_blank"
        rel="noopener noreferrer"
    >
        Read original article →
    </a>
</article>
"""


def generate_html_digest(
    stories: list[dict[str, Any]],
) -> str:
    """Generate a standalone HTML digest."""

    grouped = group_by_category(
        stories
    )

    generated_at = datetime.now(
        timezone.utc
    ).strftime(
        "%d %B %Y, %H:%M UTC"
    )

    total_stories = sum(
        len(items)
        for items in grouped.values()
    )

    sections = []

    for category in CATEGORY_ORDER:

        category_stories = grouped.get(
            category,
            [],
        )

        if not category_stories:
            continue

        category_html = ""

        for story in category_stories[
            :MAX_STORIES_PER_CATEGORY
        ]:

            category_html += (
                markdown_story_to_html(
                    story
                )
            )

        sections.append(
            f"""
<section>
    <h2>{html.escape(category)}</h2>
    {category_html}
</section>
"""
        )

    return f"""<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>D-P1-22 News Intelligence Digest</title>

<style>

body {{
    font-family:
        Arial,
        Helvetica,
        sans-serif;

    max-width: 1000px;

    margin:
        0 auto;

    padding:
        40px 24px;

    background:
        #f5f6f8;

    color:
        #20242a;

    line-height:
        1.6;
}}

header {{
    background:
        #ffffff;

    padding:
        30px;

    margin-bottom:
        30px;

    border-radius:
        10px;

    border:
        1px solid #ddd;
}}

h1 {{
    margin-top:
        0;
}}

section {{
    margin-bottom:
        35px;
}}

section > h2 {{
    border-bottom:
        2px solid #222;

    padding-bottom:
        8px;
}}

.story {{
    background:
        #ffffff;

    padding:
        22px;

    margin:
        15px 0;

    border-radius:
        8px;

    border:
        1px solid #ddd;
}}

.story h3 {{
    margin-top:
        0;

    line-height:
        1.35;
}}

.metadata {{
    display:
        flex;

    gap:
        20px;

    flex-wrap:
        wrap;

    font-size:
        0.9rem;

    color:
        #666;

    margin-bottom:
        12px;
}}

.story a {{
    text-decoration:
        none;

    font-weight:
        bold;
}}

footer {{
    margin-top:
        40px;

    font-size:
        0.85rem;

    color:
        #666;
}}

</style>

</head>

<body>

<header>

<h1>D-P1-22 — News Intelligence Digest</h1>

<p>
<strong>Generated:</strong>
{generated_at}
</p>

<p>
<strong>Stories:</strong>
{total_stories}
</p>

<p>
Articles are grouped by the project's
categorisation taxonomy. Each story represents
a semantically clustered group of source articles.
</p>

</header>

{''.join(sections)}

<footer>

D-P1-22 — News Feed to Digest Pipeline<br>
Digital Media & Strategic Communication Internship Programme 2026

</footer>

</body>

</html>
"""


# ============================================================================
# SAVE OUTPUT
# ============================================================================

def save_digest(
    markdown: str,
    html_content: str,
) -> None:
    """Save Markdown and HTML versions."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    MARKDOWN_OUTPUT.write_text(
        markdown,
        encoding="utf-8",
    )

    HTML_OUTPUT.write_text(
        html_content,
        encoding="utf-8",
    )

    logger.info(
        "Markdown digest saved to: %s",
        MARKDOWN_OUTPUT,
    )

    logger.info(
        "HTML digest saved to: %s",
        HTML_OUTPUT,
    )


# ============================================================================
# MAIN
# ============================================================================

def run_digest_generation() -> None:
    """Run the digest-generation stage."""

    logger.info(
        "======================================================"
    )

    logger.info(
        "D-P1-22 — Digest Generation"
    )

    logger.info(
        "======================================================"
    )

    stories = load_stories()

    if not stories:

        logger.warning(
            "No categorized stories available."
        )

        return

    markdown = generate_markdown_digest(
        stories
    )

    html_content = generate_html_digest(
        stories
    )

    save_digest(
        markdown,
        html_content,
    )

    logger.info(
        "Digest generation completed successfully."
    )


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    run_digest_generation()