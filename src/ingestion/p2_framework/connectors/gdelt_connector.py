"""
ingestion/connectors/gdelt_connector.py
-----------------------------------------
GDELT (Global Database of Events, Language & Tone) source connector.

GDELT monitors 100+ languages of news worldwide in real-time and scores
geopolitical events. The free DOC 2.0 API returns article-level data for
the last ~3 months — ideal for open-source intelligence (OSINT).

Source Type : CSV  (GDELT API returns CSV when format=CSV)
Entity Type : geopolitical_event
Auth        : None — completely free, no API key required
Docs        : https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

How it works
------------
1. Builds a GDELT DOC API URL from configured query topics.
2. Downloads the CSV response to a local cache file.
3. Delegates parsing to CSVConnector.
4. Cleans and enriches each row with topic tagging.
"""

from __future__ import annotations

import csv
import io
import logging
import time
from pathlib import Path
from typing import Any, Generator
from urllib.parse import urlencode

import requests

from src.ingestion.p2_framework.p2_config import (
    GDELT_API_BASE,
    GDELT_CSV_CACHE,
    GDELT_LANGUAGE,
    GDELT_MAX_RECORDS,
    GDELT_QUERY_TOPICS,
)
from src.ingestion.p2_framework.connectors.base import BaseConnector
from src.ingestion.p2_framework.error_handling.exceptions import (
    FatalIngestionError,
    StructuralIngestionError,
    TransientIngestionError,
)
from src.ingestion.p2_framework.schema import SourceType

logger = logging.getLogger("p2.connectors.gdelt")

# GDELT DOC API CSV column names (fixed schema)
_GDELT_CSV_COLUMNS = [
    "url", "url_mobile", "seendate", "title", "socialimage",
    "domain", "language", "sourcecountry",
]

# Seconds to wait between batched topic queries (respect GDELT informal limits)
_INTER_QUERY_DELAY = 2.0


