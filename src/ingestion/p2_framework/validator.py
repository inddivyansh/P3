"""
ingestion/validator.py
-----------------------
Record-level validation layer.

Takes a raw connector dict + source metadata, passes it through the
transformer to build a normalised dict, then validates it against the
Pydantic UnifiedRecord schema.

On success  → returns a validated UnifiedRecord instance.
On failure  → raises ValidationIngestionError (routed to DLQ by engine).
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from src.ingestion.p2_framework.error_handling.exceptions import ValidationIngestionError
from src.ingestion.p2_framework.schema import SourceType, UnifiedRecord
from src.ingestion.p2_framework.transformer import transform

logger = logging.getLogger("p2.validator")


def validate(
    raw_record: dict[str, Any],
    source_type: SourceType,
    source_name: str,
    entity_type: str,
    entity_id_field: str,
) -> UnifiedRecord:
    """
    Transform and validate a raw connector record.

    Parameters
    ----------
    raw_record      : Raw dict from a connector's extract() method.
    source_type     : SourceType enum (CSV / JSON / REST / SQL).
    source_name     : Logical source identifier (file path, URL, table).
    entity_type     : Business entity category (e.g. 'customer').
    entity_id_field : Field name in raw_record that holds the natural key.

    Returns
    -------
    UnifiedRecord  — Fully validated canonical record.

    Raises
    ------
    ValidationIngestionError
        If the normalised dict fails Pydantic schema validation, or if
        the transformer cannot resolve a required field (e.g. entity_id).
    """
    # ── Step 1: Normalise raw dict → canonical field dict ─────────────────
    try:
        normalised = transform(
            raw_record=raw_record,
            source_type=source_type,
            source_name=source_name,
            entity_type=entity_type,
            entity_id_field=entity_id_field,
        )
    except (ValueError, KeyError) as exc:
        raise ValidationIngestionError(
            message=f"Transformation failed before validation: {exc}",
            source=source_name,
            raw_record=raw_record,
        ) from exc

    # ── Step 2: Pydantic v2 validation ────────────────────────────────────
    try:
        record = UnifiedRecord(**normalised)
        logger.debug(
            "Record validated successfully",
            extra={
                "entity_type": entity_type,
                "entity_id": normalised.get("entity_id"),
                "source_type": source_type.value,
            },
        )
        return record
    except ValidationError as exc:
        errors = exc.errors()
        # Format pydantic errors for the DLQ entry
        error_summary = "; ".join(
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in errors
        )
        raise ValidationIngestionError(
            message=f"Schema validation failed: {error_summary}",
            source=source_name,
            raw_record=raw_record,
            pydantic_errors=errors,
        ) from exc
