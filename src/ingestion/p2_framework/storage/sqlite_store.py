"""
ingestion/storage/sqlite_store.py
-----------------------------------
Unified output store backed by SQLite via SQLAlchemy 2.0 Core.

Design decisions
----------------
- Schema mirrors UnifiedRecord field-for-field; `payload` is a JSON string.
- Idempotency: INSERT OR IGNORE on (entity_id, checksum) composite unique key.
  Running the same pipeline twice will not create duplicate rows.
- Batch writes: records are inserted in configurable batches for performance.
- Statistics: the store tracks total inserted and skipped (duplicate) counts.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import (
    Column,
    Index,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    insert,
    text,
)
from sqlalchemy.engine import Engine

from src.ingestion.p2_framework.p2_config import OUTPUT_DB_URI, STORAGE_BATCH_SIZE
from src.ingestion.p2_framework.schema import UnifiedRecord

logger = logging.getLogger("p2.storage")

# ──────────────────────────────────────────────────────────────────────────────
# Table definition
# ──────────────────────────────────────────────────────────────────────────────
_metadata = MetaData()

unified_records_table = Table(
    "unified_records",
    _metadata,
    Column("record_id",      String, primary_key=True),
    Column("source_type",    String, nullable=False),
    Column("source_name",    String, nullable=False),
    Column("ingested_at",    String, nullable=False),
    Column("entity_type",    String, nullable=False),
    Column("entity_id",      String, nullable=False),
    Column("payload",        String, nullable=False),   # JSON string
    Column("checksum",       String, nullable=False),
    Column("schema_version", String, nullable=False),
    UniqueConstraint("entity_id", "checksum", name="uq_entity_checksum"),
    Index("ix_source_type", "source_type"),
    Index("ix_entity_type", "entity_type"),
    Index("ix_ingested_at", "ingested_at"),
)


class SQLiteStore:
    """
    Manages reading/writing UnifiedRecord objects to the output SQLite DB.

    Parameters
    ----------
    db_uri     : SQLAlchemy URI (default: from config.OUTPUT_DB_URI).
    batch_size : Number of records per insert batch (default: 100).
    """

    def __init__(
        self,
        db_uri: str | None = None,
        batch_size: int = STORAGE_BATCH_SIZE,
    ) -> None:
        self._db_uri: str = db_uri or OUTPUT_DB_URI
        self._batch_size = batch_size
        self._engine: Engine = create_engine(self._db_uri)
        self._total_inserted: int = 0
        self._total_skipped: int = 0  # Duplicates that were ignored
        self._total_attempted: int = 0
        self._initialise_schema()

    # ── Public API ────────────────────────────────────────────────────────────

    def batch_write(self, records: list[UnifiedRecord]) -> dict[str, int]:
        """
        Insert a list of UnifiedRecord objects into the output store.

        Duplicate records (same entity_id + checksum) are silently skipped
        (INSERT OR IGNORE semantics) to guarantee idempotency.

        Returns
        -------
        dict with keys: inserted, skipped, attempted
        """
        if not records:
            return {"inserted": 0, "skipped": 0, "attempted": 0}

        rows = [r.to_storage_dict() for r in records]
        inserted = 0
        skipped = 0

        with self._engine.begin() as conn:
            for chunk_start in range(0, len(rows), self._batch_size):
                chunk = rows[chunk_start : chunk_start + self._batch_size]
                result = conn.execute(
                    insert(unified_records_table).prefix_with("OR IGNORE"),
                    chunk,
                )
                chunk_inserted = result.rowcount
                chunk_skipped = len(chunk) - chunk_inserted
                inserted += chunk_inserted
                skipped += chunk_skipped

        self._total_inserted += inserted
        self._total_skipped += skipped
        self._total_attempted += len(rows)

        logger.info(
            "Batch written to storage",
            extra={
                "attempted": len(rows),
                "inserted": inserted,
                "skipped_duplicates": skipped,
            },
        )
        return {"inserted": inserted, "skipped": skipped, "attempted": len(rows)}

    def get_run_stats(self) -> dict[str, int]:
        """Return cumulative write statistics for this session."""
        return {
            "total_attempted": self._total_attempted,
            "total_inserted": self._total_inserted,
            "total_skipped": self._total_skipped,
        }

    def count_all(self) -> int:
        """Return total number of records in the output store."""
        with self._engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM unified_records"))
            return result.scalar_one()

    def count_by_source(self) -> dict[str, int]:
        """Return record counts grouped by source_type."""
        with self._engine.connect() as conn:
            result = conn.execute(
                text("SELECT source_type, COUNT(*) as cnt FROM unified_records GROUP BY source_type")
            )
            return {row[0]: row[1] for row in result}

    def query_records(
        self,
        source_type: str | None = None,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Query records from the store with optional filters.

        Parameters
        ----------
        source_type : Filter by source type (CSV/JSON/REST/SQL).
        entity_type : Filter by entity type.
        limit       : Max records to return.

        Returns
        -------
        List of dicts with payload deserialized back to dict.
        """
        conditions = []
        params: dict[str, Any] = {"limit": limit}

        if source_type:
            conditions.append("source_type = :source_type")
            params["source_type"] = source_type
        if entity_type:
            conditions.append("entity_type = :entity_type")
            params["entity_type"] = entity_type

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT * FROM unified_records {where} LIMIT :limit"

        with self._engine.connect() as conn:
            result = conn.execute(text(query), params)
            rows = []
            for row in result:
                d = dict(row._mapping)
                # Deserialise payload JSON string back to dict
                try:
                    d["payload"] = json.loads(d["payload"])
                except (json.JSONDecodeError, TypeError):
                    pass
                rows.append(d)
            return rows

    def close(self) -> None:
        """Dispose of the engine and release connections."""
        self._engine.dispose()
        logger.info("SQLiteStore closed", extra={"db_uri": self._db_uri})

    # ── Schema initialisation ─────────────────────────────────────────────────

    def _initialise_schema(self) -> None:
        """Create the unified_records table if it does not already exist."""
        _metadata.create_all(self._engine, checkfirst=True)
        logger.debug(
            "Output schema initialised",
            extra={"db_uri": self._db_uri},
        )

    def __repr__(self) -> str:
        return (
            f"SQLiteStore("
            f"db={self._db_uri!r}, "
            f"inserted={self._total_inserted}, "
            f"skipped={self._total_skipped})"
        )
