"""
ingestion/schema.py
--------------------
Defines the canonical UnifiedRecord Pydantic v2 model.

Every record ingested from every source type MUST be validated against
this schema before being persisted to the output store.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


# ──────────────────────────────────────────────────────────────────────────────
# Source type enumeration
# ──────────────────────────────────────────────────────────────────────────────
class SourceType(str, Enum):
    """Identifies which connector produced the record."""
    CSV = "CSV"
    JSON = "JSON"
    REST = "REST"
    SQL = "SQL"


# ──────────────────────────────────────────────────────────────────────────────
# Canonical unified record
# ──────────────────────────────────────────────────────────────────────────────
class UnifiedRecord(BaseModel):
    """
    The single canonical schema that all ingested records conform to.

    Fields
    ------
    record_id      : Auto-generated UUID4 — globally unique record identifier.
    source_type    : Which connector produced this record (CSV/JSON/REST/SQL).
    source_name    : Logical name of the source (filename, URL, table name).
    ingested_at    : UTC timestamp of when the record entered the pipeline.
    entity_type    : High-level business entity (e.g. "customer", "order").
    entity_id      : Business/natural key from the source system.
    payload        : Full normalised record as a dict (all source fields).
    checksum       : MD5 of the canonical JSON representation of payload —
                     used for deduplication in the output store.
    schema_version : Schema version string for forward-compatibility.
    """

    record_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Auto-generated globally unique record ID (UUID4).",
    )
    source_type: SourceType = Field(
        ...,
        description="Which source connector produced this record.",
    )
    source_name: str = Field(
        ...,
        min_length=1,
        description="Logical name of the data source (file path, URL, table).",
    )
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC datetime when the record was ingested.",
    )
    entity_type: str = Field(
        ...,
        min_length=1,
        description="Business entity category (e.g. 'customer', 'order', 'employee').",
    )
    entity_id: str = Field(
        ...,
        min_length=1,
        description="Business/natural key that uniquely identifies the entity in the source.",
    )
    payload: dict[str, Any] = Field(
        ...,
        description="Full normalised record data; all source fields preserved.",
    )
    checksum: str = Field(
        default="",
        description="MD5 hex digest of the sorted canonical payload JSON. Auto-computed.",
    )
    schema_version: str = Field(
        default="1.0",
        description="Schema version for forward-compatibility tracking.",
    )

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("entity_id", mode="before")
    @classmethod
    def coerce_entity_id_to_str(cls, v: Any) -> str:
        """Accept numeric IDs from source systems and convert to str."""
        if v is None:
            raise ValueError("entity_id must not be None")
        return str(v).strip()

    @field_validator("source_name", mode="before")
    @classmethod
    def strip_source_name(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip()
        return str(v)

    @field_validator("payload", mode="before")
    @classmethod
    def payload_must_be_non_empty(cls, v: Any) -> dict:
        if not isinstance(v, dict):
            raise ValueError(f"payload must be a dict, got {type(v).__name__}")
        if not v:
            raise ValueError("payload must not be empty")
        return v

    @model_validator(mode="after")
    def compute_checksum(self) -> "UnifiedRecord":
        """
        Auto-compute the MD5 checksum from the payload after all fields
        are set. This ensures idempotency — the same source data always
        produces the same checksum regardless of ingestion time.
        """
        if not self.checksum:
            canonical = json.dumps(self.payload, sort_keys=True, default=str)
            self.checksum = hashlib.md5(canonical.encode("utf-8")).hexdigest()
        return self

    # ── Helpers ───────────────────────────────────────────────────────────────

    def to_storage_dict(self) -> dict[str, Any]:
        """
        Flatten the record for storage in SQLite.
        The `payload` dict is serialised to a JSON string.
        `ingested_at` is converted to an ISO-format string.
        """
        return {
            "record_id": self.record_id,
            "source_type": self.source_type.value,
            "source_name": self.source_name,
            "ingested_at": self.ingested_at.isoformat(),
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "payload": json.dumps(self.payload, default=str),
            "checksum": self.checksum,
            "schema_version": self.schema_version,
        }

    def __repr__(self) -> str:
        return (
            f"UnifiedRecord(source_type={self.source_type.value!r}, "
            f"entity_type={self.entity_type!r}, "
            f"entity_id={self.entity_id!r}, "
            f"checksum={self.checksum[:8]!r}...)"
        )
