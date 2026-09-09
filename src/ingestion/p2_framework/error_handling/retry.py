"""
ingestion/error_handling/retry.py
-----------------------------------
Tenacity-powered retry decorator for transient ingestion failures.

Usage
-----
    from src.ingestion.p2_framework.error_handling.retry import transient_retry

    @transient_retry
    def fetch_page(url: str) -> dict:
        ...
"""

from __future__ import annotations

import logging

import requests
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.ingestion.p2_framework.p2_config import (
    RETRY_MAX_ATTEMPTS,
    RETRY_WAIT_MAX_SECONDS,
    RETRY_WAIT_MIN_SECONDS,
    RETRY_WAIT_MULTIPLIER,
)
from src.ingestion.p2_framework.error_handling.exceptions import FatalIngestionError, TransientIngestionError

logger = logging.getLogger("p2.retry")


# ──────────────────────────────────────────────────────────────────────────────
# Retry callbacks
# ──────────────────────────────────────────────────────────────────────────────

def _before_sleep_log(retry_state: RetryCallState) -> None:
    """Log each retry attempt with wait duration before sleeping."""
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    logger.warning(
        "Transient error — retrying",
        extra={
            "attempt": retry_state.attempt_number,
            "next_wait_seconds": round(retry_state.next_action.sleep, 2) if retry_state.next_action else 0,
            "exception": repr(exc),
            "function": retry_state.fn.__name__ if retry_state.fn else "unknown",
        },
    )


def _after_exhaustion_log(retry_state: RetryCallState) -> None:
    """Called when all retries are exhausted — convert to FatalIngestionError."""
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    logger.error(
        "All retry attempts exhausted — raising FatalIngestionError",
        extra={
            "total_attempts": retry_state.attempt_number,
            "final_exception": repr(exc),
        },
    )
    raise FatalIngestionError(
        message=(
            f"All {RETRY_MAX_ATTEMPTS} retry attempts exhausted. "
            f"Last error: {exc}"
        ),
        source="retry",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Public decorator
# ──────────────────────────────────────────────────────────────────────────────

transient_retry = retry(
    retry=retry_if_exception_type(
        (
            TransientIngestionError,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
        )
    ),
    wait=wait_exponential(
        multiplier=RETRY_WAIT_MULTIPLIER,
        min=RETRY_WAIT_MIN_SECONDS,
        max=RETRY_WAIT_MAX_SECONDS,
    ),
    stop=stop_after_attempt(RETRY_MAX_ATTEMPTS),
    before_sleep=_before_sleep_log,
    retry_error_callback=_after_exhaustion_log,
    reraise=False,
)
"""
Decorator that wraps a callable with exponential-backoff retry logic.

Retries on:
  - TransientIngestionError
  - requests.exceptions.Timeout
  - requests.exceptions.ConnectionError
  - requests.exceptions.ChunkedEncodingError

After RETRY_MAX_ATTEMPTS failures, raises FatalIngestionError.
"""
