"""
ingestion/error_handling/dlq.py
---------------------------------
Dead-Letter Queue (DLQ) manager.

Failed records (structural parse errors or schema validation failures)
are written to a JSON Lines file with full forensics metadata attached.
The DLQ file can be inspected, replayed, or exported independently.
"""

from __future__ import annotations

import json
import logging
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ingestion.p2_framework.p2_config import DLQ_FILE_PATH

logger = logging.getLogger("p2.dlq")


class DLQEntry:
    """
    A single Dead-Letter Queue entry wrapping a failed record with
    full forensic context.
    """

    def __init__(
        self,
        source_type: str,
        source_name: str,
        raw_record: dict[str, Any],
        error: Exception,
        attempts: int = 1,
    ) -> None:
        self.dlq_id: str = str(uuid.uuid4())
        self.timestamp: str = datetime.now(timezone.utc).isoformat()
        self.source_type: str = source_type
        self.source_name: str = source_name
        self.raw_record: dict[str, Any] = raw_record
        self.error_type: str = type(error).__name__
        self.error_message: str = str(error)
        self.traceback: str = traceback.format_exc()
        self.attempts: int = attempts

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict suitable for JSON output."""
        return {
            "dlq_id": self.dlq_id,
            "timestamp": self.timestamp,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "raw_record": self.raw_record,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "traceback": self.traceback,
            "attempts": self.attempts,
        }


class DeadLetterQueue:
    """
    Persists failed records to a JSON Lines (`.json`) file.

    Each line in the file is a standalone JSON object (DLQEntry).
    The file is opened in append mode so entries from multiple runs
    accumulate without overwriting previous failures.

    Parameters
    ----------
    file_path : Path to the DLQ file (default: from config.DLQ_FILE_PATH).
    """

    def __init__(self, file_path: Path | None = None) -> None:
        self._file_path: Path = Path(file_path) if file_path else DLQ_FILE_PATH
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._count: int = 0  # Entries pushed in this session

    # ── Public API ────────────────────────────────────────────────────────────

    def push(
        self,
        source_type: str,
        source_name: str,
        raw_record: dict[str, Any],
        error: Exception,
        attempts: int = 1,
    ) -> DLQEntry:
        """
        Record a failed record in the DLQ file.

        Parameters
        ----------
        source_type : SourceType enum value string (e.g. "CSV").
        source_name : Logical source name (filename, URL, table).
        raw_record  : The original raw dict that failed processing.
        error       : The exception that caused the failure.
        attempts    : Number of retry attempts made before DLQ.

        Returns
        -------
        DLQEntry : The entry that was written (for inspection in tests).
        """
        entry = DLQEntry(
            source_type=source_type,
            source_name=source_name,
            raw_record=raw_record,
            error=error,
            attempts=attempts,
        )
        self._append_to_file(entry)
        self._count += 1
        logger.warning(
            "Record sent to DLQ",
            extra={
                "dlq_id": entry.dlq_id,
                "source_type": source_type,
                "source_name": source_name,
                "error_type": entry.error_type,
                "error_message": entry.error_message,
            },
        )
        return entry

    def read_all(self) -> list[dict[str, Any]]:
        """
        Read and return all DLQ entries from the file as a list of dicts.
        Returns empty list if the file does not exist.
        """
        if not self._file_path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with open(self._file_path, encoding="utf-8") as fh:
            for line_num, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    logger.error(
                        "Corrupt DLQ entry",
                        extra={"line_number": line_num, "error": str(exc)},
                    )
        return entries

    def session_count(self) -> int:
        """Number of entries pushed during the current session."""
        return self._count

    def total_count(self) -> int:
        """Total number of entries in the DLQ file (all sessions)."""
        return len(self.read_all())

    def clear(self) -> None:
        """
        Truncate the DLQ file.
        Use with caution — only in tests or after manual remediation.
        """
        if self._file_path.exists():
            self._file_path.unlink()
        self._count = 0
        logger.info("DLQ file cleared", extra={"path": str(self._file_path)})

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _append_to_file(self, entry: DLQEntry) -> None:
        """Append a single DLQEntry as a JSON line to the DLQ file."""
        with open(self._file_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict(), default=str) + "\n")

    def __repr__(self) -> str:
        return (
            f"DeadLetterQueue("
            f"file={self._file_path.name!r}, "
            f"session_entries={self._count})"
        )
