"""
ingestion/connectors/csv_connector.py
---------------------------------------
CSV file source connector.

Features
--------
- Uses csv.DictReader for row-by-row lazy extraction.
- Auto-detects delimiter (comma, tab, pipe, semicolon).
- Handles UTF-8 BOM markers transparently.
- Raises StructuralIngestionError on unreadable/malformed rows.
- Raises FatalIngestionError if the file does not exist.
"""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path
from typing import Any, Generator

from src.ingestion.p2_framework.connectors.base import BaseConnector
from src.ingestion.p2_framework.error_handling.exceptions import (
    FatalIngestionError,
    StructuralIngestionError,
)
from src.ingestion.p2_framework.schema import SourceType

logger = logging.getLogger("p2.connectors.csv")

# Delimiters to probe during auto-detection
_CANDIDATE_DELIMITERS = [",", "\t", "|", ";"]
_SNIFF_BYTES = 4096


class CSVConnector(BaseConnector):
    """
    Reads records from a CSV file and yields them as plain dicts.

    Parameters
    ----------
    file_path     : Path to the CSV file.
    entity_type   : Business entity name (e.g. 'customer').
    entity_id_field : Column that holds the primary/natural key.
    encoding      : File encoding (default: utf-8-sig to strip BOM).
    delimiter     : Override delimiter detection (None = auto-detect).
    """

    def __init__(
        self,
        file_path: str | Path,
        entity_type: str = "record",
        entity_id_field: str = "id",
        encoding: str = "utf-8-sig",
        delimiter: str | None = None,
    ) -> None:
        self._file_path = Path(file_path)
        self._encoding = encoding
        self._delimiter = delimiter
        self._file_handle: io.TextIOWrapper | None = None
        self._reader: csv.DictReader | None = None

        super().__init__(
            source_name=str(self._file_path),
            entity_type=entity_type,
            entity_id_field=entity_id_field,
        )

    # ── BaseConnector interface ───────────────────────────────────────────────

    def connect(self) -> None:
        if not self._file_path.exists():
            raise FatalIngestionError(
                message=f"CSV file not found: {self._file_path}",
                source=self.source_name,
            )
        delimiter = self._delimiter or self._detect_delimiter()
        self._file_handle = open(  # noqa: WPS515
            self._file_path, newline="", encoding=self._encoding
        )
        self._reader = csv.DictReader(self._file_handle, delimiter=delimiter)
        self._connected = True
        logger.info(
            "CSV connector connected",
            extra={"file": str(self._file_path), "delimiter": repr(delimiter)},
        )

    def extract(self) -> Generator[dict[str, Any], None, None]:
        if not self._connected or self._reader is None:
            raise FatalIngestionError(
                message="CSV connector not connected. Call connect() first.",
                source=self.source_name,
            )
        for row_num, row in enumerate(self._reader, start=2):  # header = row 1
            try:
                # csv.DictReader can produce None keys when a row has too many
                # columns — treat that as a structural error.
                if None in row:
                    raise StructuralIngestionError(
                        message=(
                            f"Row {row_num} has more columns than the header "
                            f"(extra values: {row[None]!r})."
                        ),
                        source=self.source_name,
                        raw_record=dict(row),
                    )
                # Strip whitespace from all string values
                clean = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
                yield clean
            except StructuralIngestionError:
                raise  # Let the engine handle DLQ routing
            except Exception as exc:
                raise StructuralIngestionError(
                    message=f"Unexpected error parsing row {row_num}: {exc}",
                    source=self.source_name,
                    raw_record=dict(row) if row else {},
                ) from exc

    def disconnect(self) -> None:
        if self._file_handle is not None:
            self._file_handle.close()
            self._file_handle = None
            self._reader = None
        self._connected = False
        logger.info("CSV connector disconnected", extra={"file": str(self._file_path)})

    def get_source_type(self) -> SourceType:
        return SourceType.CSV

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _detect_delimiter(self) -> str:
        """
        Sniff the delimiter from the first few KB of the file.
        Falls back to comma if detection fails.
        """
        try:
            with open(self._file_path, encoding=self._encoding, newline="") as fh:
                sample = fh.read(_SNIFF_BYTES)
            dialect = csv.Sniffer().sniff(sample, delimiters="".join(_CANDIDATE_DELIMITERS))
            logger.debug(
                "CSV delimiter auto-detected",
                extra={"delimiter": repr(dialect.delimiter)},
            )
            return dialect.delimiter
        except csv.Error:
            logger.debug(
                "CSV delimiter detection failed — defaulting to comma.",
                extra={"file": str(self._file_path)},
            )
            return ","
