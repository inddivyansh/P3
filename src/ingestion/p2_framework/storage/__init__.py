# src/ingestion/p2_framework/storage/__init__.py
"""
Storage sub-package for the P2-21 ingestion framework.
"""

from src.ingestion.p2_framework.storage.sqlite_store import SQLiteStore

__all__ = ["SQLiteStore"]
