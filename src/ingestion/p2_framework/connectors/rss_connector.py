"""
ingestion/connectors/rss_connector.py
---------------------------------------
Defence RSS feed connector — treated as the JSON source type.

Reads multiple RSS/Atom feed URLs using feedparser, yielding one
dict per article. Each record is tagged with its source feed name.

Source Type : JSON  (RSS is structured data yielded as dicts)
Entity Type : defence_news
Auth        : None — all feeds are publicly accessible

Feed sources (configured in config.py):
  - idrw.org               Indian Defence Research Wing
  - nationaldefence.in     National Defence India
  - broadsword             Ajai Shukla (leading Indian defence analyst)
  - thehindu_national      The Hindu National section
  - thewire                The Wire security/geopolitics coverage
  - defenceaviation        Defence Aviation India
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Generator

import feedparser
import requests

from src.ingestion.p2_framework.p2_config import (
    RSS_FEED_URLS,
    RSS_MAX_ITEMS_PER_FEED,
    RSS_TIMEOUT_SECONDS,
)
from src.ingestion.p2_framework.connectors.base import BaseConnector
from src.ingestion.p2_framework.error_handling.exceptions import FatalIngestionError
from src.ingestion.p2_framework.schema import SourceType

logger = logging.getLogger("p2.connectors.rss")


class RSSConnector(BaseConnector):
    """
    Fetches and parses multiple RSS/Atom feeds, yielding one record
    per article across all feeds.

    Parameters
    ----------
    feed_urls     : List of (name, url) tuples for RSS feeds to fetch.
    max_per_feed  : Max articles to yield per feed (prevents runaway).
    timeout       : HTTP timeout per feed fetch.
    """

    def __init__(
        self,
        feed_urls: list[tuple[str, str]] | None = None,
        max_per_feed: int = RSS_MAX_ITEMS_PER_FEED,
        timeout: int = RSS_TIMEOUT_SECONDS,
    ) -> None:
        self._feed_urls  = feed_urls or RSS_FEED_URLS
        self._max_per_feed = max_per_feed
        self._timeout    = timeout
        self._feed_data: list[tuple[str, feedparser.FeedParserDict]] = []

        super().__init__(
            source_name="rss_defence_feeds",
            entity_type="defence_news",
            entity_id_field="link",
        )

    # ── BaseConnector interface ───────────────────────────────────────────────

    def connect(self) -> None:
        """
        Pre-fetch all configured RSS feeds. Feeds that fail to load
        are logged as warnings and skipped — other feeds still process.
        """
        loaded = 0
        for feed_name, feed_url in self._feed_urls:
            try:
                raw = self._fetch_feed(feed_name, feed_url)
                if raw is not None:
                    self._feed_data.append((feed_name, raw))
                    loaded += 1
            except Exception as exc:
                logger.warning(
                    "RSS feed skipped due to fetch error",
                    extra={"feed": feed_name, "url": feed_url, "error": str(exc)},
                )

        if loaded == 0:
            raise FatalIngestionError(
                message="All RSS feeds failed to load. Check network connectivity.",
                source=self.source_name,
            )

        self._connected = True
        logger.info(
            "RSS connector connected",
            extra={"feeds_loaded": loaded, "feeds_total": len(self._feed_urls)},
        )

    def extract(self) -> Generator[dict[str, Any], None, None]:
        if not self._connected:
            raise FatalIngestionError(
                message="RSSConnector not connected. Call connect() first.",
                source=self.source_name,
            )
        for feed_name, parsed_feed in self._feed_data:
            entries = parsed_feed.get("entries", [])
            count = 0
            for entry in entries:
                if count >= self._max_per_feed:
                    break
                record = self._entry_to_dict(entry, feed_name)
                if record:
                    yield record
                    count += 1
            logger.debug(
                "RSS feed extracted",
                extra={"feed": feed_name, "articles_yielded": count},
            )

    def disconnect(self) -> None:
        self._feed_data = []
        self._connected = False
        logger.info("RSS connector disconnected")

    def get_source_type(self) -> SourceType:
        return SourceType.JSON   # RSS treated as structured JSON source

    # ── Private helpers ───────────────────────────────────────────────────────

    def _fetch_feed(
        self,
        feed_name: str,
        feed_url: str,
    ) -> feedparser.FeedParserDict | None:
        """
        Download and parse a single RSS/Atom feed.
        feedparser handles XML parsing and normalises Atom/RSS differences.
        """
        logger.info(
            "Fetching RSS feed",
            extra={"feed": feed_name, "url": feed_url},
        )
        try:
            # Use requests to get the raw content (better timeout control)
            resp = requests.get(
                feed_url,
                timeout=self._timeout,
                headers={"User-Agent": "DefenceIntelBot/2.0 (research; contact@example.com)"},
            )
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
        except requests.exceptions.RequestException as exc:
            # Try feedparser's own fetcher as fallback
            logger.debug(
                "requests fetch failed, trying feedparser direct",
                extra={"feed": feed_name, "error": str(exc)},
            )
            parsed = feedparser.parse(feed_url)

        if parsed.get("bozo") and not parsed.get("entries"):
            logger.warning(
                "RSS feed parse error (bozo)",
                extra={
                    "feed": feed_name,
                    "bozo_exception": str(parsed.get("bozo_exception", "unknown")),
                },
            )
            return None

        entry_count = len(parsed.get("entries", []))
        logger.info(
            "RSS feed fetched",
            extra={"feed": feed_name, "entries": entry_count},
        )
        return parsed

    def _entry_to_dict(
        self,
        entry: Any,
        feed_name: str,
    ) -> dict[str, Any] | None:
        """
        Convert a feedparser entry object to a plain dict.
        Returns None if the entry has no meaningful content.
        """
        def _get(obj: Any, key: str, default: Any = "") -> Any:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        title   = _get(entry, "title", "") or ""
        link    = _get(entry, "link", "") or ""
        summary = _get(entry, "summary", "") or _get(entry, "description", "") or ""
        author  = _get(entry, "author", "") or ""

        # Tags/categories
        tags = []
        raw_tags = _get(entry, "tags", []) or []
        for tag in raw_tags:
            term = _get(tag, "term", None) if isinstance(tag, (dict, object)) else str(tag)
            if term:
                tags.append(str(term).strip())

        # Published datetime
        published_parsed = _get(entry, "published_parsed", None)
        if published_parsed:
            try:
                published = datetime(*published_parsed[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                published = str(published_parsed)
        else:
            published = _get(entry, "published", "") or datetime.now(timezone.utc).isoformat()

        if not title and not link:
            return None   # Skip empty entries

        # Stable ID from URL hash (handles missing guids)
        entity_id = link or hashlib.md5(f"{title}{published}".encode()).hexdigest()

        return {
            "id":          entity_id,
            "title":       title.strip(),
            "summary":     _strip_html(summary[:500]),   # Truncate long summaries
            "link":        link,
            "author":      author,
            "published":   published,
            "source_feed": feed_name,
            "tags":        tags,
        }


# ── Utility ───────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    """Remove basic HTML tags from RSS summary text."""
    import re
    clean = re.sub(r"<[^>]+>", " ", text)
    return " ".join(clean.split())
