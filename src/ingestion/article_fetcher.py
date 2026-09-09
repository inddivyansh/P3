"""Article page retrieval and full-text extraction using requests + trafilatura."""
"""
D-P1-22 — News Feed to Digest Pipeline

Article full-text extraction module.

Responsibilities:
    1. Read articles collected by feed_reader
    2. Fetch article webpages
    3. Extract clean article text using Trafilatura
    4. Preserve the original feed metadata
    5. Save processed articles

This module does NOT:
    - classify articles
    - perform semantic deduplication
    - generate the digest
"""

import json
import logging
from pathlib import Path
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests
from requests.adapters import HTTPAdapter
import trafilatura
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "articles.json"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "articles.json"
DATABASE_FILE = PROJECT_ROOT / "data" / "database" / "news_pipeline.db"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

# Suppress noisy internal scraper errors
logging.getLogger("trafilatura").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("requests").setLevel(logging.CRITICAL)

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Thread-local storage for connection-pooled requests sessions
_thread_local = threading.local()


def _get_session() -> requests.Session:
    """Return a thread-local requests.Session with connection pooling and retries."""
    if not hasattr(_thread_local, "session"):
        session = requests.Session()
        retry_strategy = Retry(
            total=1,
            backoff_factor=0.2,
            status_forcelist=[502, 503, 504],
        )
        adapter = HTTPAdapter(
            pool_connections=25,
            pool_maxsize=25,
            max_retries=retry_strategy,
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update(BROWSER_HEADERS)
        _thread_local.session = session
    return _thread_local.session


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def load_cached_texts(db_path: Path = DATABASE_FILE) -> dict[str, str]:
    """Load pre-extracted article texts from SQLite to avoid re-downloading."""
    if not db_path.exists():
        return {}
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT article_id, article_text FROM articles WHERE article_text IS NOT NULL AND LENGTH(article_text) > 50"
        )
        cached = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return cached
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Load articles
# ---------------------------------------------------------------------------

def load_articles(
    input_path: Path = INPUT_FILE,
) -> list[dict[str, Any]]:
    """Load articles produced by the feed ingestion stage."""

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}\n"
            "Run feed_reader.py first."
        )

    with input_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        articles = data
    elif isinstance(data, dict):
        articles = data.get("articles", [])
    else:
        raise ValueError("Invalid articles.json format.")

    if not isinstance(articles, list):
        raise ValueError(
            "Invalid articles.json format: articles must be a list."
        )

    logger.info(
        "Loaded %d article(s)",
        len(articles),
    )

    return articles


# ---------------------------------------------------------------------------
# Article extraction
# ---------------------------------------------------------------------------

def extract_article_text(url: str, fallback_summary: str = "") -> tuple[str | None, str]:
    """
    Download an article and extract its main text using Trafilatura.
    Falls back to RSS summary if webpage extraction or paywall blocks access.

    Returns:
        tuple (clean_text, method_used)
    """
    session = _get_session()

    try:
        resp = session.get(url, timeout=(3.0, 5.0), allow_redirects=True)
        if resp.status_code == 200 and resp.text:
            text = trafilatura.extract(
                resp.text,
                include_comments=False,
                include_tables=False,
                include_links=False,
                include_images=False,
                favor_precision=True,
            )
            if text and len(text.strip()) > 50:
                return text.strip(), "Extracted"
        elif resp.status_code in (401, 403, 404, 410, 500):
            # Fast fail on hard HTTP client/server errors
            if fallback_summary and len(fallback_summary.strip()) > 20:
                return fallback_summary.strip(), "Fallback-Summary"
            return None, "Failed"
    except Exception:
        pass

    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                include_links=False,
                include_images=False,
                favor_precision=True,
            )
            if text and len(text.strip()) > 50:
                return text.strip(), "Extracted"
    except Exception:
        pass

    if fallback_summary and len(fallback_summary.strip()) > 20:
        return fallback_summary.strip(), "Fallback-Summary"

    return None, "Failed"


