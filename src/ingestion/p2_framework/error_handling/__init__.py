# src/ingestion/p2_framework/error_handling/__init__.py
"""
Error handling sub-package for the P2-21 ingestion framework.
"""

from src.ingestion.p2_framework.error_handling.exceptions import (
    IngestionBaseError,
    TransientIngestionError,
    StructuralIngestionError,
    ValidationIngestionError,
    FatalIngestionError,
)
from src.ingestion.p2_framework.error_handling.dlq import DeadLetterQueue, DLQEntry
from src.ingestion.p2_framework.error_handling.retry import transient_retry

__all__ = [
    "IngestionBaseError",
    "TransientIngestionError",
    "StructuralIngestionError",
    "ValidationIngestionError",
    "FatalIngestionError",
    "DeadLetterQueue",
    "DLQEntry",
    "transient_retry",
]
