"""
ingestion/connectors/json_connector.py
----------------------------------------
JSON file source connector.

Supports two JSON layouts:
  1. JSON Array  — [ {...}, {...}, ... ]
  2. JSON Lines  — one JSON object per line (`.jsonl` or `.ndjson`)

Features
--------
- Lazy loading: streams JSON Lines without reading the whole file.
- Nested flattening: optionally flattens nested dicts up to `max_depth` levels.
- Raises StructuralIngestionError on JSON parse failures (per-record).
- Raises FatalIngestionError if the file does not exist.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Generator

from src.ingestion.p2_framework.connectors.base import BaseConnector
from src.ingestion.p2_framework.error_handling.exceptions import (
    FatalIngestionError,
    StructuralIngestionError,
)
from src.ingestion.p2_framework.schema import SourceType

logger = logging.getLogger("p2.connectors.json")


class JSONConnector(BaseConnector):
    """
    Reads records from a JSON array file or JSON Lines file.

    Parameters
    ----------
    file_path       : Path to the JSON / JSONL file.
    entity_type     : Business entity name (e.g. 'order').
    entity_id_field : Key holding the natural primary key.
    flatten         : If True, flatten nested dicts (default True).
    max_depth       : Max flattening depth (default 1).
    """

    def __init__(
        self,
        file_path: str | Path,
        entity_type: str = "record",
        entity_id_field: str = "id",
        flatten: bool = True,
        max_depth: int = 1,
    ) -> None:
        self._file_path = Path(file_path)
        self._flatten = flatten
        self._max_depth = max_depth
        self._data: list[dict[str, Any]] | None = None  # for array mode
        self._mode: str = "unknown"  # "array" or "lines"

        super().__init__(
            source_name=str(self._file_path),
            entity_type=entity_type,
            entity_id_field=entity_id_field,
        )

    # ── BaseConnector interface ───────────────────────────────────────────────

    def connect(self) -> None:
        if not self._file_path.exists():
            raise FatalIngestionError(
                message=f"JSON file not found: {self._file_path}",
                source=self.source_name,
            )
        # Peek at the first non-whitespace character to determine layout
        with open(self._file_path, encoding="utf-8") as fh:
            first_char = ""
            while True:
                ch = fh.read(1)
                if not ch:
                    break
                if ch.strip():
                    first_char = ch
                    break

        if first_char == "[":
            # Array mode — load fully into memory (acceptable for typical files)
            self._mode = "array"
            try:
                with open(self._file_path, encoding="utf-8") as fh:
                    self._data = json.load(fh)
                if not isinstance(self._data, list):
                    raise FatalIngestionError(
                        message="JSON file root is not an array.",
                        source=self.source_name,
                    )
            except json.JSONDecodeError as exc:
                raise FatalIngestionError(
                    message=f"Failed to parse JSON array file: {exc}",
                    source=self.source_name,
                ) from exc
        elif first_char == "{":
            # JSON Lines mode — stream line by line
            self._mode = "lines"
        else:
            raise FatalIngestionError(
                message=f"Unexpected JSON file format (first char={first_char!r}).",
                source=self.source_name,
            )

        self._connected = True
        logger.info(
            "JSON connector connected",
            extra={"file": str(self._file_path), "mode": self._mode},
        )

    def extract(self) -> Generator[dict[str, Any], None, None]:
        if not self._connected:
            raise FatalIngestionError(
                message="JSON connector not connected. Call connect() first.",
                source=self.source_name,
            )
        if self._mode == "array":
            yield from self._extract_array()
        else:
            yield from self._extract_lines()

    def disconnect(self) -> None:
        self._data = None
        self._connected = False
        logger.info("JSON connector disconnected", extra={"file": str(self._file_path)})

    def get_source_type(self) -> SourceType:
        return SourceType.JSON

    # ── Private extraction helpers ────────────────────────────────────────────

    def _extract_array(self) -> Generator[dict[str, Any], None, None]:
        for idx, item in enumerate(self._data):  # type: ignore[union-attr]
            if not isinstance(item, dict):
                raise StructuralIngestionError(
                    message=f"Array item [{idx}] is not a dict: {type(item).__name__}",
                    source=self.source_name,
                    raw_record={"index": idx, "value": str(item)},
                )
            record = self._maybe_flatten(item)
            yield record

    def _extract_lines(self) -> Generator[dict[str, Any], None, None]:
        with open(self._file_path, encoding="utf-8") as fh:
            for line_num, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    if not isinstance(item, dict):
                        raise StructuralIngestionError(
                            message=f"Line {line_num} is not a JSON object.",
                            source=self.source_name,
                            raw_record={"line_number": line_num, "content": line[:200]},
                        )
                    yield self._maybe_flatten(item)
                except json.JSONDecodeError as exc:
                    raise StructuralIngestionError(
                        message=f"JSON parse error on line {line_num}: {exc}",
                        source=self.source_name,
                        raw_record={"line_number": line_num, "content": line[:200]},
                    ) from exc

    def _maybe_flatten(self, record: dict[str, Any]) -> dict[str, Any]:
        """Optionally flatten nested dicts using dot-notation keys."""
        if not self._flatten:
            return record
        return _flatten_dict(record, max_depth=self._max_depth)


# ── Module-level flatten utility ──────────────────────────────────────────────

def _flatten_dict(
    d: dict[str, Any],
    parent_key: str = "",
    sep: str = ".",
    current_depth: int = 0,
    max_depth: int = 1,
) -> dict[str, Any]:
    """
    Recursively flatten a nested dict up to `max_depth` levels.

    Example (max_depth=1)
    -----
    {"address": {"city": "Delhi", "zip": "110001"}, "name": "Alice"}
    → {"address.city": "Delhi", "address.zip": "110001", "name": "Alice"}
    """
    items: dict[str, Any] = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict) and current_depth < max_depth:
            items.update(
                _flatten_dict(v, new_key, sep, current_depth + 1, max_depth)
            )
        else:
            items[new_key] = v
    return items