# ---------------------------------------------------------------------------
# Process articles (Multi-threaded & Cached)
# ---------------------------------------------------------------------------

def process_articles(
    articles: list[dict[str, Any]],
    max_workers: int = 20,
) -> list[dict[str, Any]]:
    """
    Extract full text from every article using multi-threaded execution
    and database caching.
    """
    cached_texts = load_cached_texts()
    total = len(articles)
    logger.info(
        "Starting parallel extraction for %d articles (%d workers, %d pre-cached in DB)...",
        total,
        max_workers,
        len(cached_texts),
    )

    results: list[dict[str, Any] | None] = [None] * total
    successful = 0
    cached_count = 0
    failed = 0
    completed_counter = 0
    lock = threading.Lock()

    def process_single(item_tuple: tuple[int, dict[str, Any]]):
        nonlocal completed_counter, successful, cached_count, failed
        index, article = item_tuple
        url = article.get("url")
        article_id = article.get("article_id")
        title = (article.get("title") or "Untitled")[:65]
        source = article.get("source") or "Feed"

        if not url:
            with lock:
                completed_counter += 1
                failed += 1
                logger.warning(
                    "[%d/%d] Skipped (no URL) | %s | %s",
                    completed_counter,
                    total,
                    source,
                    title,
                )
            processed_article = dict(article)
            processed_article["article_text"] = None
            processed_article["text_length"] = 0
            return index, processed_article

        # 1. Fast Cache Check
        if article_id and article_id in cached_texts:
            cached_text = cached_texts[article_id]
            processed_article = dict(article)
            processed_article["article_text"] = cached_text
            processed_article["text_length"] = len(cached_text)
            with lock:
                completed_counter += 1
                cached_count += 1
                successful += 1
                logger.info(
                    "[%d/%d] Cached (%d chars) | %s | %s",
                    completed_counter,
                    total,
                    len(cached_text),
                    source,
                    title,
                )
            return index, processed_article

        # 2. Parallel Network Extraction
        summary_fallback = article.get("summary") or article.get("title") or ""
        article_text, method = extract_article_text(url, fallback_summary=summary_fallback)

        processed_article = dict(article)
        processed_article["article_text"] = article_text
        text_len = len(article_text) if article_text else 0
        processed_article["text_length"] = text_len

        with lock:
            completed_counter += 1
            if article_text:
                successful += 1
                logger.info(
                    "[%d/%d] %s (%d chars) | %s | %s",
                    completed_counter,
                    total,
                    method,
                    text_len,
                    source,
                    title,
                )
            else:
                failed += 1
                logger.warning(
                    "[%d/%d] Extraction failed/empty | %s | %s",
                    completed_counter,
                    total,
                    source,
                    title,
                )

        return index, processed_article

    # Run in parallel with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_single, (i, art))
            for i, art in enumerate(articles)
        ]
        for future in as_completed(futures):
            idx, res = future.result()
            results[idx] = res

    processed_articles = [r for r in results if r is not None]

    logger.info(
        "Extraction complete | total=%d | successful=%d (cached=%d, fetched=%d) | failed=%d",
        total,
        successful,
        cached_count,
        successful - cached_count,
        failed,
    )

    return processed_articles


# ---------------------------------------------------------------------------
# Save processed articles
# ---------------------------------------------------------------------------

def save_articles(
    articles: list[dict[str, Any]],
    output_path: Path = OUTPUT_FILE,
) -> None:
    """Save processed articles to JSON."""

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
        "Saved processed articles to %s",
        output_path,
    )


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------

def run_article_extraction() -> list[dict[str, Any]]:
    """Run the complete article extraction stage."""

    articles = load_articles()

    processed_articles = process_articles(
        articles
    )

    save_articles(
        processed_articles
    )

    return processed_articles


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_article_extraction()