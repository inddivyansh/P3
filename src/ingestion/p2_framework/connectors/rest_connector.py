"""
ingestion/connectors/rest_connector.py
----------------------------------------
REST API source connector with pagination support and retry logic.

Features
--------
- Persistent requests.Session for connection reuse.
- Tenacity exponential-backoff retry on 5xx / network errors.
- Pagination: follows `next` / configurable next-page key in response.
- Supports Bearer token and custom header auth.
- Raises TransientIngestionError on 5xx/timeout (will be retried).
- Raises FatalIngestionError on 4xx auth errors (401, 403).
"""

from __future__ import annotations

import logging
from typing import Any, Generator

import requests

from src.ingestion.p2_framework.connectors.base import BaseConnector
from src.ingestion.p2_framework.error_handling.exceptions import (
    FatalIngestionError,
    StructuralIngestionError,
    TransientIngestionError,
)
from src.ingestion.p2_framework.error_handling.retry import transient_retry
from src.ingestion.p2_framework.schema import SourceType

logger = logging.getLogger("p2.connectors.rest")

# HTTP status codes that should NOT be retried
_FATAL_STATUS_CODES = {400, 401, 403, 404, 410}


class RESTConnector(BaseConnector):
    """
    Fetches records from a paginated REST API endpoint.

    Parameters
    ----------
    url             : Base URL of the API endpoint.
    entity_type     : Business entity name (e.g. 'user').
    entity_id_field : JSON key that holds the natural primary key.
    headers         : Optional dict of request headers (auth, content-type).
    params          : Optional dict of default query params.
    data_key        : Key in the response JSON that holds the records list.
                      If None, assumes the response itself is a list.
    next_page_key   : Key in the response JSON holding the next-page URL.
                      Set to None to disable pagination (default: None).
    timeout         : Request timeout in seconds (default: 30).
    """

    def __init__(
        self,
        url: str,
        entity_type: str = "record",
        entity_id_field: str = "id",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        data_key: str | None = None,
        next_page_key: str | None = None,
        timeout: int = 30,
    ) -> None:
        self._url = url
        self._headers = headers or {}
        self._params = params or {}
        self._data_key = data_key
        self._next_page_key = next_page_key
        self._timeout = timeout
        self._session: requests.Session | None = None

        super().__init__(
            source_name=url,
            entity_type=entity_type,
            entity_id_field=entity_id_field,
        )

    # ── BaseConnector interface ───────────────────────────────────────────────

    def connect(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(self._headers)
        self._connected = True
        logger.info("REST connector session opened", extra={"url": self._url})

    def extract(self) -> Generator[dict[str, Any], None, None]:
        if not self._connected or self._session is None:
            raise FatalIngestionError(
                message="REST connector not connected. Call connect() first.",
                source=self.source_name,
            )
        current_url: str | None = self._url
        page = 0
        while current_url:
            page += 1
            logger.debug("Fetching REST page", extra={"url": current_url, "page": page})
            response_data = self._fetch_page(current_url)
            records = self._extract_records(response_data)
            for record in records:
                yield record
            current_url = self._get_next_url(response_data)

    def disconnect(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None
        self._connected = False
        logger.info("REST connector session closed", extra={"url": self._url})

    def get_source_type(self) -> SourceType:
        return SourceType.REST

    # ── Private helpers ───────────────────────────────────────────────────────

    @transient_retry
    def _fetch_page(self, url: str) -> Any:
        """
        Perform a single HTTP GET and return the parsed JSON.
        Decorated with @transient_retry for automatic exponential backoff.
        """
        try:
            response = self._session.get(  # type: ignore[union-attr]
                url,
                params=self._params,
                timeout=self._timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise TransientIngestionError(
                message=f"Request timed out after {self._timeout}s: {url}",
                source=self.source_name,
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise TransientIngestionError(
                message=f"Connection error fetching {url}: {exc}",
                source=self.source_name,
            ) from exc

        status = response.status_code
        if status in _FATAL_STATUS_CODES:
            raise FatalIngestionError(
                message=f"Fatal HTTP {status} from {url} — not retrying.",
                source=self.source_name,
            )
        if status == 429:
            raise TransientIngestionError(
                message=f"HTTP 429 Rate limited by {url}",
                source=self.source_name,
            )
        if status >= 500:
            raise TransientIngestionError(
                message=f"HTTP {status} server error from {url}",
                source=self.source_name,
            )
        response.raise_for_status()

        try:
            return response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise StructuralIngestionError(
                message=f"Response from {url} is not valid JSON: {exc}",
                source=self.source_name,
            ) from exc

    def _extract_records(self, data: Any) -> list[dict[str, Any]]:
        """
        Pull the list of records out of the response payload.
        Uses `data_key` if set; otherwise expects the root to be a list.
        """
        if self._data_key:
            if not isinstance(data, dict) or self._data_key not in data:
                raise StructuralIngestionError(
                    message=(
                        f"Response missing expected data_key={self._data_key!r}. "
                        f"Got keys: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}"
                    ),
                    source=self.source_name,
                )
            records = data[self._data_key]
        else:
            records = data

        if not isinstance(records, list):
            raise StructuralIngestionError(
                message=f"Expected a list of records, got {type(records).__name__}.",
                source=self.source_name,
            )
        return records

    def _get_next_url(self, data: Any) -> str | None:
        """Extract the next-page URL from the response if pagination is configured."""
        if self._next_page_key is None or not isinstance(data, dict):
            return None
        return data.get(self._next_page_key)
