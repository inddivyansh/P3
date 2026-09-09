"""
ingestion/engine.py
---------------------
Central orchestrator: IngestionEngine.

Coordinates the full ingestion lifecycle for every registered connector:
  connect → extract → validate → batch-write → disconnect

Error routing
-------------
  StructuralIngestionError  → DLQ (record quarantined, pipeline continues)
  ValidationIngestionError  → DLQ (record quarantined, pipeline continues)
  FatalIngestionError       → Connector aborted; other connectors continue
  Unexpected Exception      → Logged as ERROR; treated as fatal for connector

After all connectors complete, call engine.report() for a run summary.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from src.ingestion.p2_framework.connectors.base import BaseConnector
from src.ingestion.p2_framework.error_handling.dlq import DeadLetterQueue
from src.ingestion.p2_framework.error_handling.exceptions import (
    FatalIngestionError,
    IngestionBaseError,
    StructuralIngestionError,
    ValidationIngestionError,
)
from src.ingestion.p2_framework.schema import UnifiedRecord
from src.ingestion.p2_framework.storage.sqlite_store import SQLiteStore
from src.ingestion.p2_framework.validator import validate

logger = logging.getLogger("p2.engine")


# ──────────────────────────────────────────────────────────────────────────────
# Per-connector run statistics
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class ConnectorStats:
    source_type: str
    source_name: str
    total_extracted: int = 0
    total_validated: int = 0
    total_failed: int = 0       # Sent to DLQ
    total_inserted: int = 0
    total_skipped: int = 0      # Duplicates
    duration_seconds: float = 0.0
    status: str = "pending"     # pending | success | aborted


# ──────────────────────────────────────────────────────────────────────────────
# Ingestion Engine
# ──────────────────────────────────────────────────────────────────────────────
class IngestionEngine:
    """
    Orchestrates ingestion from multiple registered source connectors
    into a single unified output store.

    Parameters
    ----------
    storage   : SQLiteStore instance (output destination).
    dlq       : DeadLetterQueue instance.
    batch_size: Number of validated records to accumulate before writing.
    """

    def __init__(
        self,
        storage: SQLiteStore | None = None,
        dlq: DeadLetterQueue | None = None,
        batch_size: int = 100,
    ) -> None:
        self._storage = storage or SQLiteStore()
        self._dlq = dlq or DeadLetterQueue()
        self._batch_size = batch_size
        self._connectors: list[BaseConnector] = []
        self._stats: list[ConnectorStats] = []
        self._pipeline_start: float = 0.0
        self._pipeline_end: float = 0.0

    @classmethod
    def from_config(
        cls,
        config: dict[str, Any] | str | Path | None = None,
        source_filter: str | None = None,
        skip_rss: bool = False,
        storage: SQLiteStore | None = None,
        dlq: DeadLetterQueue | None = None,
    ) -> "IngestionEngine":
        """
        Build and configure an IngestionEngine instance directly from a configuration
        dictionary or YAML file path using ConnectorFactory.
        """
        from pathlib import Path
        from src.ingestion.p2_framework.factory import ConnectorFactory
        from src.ingestion.p2_framework.p2_config import load_sources_config, DLQ_FILE_PATH, STORAGE_BATCH_SIZE

        if config is None or isinstance(config, (str, Path)):
            cfg_dict = load_sources_config(config)
        else:
            cfg_dict = config

        batch_size = cfg_dict.get("storage", {}).get("batch_size", STORAGE_BATCH_SIZE)
        engine = cls(
            storage=storage,
            dlq=dlq or DeadLetterQueue(file_path=DLQ_FILE_PATH),
            batch_size=batch_size,
        )

        connectors = ConnectorFactory.build_all_from_config(
            config=cfg_dict,
            source_filter=source_filter,
            skip_rss=skip_rss,
        )

        for conn in connectors:
            engine.register_connector(conn)

        return engine

    # ── Registration ──────────────────────────────────────────────────────────

    def register_connector(self, connector: BaseConnector) -> None:
        """Add a connector to the pipeline. Call before run()."""
        self._connectors.append(connector)
        logger.info(
            "Connector registered",
            extra={
                "connector": connector.__class__.__name__,
                "source_name": connector.source_name,
                "entity_type": connector.entity_type,
            },
        )

    # ── Pipeline execution ────────────────────────────────────────────────────

    def run(self) -> None:
        """
        Execute the full ingestion pipeline for all registered connectors.
        Connectors run sequentially. A fatal error in one connector does NOT
        stop the others from running.
        """
        if not self._connectors:
            logger.warning("No connectors registered — nothing to do.")
            return

        self._pipeline_start = time.perf_counter()
        logger.info(
            "Pipeline started",
            extra={"num_connectors": len(self._connectors)},
        )

        for connector in self._connectors:
            stats = self._run_connector(connector)
            self._stats.append(stats)

        self._pipeline_end = time.perf_counter()
        total_duration = round(self._pipeline_end - self._pipeline_start, 3)
        logger.info(
            "Pipeline completed",
            extra={
                "total_duration_seconds": total_duration,
                "connectors_run": len(self._connectors),
                "dlq_entries": self._dlq.session_count(),
            },
        )

    def _run_connector(self, connector: BaseConnector) -> ConnectorStats:
        """Run a single connector and return its statistics."""
        stats = ConnectorStats(
            source_type=connector.get_source_type().value,
            source_name=connector.source_name,
        )
        start = time.perf_counter()
        buffer: list[UnifiedRecord] = []

        logger.info(
            "Connector starting",
            extra={
                "source_type": stats.source_type,
                "source_name": stats.source_name,
            },
        )

        try:
            connector.connect()
            extractor = connector.extract()
            while True:
                try:
                    raw_record = next(extractor)
                except StopIteration:
                    break
                except (StructuralIngestionError, ValidationIngestionError) as exc:
                    # Error raised from within the generator (e.g. malformed row)
                    stats.total_extracted += 1
                    stats.total_failed += 1
                    self._dlq.push(
                        source_type=connector.get_source_type().value,
                        source_name=connector.source_name,
                        raw_record=exc.raw_record,
                        error=exc,
                    )
                    continue

                stats.total_extracted += 1
                validated = self._process_record(raw_record, connector, stats)
                if validated is not None:
                    buffer.append(validated)
                    if len(buffer) >= self._batch_size:
                        self._flush_buffer(buffer, stats)
                        buffer = []

            # Flush remaining records
            if buffer:
                self._flush_buffer(buffer, stats)

            stats.status = "success"

        except FatalIngestionError as exc:
            stats.status = "aborted"
            logger.error(
                "Connector aborted — FatalIngestionError",
                extra={
                    "source_type": stats.source_type,
                    "source_name": stats.source_name,
                    "error": str(exc),
                },
            )
        except Exception as exc:
            stats.status = "aborted"
            logger.error(
                "Connector aborted — unexpected error",
                extra={
                    "source_type": stats.source_type,
                    "source_name": stats.source_name,
                    "error": repr(exc),
                },
                exc_info=True,
            )
        finally:
            try:
                connector.disconnect()
            except Exception:
                pass  # Don't let disconnect errors mask original errors

        stats.duration_seconds = round(time.perf_counter() - start, 3)
        logger.info(
            "Connector finished",
            extra={
                "source_type": stats.source_type,
                "extracted": stats.total_extracted,
                "validated": stats.total_validated,
                "failed": stats.total_failed,
                "inserted": stats.total_inserted,
                "skipped": stats.total_skipped,
                "status": stats.status,
                "duration_s": stats.duration_seconds,
            },
        )
        return stats

    def _process_record(
        self,
        raw_record: dict[str, Any],
        connector: BaseConnector,
        stats: ConnectorStats,
    ) -> UnifiedRecord | None:
        """
        Validate a single raw record. Returns the UnifiedRecord on success,
        or None if the record was quarantined to the DLQ.
        """
        try:
            unified = validate(
                raw_record=raw_record,
                source_type=connector.get_source_type(),
                source_name=connector.source_name,
                entity_type=connector.entity_type,
                entity_id_field=connector.entity_id_field,
            )
            stats.total_validated += 1
            return unified

        except (StructuralIngestionError, ValidationIngestionError) as exc:
            stats.total_failed += 1
            self._dlq.push(
                source_type=connector.get_source_type().value,
                source_name=connector.source_name,
                raw_record=raw_record,
                error=exc,
            )
            return None

    def _flush_buffer(
        self,
        buffer: list[UnifiedRecord],
        stats: ConnectorStats,
    ) -> None:
        """Write a buffer of validated records to the output store."""
        result = self._storage.batch_write(buffer)
        stats.total_inserted += result["inserted"]
        stats.total_skipped += result["skipped"]

    # ── Reporting ──────────────────────────────────────────────────────────────

    def report(self) -> str:
        """
        Print and return a formatted pipeline run summary table.
        """
        total_duration = round(self._pipeline_end - self._pipeline_start, 3)
        lines = [
            "",
            "=" * 74,
            "     MULTI-SOURCE DATA INGESTION FRAMEWORK -- RUN SUMMARY",
            "=" * 74,
            "",
            f"  {'SOURCE':<8} {'NAME':<38} {'EXTRACTED':>9} {'VALID':>7} {'FAILED':>7} {'INSERTED':>9} {'SKIPPED':>8} {'STATUS':<10}",
            "  " + "-" * 100,
        ]

        totals = {"extracted": 0, "validated": 0, "failed": 0, "inserted": 0, "skipped": 0}
        for s in self._stats:
            lines.append(
                f"  {s.source_type:<8} {s.source_name[:37]:<38} "
                f"{s.total_extracted:>9,} {s.total_validated:>7,} {s.total_failed:>7,} "
                f"{s.total_inserted:>9,} {s.total_skipped:>8,} {s.status:<10}"
            )
            totals["extracted"]  += s.total_extracted
            totals["validated"]  += s.total_validated
            totals["failed"]     += s.total_failed
            totals["inserted"]   += s.total_inserted
            totals["skipped"]    += s.total_skipped

        lines += [
            "  " + "-" * 100,
            f"  {'TOTAL':<8} {'':<38} "
            f"{totals['extracted']:>9,} {totals['validated']:>7,} {totals['failed']:>7,} "
            f"{totals['inserted']:>9,} {totals['skipped']:>8,}",
            "",
            f"  DLQ entries this session : {self._dlq.session_count()}",
            f"  DLQ file (total)         : {self._dlq.total_count()}",
            f"  Total pipeline duration  : {total_duration}s",
            "",
        ]
        report_str = "\n".join(lines)
        print(report_str)
        return report_str

    def get_stats(self) -> list[ConnectorStats]:
        """Return per-connector statistics for programmatic access."""
        return list(self._stats)

    def get_storage(self) -> SQLiteStore:
        return self._storage

    def get_dlq(self) -> DeadLetterQueue:
        return self._dlq