class GDELTConnector(BaseConnector):
    """
    Fetches geopolitical event articles from the GDELT DOC 2.0 API.

    Makes one API call per configured query topic, merges all results,
    deduplicates by URL, and caches to a local CSV file for inspection.

    Parameters
    ----------
    query_topics  : List of search topics (OR'd together across calls).
    max_records   : Max articles per topic query (GDELT cap: 250).
    language      : Source language filter (default: 'english').
    cache_path    : Path to write the merged CSV cache.
    timeout       : HTTP request timeout in seconds.
    """

    def __init__(
        self,
        query_topics: list[str] | None = None,
        max_records: int = GDELT_MAX_RECORDS,
        language: str = GDELT_LANGUAGE,
        cache_path: Path | None = None,
        timeout: int = 5,
        use_cache_fallback: bool = True,
    ) -> None:
        self._query_topics = query_topics or GDELT_QUERY_TOPICS
        self._max_records  = min(max_records, 250)   # Hard GDELT cap
        self._language     = language
        self._cache_path   = cache_path or GDELT_CSV_CACHE
        self._timeout      = timeout
        self._use_cache_fallback = use_cache_fallback
        self._rows: list[dict[str, Any]] = []

        super().__init__(
            source_name="gdeltproject.org",
            entity_type="geopolitical_event",
            entity_id_field="url",
        )

    # ── BaseConnector interface ───────────────────────────────────────────────

    def connect(self) -> None:
        """
        Fetch articles for all query topics, merge, deduplicate,
        and write to the local CSV cache. Falls back to cached data if live
        API is unreachable or timing out.
        """
        all_rows: dict[str, dict[str, Any]] = {}  # keyed by URL for dedup
        consecutive_network_errors = 0

        for idx, topic in enumerate(self._query_topics):
            logger.info(
                "GDELT query",
                extra={
                    "topic": topic,
                    "query_num": f"{idx+1}/{len(self._query_topics)}",
                },
            )
            try:
                rows = self._fetch_topic(topic)
                consecutive_network_errors = 0
                for row in rows:
                    url = row.get("url", "")
                    if url and url not in all_rows:
                        row["query_topic"] = topic   # tag which topic found it
                        all_rows[url] = row
                logger.info(
                    "GDELT topic fetched",
                    extra={"topic": topic, "articles": len(rows), "total_unique": len(all_rows)},
                )
            except FatalIngestionError:
                raise
            except Exception as exc:
                consecutive_network_errors += 1
                logger.warning(
                    "GDELT topic query failed — skipping",
                    extra={"topic": topic, "error": str(exc)},
                )
                # If network is unresponsive for consecutive queries, don't hang for minutes
                if consecutive_network_errors >= 2 and not all_rows:
                    logger.warning(
                        "GDELT live endpoint unreachable — switching to local cache fallback"
                    )
                    break

            # Respect GDELT's informal rate limit
            if idx < len(self._query_topics) - 1:
                time.sleep(_INTER_QUERY_DELAY)

        if not all_rows:
            if self._use_cache_fallback and self._cache_path and self._cache_path.exists():
                logger.warning(
                    "GDELT live query returned zero articles; loading from local CSV cache",
                    extra={"cache_path": str(self._cache_path)},
                )
                cached_rows = self._read_cache()
                if cached_rows:
                    self._rows = cached_rows
                    self._connected = True
                    logger.info(
                        "GDELT connector loaded cached records",
                        extra={"total_unique_articles": len(self._rows), "cache": str(self._cache_path)},
                    )
                    return

            raise FatalIngestionError(
                message="GDELT returned zero articles across all query topics.",
                source=self.source_name,
            )

        self._rows = list(all_rows.values())
        self._write_cache()
        self._connected = True
        logger.info(
            "GDELT connector connected",
            extra={"total_unique_articles": len(self._rows)},
        )

    def extract(self) -> Generator[dict[str, Any], None, None]:
        if not self._connected:
            raise FatalIngestionError(
                message="GDELTConnector not connected. Call connect() first.",
                source=self.source_name,
            )
        for row in self._rows:
            yield self._clean_row(row)

    def disconnect(self) -> None:
        self._rows = []
        self._connected = False
        logger.info(
            "GDELT connector disconnected",
            extra={"cache": str(self._cache_path)},
        )

    def get_source_type(self) -> SourceType:
        return SourceType.CSV

    # ── Private helpers ───────────────────────────────────────────────────────

    def _fetch_topic(self, topic: str) -> list[dict[str, Any]]:
        """
        Fetch articles for a single topic from the GDELT DOC 2.0 API.
        Returns a list of row dicts.
        """
        params = {
            "query":        f'"{topic}" sourcelang:{self._language}',
            "mode":         "ArtList",
            "maxrecords":   self._max_records,
            "format":       "CSV",
        }
        url = f"{GDELT_API_BASE}?{urlencode(params)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/csv,text/plain,*/*",
        }
        logger.debug("GDELT request URL", extra={"url": url})

        try:
            resp = requests.get(url, headers=headers, timeout=self._timeout)
        except requests.exceptions.Timeout as exc:
            raise TransientIngestionError(
                message=f"GDELT request timed out for topic={topic!r}",
                source=self.source_name,
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise TransientIngestionError(
                message=f"GDELT connection error for topic={topic!r}: {exc}",
                source=self.source_name,
            ) from exc

        if resp.status_code != 200:
            raise FatalIngestionError(
                message=f"GDELT returned HTTP {resp.status_code} for topic={topic!r}",
                source=self.source_name,
            )

        content = resp.text.strip()
        if not content:
            logger.warning("GDELT returned empty response", extra={"topic": topic})
            return []

        # Parse CSV response
        rows = []
        reader = csv.reader(io.StringIO(content))
        for line in reader:
            if not line or len(line) < 4:
                continue
            # Skip header line if present
            first_col = line[0].lstrip("\ufeff").strip().lower()
            if first_col == "url":
                continue
            # Pad or trim to expected column count
            padded = (line + [""] * len(_GDELT_CSV_COLUMNS))[: len(_GDELT_CSV_COLUMNS)]
            rows.append(dict(zip(_GDELT_CSV_COLUMNS, padded)))
        return rows

    def _read_cache(self) -> list[dict[str, Any]]:
        """Read fallback articles from local CSV cache."""
        if not self._cache_path or not self._cache_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        with open(self._cache_path, "r", encoding="utf-8-sig", errors="replace") as fh:
            reader = csv.DictReader(fh)
            for raw_row in reader:
                if not raw_row:
                    continue
                url = (raw_row.get("url") or raw_row.get("URL") or "").strip()
                if not url or url.lower() in ("url", "mobileurl") or not url.startswith("http"):
                    continue
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                # Standardize column keys
                std_row: dict[str, Any] = {
                    "url": url,
                    "url_mobile": (raw_row.get("url_mobile") or raw_row.get("MobileURL") or "").strip(),
                    "seendate": (raw_row.get("seendate") or raw_row.get("Date") or "").strip(),
                    "title": (raw_row.get("title") or raw_row.get("Title") or "").strip(),
                    "socialimage": (raw_row.get("socialimage") or raw_row.get("Image") or "").strip(),
                    "domain": (raw_row.get("domain") or raw_row.get("Domain") or "").strip(),
                    "language": (raw_row.get("language") or raw_row.get("Language") or "English").strip(),
                    "sourcecountry": (raw_row.get("sourcecountry") or raw_row.get("SourceCountry") or "").strip(),
                    "query_topic": (raw_row.get("query_topic") or "Indian Army").strip(),
                }
                rows.append(std_row)
        return rows

    def _clean_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """Normalise GDELT row fields."""
        # Parse seendate: YYYYMMDDTHHMMSSZ -> readable
        raw_date = row.get("seendate", "")
        if raw_date and len(raw_date) >= 15 and "T" in raw_date:
            try:
                row["seendate"] = (
                    f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                    f"T{raw_date[9:11]}:{raw_date[11:13]}:{raw_date[13:15]}Z"
                )
            except Exception:
                pass  # Keep original if parsing fails
        return row

    def _write_cache(self) -> None:
        """Write the merged deduplicated rows to the local CSV cache file."""
        if not self._rows:
            return
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(self._rows[0].keys())
        with open(self._cache_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(self._rows)
        logger.debug(
            "GDELT cache written",
            extra={"path": str(self._cache_path), "rows": len(self._rows)},
        )
