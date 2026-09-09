"""
ingestion/error_handling/exceptions.py
----------------------------------------
Custom exception hierarchy for the ingestion framework.

Error taxonomy
--------------
IngestionBaseError
├── TransientIngestionError    Retriable — network timeout, server 5xx, rate limit
├── StructuralIngestionError   Non-retriable — malformed CSV row, bad JSON syntax
├── ValidationIngestionError   Non-retriable — record fails Pydantic schema validation
└── FatalIngestionError        Pipeline-aborting — auth failure, missing connector config
"""


class IngestionBaseError(Exception):
    """
    Base class for all ingestion framework errors.

    Parameters
    ----------
    message    : Human-readable description of the error.
    source     : The connector/source name where the error occurred.
    raw_record : The offending raw record dict (if available).
    """

    def __init__(
        self,
        message: str,
        source: str = "unknown",
        raw_record: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.source = source
        self.raw_record = raw_record or {}

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"source={self.source!r}, "
            f"message={self.message!r})"
        )


class TransientIngestionError(IngestionBaseError):
    """
    A temporary failure that is safe to retry.

    Examples
    --------
    - HTTP 500 / 503 from REST API
    - Network connection timeout
    - Database connection dropped mid-stream
    - API rate-limit (HTTP 429)
    """


class StructuralIngestionError(IngestionBaseError):
    """
    The raw data itself is malformed and cannot be parsed.
    The record is routed to the Dead-Letter Queue; the pipeline continues.

    Examples
    --------
    - CSV row with wrong number of columns
    - JSON that cannot be decoded (syntax error)
    - Binary file where text was expected
    """


class ValidationIngestionError(IngestionBaseError):
    """
    The parsed record fails Pydantic schema validation.
    The record is routed to the Dead-Letter Queue; the pipeline continues.

    Examples
    --------
    - Required field `entity_id` is None
    - `payload` is empty dict
    - Field value fails type coercion
    """

    def __init__(
        self,
        message: str,
        source: str = "unknown",
        raw_record: dict | None = None,
        pydantic_errors: list | None = None,
    ) -> None:
        super().__init__(message, source, raw_record)
        self.pydantic_errors = pydantic_errors or []


class FatalIngestionError(IngestionBaseError):
    """
    An unrecoverable error that should abort the current connector run.
    All remaining retries have been exhausted, or the error is inherently
    non-retriable (e.g. wrong credentials, missing file).

    Examples
    --------
    - HTTP 401 / 403 from REST API (auth failure)
    - Source file does not exist
    - Database table not found
    - All retry attempts exhausted
    """
