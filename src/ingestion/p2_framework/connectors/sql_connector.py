"""
ingestion/connectors/sql_connector.py
---------------------------------------
SQL database source connector (SQLAlchemy — DB-agnostic).

Supports any SQLAlchemy-compatible database:
  SQLite, PostgreSQL, MySQL, MSSQL, Oracle, etc.

Features
--------
- DB-agnostic via SQLAlchemy 2.0 Core (no ORM).
- Configurable: table name, batch size, optional WHERE filter.
- Yields one dict per row using .mappings() for zero-copy reads.
- Raises FatalIngestionError on connection or table-not-found errors.
"""

from __future__ import annotations

import logging
from typing import Any, Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError

from src.ingestion.p2_framework.connectors.base import BaseConnector
from src.ingestion.p2_framework.error_handling.exceptions import FatalIngestionError
from src.ingestion.p2_framework.schema import SourceType

logger = logging.getLogger("p2.connectors.sql")


class SQLConnector(BaseConnector):
    """
    Reads rows from a SQL table and yields them as plain dicts.

    Parameters
    ----------
    db_uri          : SQLAlchemy connection URI.
                      e.g. "sqlite:///data/sample_db.sqlite"
                           "postgresql://user:pass@host/dbname"
    table_name      : Name of the source table to read from.
    entity_type     : Business entity name (e.g. 'employee').
    entity_id_field : Column name holding the natural primary key.
    batch_size      : Number of rows to fetch per database round-trip.
    where_clause    : Optional SQL WHERE clause (without "WHERE" keyword).
                      e.g. "status = 'active' AND created_at > '2024-01-01'"
    """

    def __init__(
        self,
        db_uri: str,
        table_name: str,
        entity_type: str = "record",
        entity_id_field: str = "id",
        batch_size: int = 500,
        where_clause: str | None = None,
    ) -> None:
        self._db_uri = db_uri
        self._table_name = table_name
        self._batch_size = batch_size
        self._where_clause = where_clause
        self._engine = None
        self._connection = None

        super().__init__(
            source_name=f"{db_uri}/{table_name}",
            entity_type=entity_type,
            entity_id_field=entity_id_field,
        )

    # ── BaseConnector interface ───────────────────────────────────────────────

    def connect(self) -> None:
        try:
            self._engine = create_engine(self._db_uri)
            self._connection = self._engine.connect()
            # Verify the table exists
            inspector = inspect(self._engine)
            available_tables = inspector.get_table_names()
            if self._table_name not in available_tables:
                raise FatalIngestionError(
                    message=(
                        f"Table '{self._table_name}' not found in database. "
                        f"Available tables: {available_tables}"
                    ),
                    source=self.source_name,
                )
            self._connected = True
            logger.info(
                "SQL connector connected",
                extra={"db_uri": self._db_uri, "table": self._table_name},
            )
        except OperationalError as exc:
            raise FatalIngestionError(
                message=f"Failed to connect to database '{self._db_uri}': {exc}",
                source=self.source_name,
            ) from exc

    def extract(self) -> Generator[dict[str, Any], None, None]:
        if not self._connected or self._connection is None:
            raise FatalIngestionError(
                message="SQL connector not connected. Call connect() first.",
                source=self.source_name,
            )
        query = self._build_query()
        logger.debug("Executing SQL query", extra={"query": query})
        try:
            result = self._connection.execute(text(query))
            # Stream in configurable batches for memory efficiency
            while True:
                batch = result.fetchmany(self._batch_size)
                if not batch:
                    break
                for row in batch:
                    yield dict(row._mapping)
        except (OperationalError, ProgrammingError) as exc:
            raise FatalIngestionError(
                message=f"SQL query failed on table '{self._table_name}': {exc}",
                source=self.source_name,
            ) from exc

    def disconnect(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
        self._connected = False
        logger.info(
            "SQL connector disconnected",
            extra={"table": self._table_name},
        )

    def get_source_type(self) -> SourceType:
        return SourceType.SQL

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_query(self) -> str:
        """Construct the SELECT query string."""
        base = f"SELECT * FROM {self._table_name}"
        if self._where_clause:
            return f"{base} WHERE {self._where_clause}"
        return base
