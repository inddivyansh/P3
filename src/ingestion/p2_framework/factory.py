"""
src/ingestion/p2_framework/factory.py
---------------------------------------
Extensible Connector Factory and Registry for Multi-Source Data Ingestion.

Implements the Open-Closed Principle (OCP):
- New data source connectors can be registered dynamically via the
  `@register_connector(type_name)` decorator or `ConnectorFactory.register()`.
- The factory dynamically instantiates active connectors based on declarative
  YAML/dict configuration without requiring changes to pipeline orchestrators.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Type

import yaml

from src.ingestion.p2_framework.connectors.base import BaseConnector

logger = logging.getLogger("p2.factory")


class ConnectorRegistry:
    """Registry maintaining mappings of source type identifiers to connector classes."""

    _registry: dict[str, Type[BaseConnector]] = {}

    @classmethod
    def register(cls, source_type: str, connector_cls: Type[BaseConnector]) -> None:
        """Register a connector class under a source type identifier."""
        key = source_type.strip().lower()
        cls._registry[key] = connector_cls
        logger.debug("Registered connector '%s' -> %s", key, connector_cls.__name__)

    @classmethod
    def get(cls, source_type: str) -> Type[BaseConnector] | None:
        """Retrieve registered connector class for a source type."""
        return cls._registry.get(source_type.strip().lower())

    @classmethod
    def all(cls) -> dict[str, Type[BaseConnector]]:
        """Return a copy of all registered connectors."""
        return dict(cls._registry)


def register_connector(source_type: str) -> Callable[[Type[BaseConnector]], Type[BaseConnector]]:
    """Decorator to register a connector class into ConnectorRegistry."""
    def decorator(cls: Type[BaseConnector]) -> Type[BaseConnector]:
        ConnectorRegistry.register(source_type, cls)
        return cls
    return decorator


class ConnectorFactory:
    """
    Factory for instantiating source connectors from declarative configuration.
    """

    @classmethod
    def register(cls, source_type: str, connector_cls: Type[BaseConnector]) -> None:
        """Register a connector class."""
        ConnectorRegistry.register(source_type, connector_cls)

    @classmethod
    def get_registered_types(cls) -> list[str]:
        """List all currently registered source type identifiers."""
        return sorted(ConnectorRegistry.all().keys())

    @classmethod
    def create_connector(
        cls,
        source_type: str,
        project_root: Path | None = None,
        **kwargs: Any,
    ) -> BaseConnector:
        """
        Instantiate a connector by source type key and configuration arguments.

        Parameters
        ----------
        source_type  : Identifier e.g. 'gdelt', 'worldbank', 'sql', 'rss', 'csv', 'rest', 'json'.
        project_root : Base root for relative paths (defaults to cwd / project root).
        **kwargs     : Source-specific parameters from YAML config.
        """
        key = source_type.strip().lower()
        connector_cls = ConnectorRegistry.get(key)
        if not connector_cls:
            available = cls.get_registered_types()
            raise ValueError(
                f"Unknown connector source type: '{source_type}'. "
                f"Registered types: {available}"
            )

        if project_root is None:
            # Default to project root: 3 levels up from this file
            project_root = Path(__file__).resolve().parents[3]

        # Specific normalization per connector type
        if key == "gdelt":
            cache_path = kwargs.get("cache_path")
            if cache_path:
                cache_path = project_root / cache_path if not Path(cache_path).is_absolute() else Path(cache_path)
            return connector_cls(
                query_topics=kwargs.get("query_topics"),
                max_records=kwargs.get("max_records", 250),
                language=kwargs.get("language", "english"),
                cache_path=cache_path,
                timeout=kwargs.get("timeout_seconds", kwargs.get("timeout", 5)),
                use_cache_fallback=kwargs.get("use_cache_fallback", True),
            )

        elif key == "worldbank":
            return connector_cls(
                countries=kwargs.get("countries", "IN;CN;PK;NP;BD;LK;MM;AF;RU;US"),
                indicator=kwargs.get("indicator", "MS.MIL.XPND.GD.ZS"),
                years=kwargs.get("years", 15),
                timeout=kwargs.get("timeout_seconds", kwargs.get("timeout", 30)),
            )

        elif key == "sql":
            db_path = kwargs.get("db_path", "data/intelligence_db.sqlite")
            db_file = project_root / db_path if not Path(db_path).is_absolute() else Path(db_path)
            db_uri = kwargs.get("db_uri") or f"sqlite:///{db_file}"
            return connector_cls(
                db_uri=db_uri,
                table_name=kwargs.get("table", kwargs.get("table_name", "countries_of_interest")),
                entity_type=kwargs.get("entity_type", "strategic_reference"),
                entity_id_field=kwargs.get("entity_id_field", "id"),
            )

        elif key == "rss":
            feed_urls = []
            # Support feeds list of dicts or tuples
            raw_feeds = kwargs.get("feeds", [])
            for item in raw_feeds:
                if isinstance(item, dict):
                    feed_urls.append((item.get("name", ""), item.get("url", "")))
                elif isinstance(item, (list, tuple)) and len(item) == 2:
                    feed_urls.append((item[0], item[1]))

            return connector_cls(
                feed_urls=feed_urls if feed_urls else None,
                max_per_feed=kwargs.get("max_items_per_feed", kwargs.get("max_per_feed", 50)),
                timeout=kwargs.get("timeout_seconds", kwargs.get("timeout", 15)),
            )

        elif key == "csv":
            file_path = kwargs.get("file_path", "")
            full_path = project_root / file_path if not Path(file_path).is_absolute() else Path(file_path)
            return connector_cls(
                file_path=full_path,
                entity_type=kwargs.get("entity_type", "generic_csv"),
                entity_id_field=kwargs.get("entity_id_field", "id"),
            )

        elif key == "json":
            file_path = kwargs.get("file_path", "")
            full_path = project_root / file_path if not Path(file_path).is_absolute() else Path(file_path)
            return connector_cls(
                file_path=full_path,
                entity_type=kwargs.get("entity_type", "generic_json"),
                entity_id_field=kwargs.get("entity_id_field", "id"),
            )

        elif key == "rest":
            return connector_cls(
                base_url=kwargs.get("base_url", ""),
                endpoint=kwargs.get("endpoint", ""),
                entity_type=kwargs.get("entity_type", "generic_rest"),
                entity_id_field=kwargs.get("entity_id_field", "id"),
                params=kwargs.get("params"),
                headers=kwargs.get("headers"),
            )

        # Generic fallback: instantiate with kwargs
        return connector_cls(**kwargs)

    @classmethod
    def build_all_from_config(
        cls,
        config: dict[str, Any] | str | Path,
        project_root: Path | None = None,
        source_filter: str | None = None,
        skip_rss: bool = False,
    ) -> list[BaseConnector]:
        """
        Build all enabled connectors from a configuration dict or YAML file path.

        Parameters
        ----------
        config        : Parsed configuration dict or path to sources.yaml.
        project_root  : Project root directory for path resolution.
        source_filter : Optional single source identifier filter (e.g. 'gdelt').
        skip_rss      : If True, exclude the RSS connector.

        Returns
        -------
        List of initialized BaseConnector instances ready for IngestionEngine.
        """
        if project_root is None:
            project_root = Path(__file__).resolve().parents[3]

        if isinstance(config, (str, Path)):
            config_path = Path(config)
            if not config_path.is_absolute():
                config_path = project_root / config_path
            if not config_path.exists():
                logger.warning("Sources config not found at %s. Using default fallback config.", config_path)
                from src.ingestion.p2_framework.p2_config import load_sources_config
                config = load_sources_config(config_path)
            else:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}

        sources_dict = config.get("sources", {}) if isinstance(config, dict) else {}
        connectors: list[BaseConnector] = []

        for source_key, source_params in sources_dict.items():
            if not isinstance(source_params, dict):
                continue

            # Check enabled flag
            if not source_params.get("enabled", True):
                logger.debug("Source '%s' is disabled in config. Skipping.", source_key)
                continue

            # Check skip_rss
            source_type = source_params.get("source_type", source_key).lower()
            if skip_rss and source_type == "rss":
                logger.debug("Skipping RSS connector as requested.")
                continue

            # Check source_filter
            if source_filter and source_filter.lower() not in (source_key.lower(), source_type):
                continue

            # Special case for SQL connector: check if DB file exists
            if source_type == "sql":
                db_path = source_params.get("db_path", "data/intelligence_db.sqlite")
                db_file = project_root / db_path if not Path(db_path).is_absolute() else Path(db_path)
                if not db_file.exists():
                    logger.warning(
                        "Strategic Intel DB not found at %s. Skipping SQL connector. "
                        "(Seed with: python scripts/p2_seed_intelligence_db.py)",
                        db_file,
                    )
                    continue

            try:
                connector = cls.create_connector(
                    source_type=source_type,
                    project_root=project_root,
                    **source_params,
                )
                connectors.append(connector)
                logger.info("Instantiated connector for source '%s' (%s)", source_key, connector.__class__.__name__)
            except Exception as e:
                logger.error("Failed to instantiate connector for source '%s': %s", source_key, e)

        return connectors


# ──────────────────────────────────────────────────────────────────────────────
# Auto-register core built-in connectors
# ──────────────────────────────────────────────────────────────────────────────
from src.ingestion.p2_framework.connectors.gdelt_connector import GDELTConnector
from src.ingestion.p2_framework.connectors.worldbank_connector import WorldBankConnector
from src.ingestion.p2_framework.connectors.sql_connector import SQLConnector
from src.ingestion.p2_framework.connectors.rss_connector import RSSConnector
from src.ingestion.p2_framework.connectors.csv_connector import CSVConnector
from src.ingestion.p2_framework.connectors.json_connector import JSONConnector
from src.ingestion.p2_framework.connectors.rest_connector import RESTConnector

ConnectorFactory.register("gdelt", GDELTConnector)
ConnectorFactory.register("worldbank", WorldBankConnector)
ConnectorFactory.register("sql", SQLConnector)
ConnectorFactory.register("rss", RSSConnector)
ConnectorFactory.register("csv", CSVConnector)
ConnectorFactory.register("json", JSONConnector)
ConnectorFactory.register("rest", RESTConnector)
