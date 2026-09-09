"""
ingestion/connectors/base.py
------------------------------
Abstract base class for all source connectors.

Every connector must:
  1. Inherit from BaseConnector
  2. Implement connect(), extract(), disconnect(), get_source_type()
  3. Support the context manager protocol (__enter__ / __exit__)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Generator

from src.ingestion.p2_framework.schema import SourceType

logger = logging.getLogger("p2.connectors")


class BaseConnector(ABC):
    """
    Abstract base for all source connectors.

    Parameters
    ----------
    source_name  : Logical identifier for this source (file path, URL, table).
    entity_type  : The business entity category this source represents
                   (e.g. 'customer', 'order', 'employee', 'user').
    entity_id_field : The field name in the raw record that holds the
                      business/natural key (e.g. 'id', 'CustomerID').
    """

    def __init__(
        self,
        source_name: str,
        entity_type: str,
        entity_id_field: str,
    ) -> None:
        self.source_name = source_name
        self.entity_type = entity_type
        self.entity_id_field = entity_id_field
        self._connected: bool = False
        self.logger = logging.getLogger(
            f"p2.connectors.{self.__class__.__name__}"
        )

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to the data source.
        Called once before extract(). Should set self._connected = True.
        Raises FatalIngestionError on unrecoverable connection failures.
        """

    @abstractmethod
    def extract(self) -> Generator[dict[str, Any], None, None]:
        """
        Yield raw records one at a time as plain dicts.

        Implementations should:
          - Yield records lazily (generator, not list) for memory efficiency.
          - Raise StructuralIngestionError on per-record parse failures
            (let the engine decide whether to DLQ or abort).
          - Raise TransientIngestionError for retriable network/IO errors.
        """

    @abstractmethod
    def disconnect(self) -> None:
        """
        Release any held resources (file handles, DB connections, sessions).
        Should set self._connected = False.
        """

    @abstractmethod
    def get_source_type(self) -> SourceType:
        """Return the SourceType enum value identifying this connector."""

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> "BaseConnector":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        self.disconnect()
        # Do not suppress exceptions — let them propagate to the engine.
        return False

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._connected

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"source_name={self.source_name!r}, "
            f"entity_type={self.entity_type!r}, "
            f"connected={self._connected})"
        )
