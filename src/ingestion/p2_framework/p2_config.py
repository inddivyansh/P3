"""
src/ingestion/p2_framework/p2_config.py
-----------------------------------------
Configuration loader and runtime defaults for the Multi-Source Ingestion Framework.

Loads declarative configuration from `config/sources.yaml` with fallback defaults
and environment variable overrides.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("p2.config")

# ──────────────────────────────────────────────────────────────────────────────
# Base paths — resolved from project root
# ──────────────────────────────────────────────────────────────────────────────
# This file lives at: src/ingestion/p2_framework/p2_config.py
# Project root is 3 levels up: .parent.parent.parent
P2_PROJECT_ROOT = Path(__file__).resolve().parents[3]

P2_DATA_DIR   = P2_PROJECT_ROOT / "data"
P2_LOGS_DIR   = P2_PROJECT_ROOT / "logs" / "p2_ingestion"
P2_DLQ_DIR    = P2_PROJECT_ROOT / "data" / "p2_dlq"
P2_OUTPUT_DIR = P2_PROJECT_ROOT / "data" / "p2_raw_store"
SOURCES_CONFIG_FILE = P2_PROJECT_ROOT / "config" / "sources.yaml"

# Ensure runtime directories exist
for _dir in (P2_DATA_DIR, P2_LOGS_DIR, P2_DLQ_DIR, P2_OUTPUT_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# Dynamic YAML Config Loader
# ──────────────────────────────────────────────────────────────────────────────
def load_sources_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """
    Load sources configuration from YAML with fallback defaults.
    """
    path = Path(config_path) if config_path else SOURCES_CONFIG_FILE
    if not path.is_absolute():
        path = P2_PROJECT_ROOT / path

    config: dict[str, Any] = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            logger.debug("Loaded sources configuration from %s", path)
        except Exception as e:
            logger.warning("Failed to parse sources config at %s: %s. Using defaults.", path, e)

    # Ensure baseline structure
    if "sources" not in config:
        config["sources"] = {}
    if "storage" not in config:
        config["storage"] = {}
    if "error_policy" not in config:
        config["error_policy"] = {}

    return config


# Load active config at module import
_ACTIVE_CONFIG = load_sources_config()

# ──────────────────────────────────────────────────────────────────────────────
# Output / DLQ paths
# ──────────────────────────────────────────────────────────────────────────────
_raw_db_rel = _ACTIVE_CONFIG.get("storage", {}).get("raw_db_path", "data/p2_raw_store/unified_store.sqlite")
OUTPUT_DB_PATH = P2_PROJECT_ROOT / _raw_db_rel if not Path(_raw_db_rel).is_absolute() else Path(_raw_db_rel)
OUTPUT_DB_URI  = os.getenv("P2_OUTPUT_DB_URI", f"sqlite:///{OUTPUT_DB_PATH}")

_dlq_rel = _ACTIVE_CONFIG.get("storage", {}).get("dlq_path", "data/p2_dlq/dead_letter.json")
DLQ_FILE_PATH  = P2_PROJECT_ROOT / _dlq_rel if not Path(_dlq_rel).is_absolute() else Path(_dlq_rel)

# ──────────────────────────────────────────────────────────────────────────────
# SOURCE 1 — GDELT Geopolitical Events (CSV)
# ──────────────────────────────────────────────────────────────────────────────
_gdelt_cfg = _ACTIVE_CONFIG.get("sources", {}).get("gdelt", {})

GDELT_API_BASE = os.getenv("GDELT_API_BASE", _gdelt_cfg.get("api_base", "https://api.gdeltproject.org/api/v2/doc/doc"))

GDELT_QUERY_TOPICS = _gdelt_cfg.get("query_topics", [
    "Indian Army",
    "Pakistan army",
    "China PLA",
    "LAC border India",
    "Line of Control India",
    "DRDO India",
    "Doklam",
    "Arunachal Pradesh China",
    "Siachen glacier",
    "Indian Navy",
    "IAF India",
    "defence procurement India",
    "India China border",
    "India Pakistan border",
    "nuclear Pakistan India",
    "terrorism India",
])

GDELT_MAX_RECORDS  = int(os.getenv("GDELT_MAX_RECORDS", str(_gdelt_cfg.get("max_records", 250))))
GDELT_LANGUAGE     = os.getenv("GDELT_LANGUAGE", _gdelt_cfg.get("language", "english"))

_gdelt_cache_rel   = _gdelt_cfg.get("cache_path", "data/gdelt_events.csv")
GDELT_CSV_CACHE    = P2_PROJECT_ROOT / _gdelt_cache_rel if not Path(_gdelt_cache_rel).is_absolute() else Path(_gdelt_cache_rel)

# ──────────────────────────────────────────────────────────────────────────────
# SOURCE 2 — Defence RSS Feeds (JSON/feedparser)
# ──────────────────────────────────────────────────────────────────────────────
_rss_cfg = _ACTIVE_CONFIG.get("sources", {}).get("rss", {})

_configured_rss_feeds = _rss_cfg.get("feeds", [])
if _configured_rss_feeds:
    RSS_FEED_URLS = [
        (f.get("name", ""), f.get("url", "")) if isinstance(f, dict) else (f[0], f[1])
        for f in _configured_rss_feeds
    ]
else:
    RSS_FEED_URLS = [
        ("idrw.org",           "https://idrw.org/feed"),
        ("nationaldefence.in", "https://nationaldefence.in/feed"),
        ("broadsword",         "https://ajaishukla.blogspot.com/feeds/posts/default"),
        ("thehindu_national",  "https://www.thehindu.com/news/national/feeder/default.rss"),
        ("thewire",            "https://thewire.in/rss"),
        ("firstpost_defence",  "https://www.firstpost.com/rss/defence.xml"),
    ]

RSS_TIMEOUT_SECONDS    = int(os.getenv("RSS_TIMEOUT_SECONDS", str(_rss_cfg.get("timeout_seconds", 15))))
RSS_MAX_ITEMS_PER_FEED = int(os.getenv("RSS_MAX_ITEMS_PER_FEED", str(_rss_cfg.get("max_items_per_feed", 50))))

# ──────────────────────────────────────────────────────────────────────────────
# SOURCE 3 — World Bank Military Expenditure API (REST)
# ──────────────────────────────────────────────────────────────────────────────
_wb_cfg = _ACTIVE_CONFIG.get("sources", {}).get("worldbank", {})

WORLD_BANK_BASE_URL  = os.getenv("WORLD_BANK_BASE_URL", _wb_cfg.get("base_url", "https://api.worldbank.org/v2"))
WORLD_BANK_INDICATOR = os.getenv("WORLD_BANK_INDICATOR", _wb_cfg.get("indicator", "MS.MIL.XPND.GD.ZS"))
WORLD_BANK_COUNTRIES = os.getenv("WORLD_BANK_COUNTRIES", _wb_cfg.get("countries", "IN;CN;PK;NP;BD;LK;MM;AF;RU;US"))
WORLD_BANK_YEARS     = int(os.getenv("WORLD_BANK_YEARS", str(_wb_cfg.get("years", 15))))

# ──────────────────────────────────────────────────────────────────────────────
# SOURCE 4 — Strategic Intelligence Reference DB (SQL)
# ──────────────────────────────────────────────────────────────────────────────
_sql_cfg = _ACTIVE_CONFIG.get("sources", {}).get("sql", {})

_sql_db_rel = _sql_cfg.get("db_path", "data/intelligence_db.sqlite")
INTEL_DB_PATH  = P2_PROJECT_ROOT / _sql_db_rel if not Path(_sql_db_rel).is_absolute() else Path(_sql_db_rel)
INTEL_DB_URI   = os.getenv("INTEL_DB_URI", f"sqlite:///{INTEL_DB_PATH}")
INTEL_DB_TABLE = _sql_cfg.get("table", "countries_of_interest")

# ──────────────────────────────────────────────────────────────────────────────
# Retry settings
# ──────────────────────────────────────────────────────────────────────────────
_err_cfg = _ACTIVE_CONFIG.get("error_policy", {})

RETRY_MAX_ATTEMPTS     = int(_err_cfg.get("retry_max_attempts", 5))
RETRY_WAIT_MIN_SECONDS = int(_err_cfg.get("retry_wait_min_seconds", 2))
RETRY_WAIT_MAX_SECONDS = int(_err_cfg.get("retry_wait_max_seconds", 60))
RETRY_WAIT_MULTIPLIER  = int(_err_cfg.get("retry_multiplier", 2))

# ──────────────────────────────────────────────────────────────────────────────
# Schema & Batch sizes
# ──────────────────────────────────────────────────────────────────────────────
SCHEMA_VERSION = _ACTIVE_CONFIG.get("version", "2.0")
STORAGE_BATCH_SIZE    = int(_ACTIVE_CONFIG.get("storage", {}).get("batch_size", 100))
SQL_SOURCE_BATCH_SIZE = int(_sql_cfg.get("batch_size", 500))

LOG_FILE_PATH = P2_LOGS_DIR / "p2_ingestion.log"
