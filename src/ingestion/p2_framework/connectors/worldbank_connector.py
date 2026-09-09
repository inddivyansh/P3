"""
ingestion/connectors/worldbank_connector.py
--------------------------------------------
World Bank Military Expenditure API connector.

Fetches military spending as % of GDP for strategically important
countries (India and 9 neighbours/major powers) for the last N years.

Source Type : REST
Entity Type : military_expenditure
Auth        : None — World Bank Indicators API is fully open
API Docs    : https://datahelpdesk.worldbank.org/knowledgebase/topics/125589

Why this matters for Indian Army
----------------------------------
Tracking China's and Pakistan's military spending trends relative to
GDP reveals budget priority shifts and potential capability build-ups
before they become visible in news or satellite imagery.
"""

from __future__ import annotations

import logging
from typing import Any, Generator

import requests

from src.ingestion.p2_framework.p2_config import (
    WORLD_BANK_BASE_URL,
    WORLD_BANK_COUNTRIES,
    WORLD_BANK_INDICATOR,
    WORLD_BANK_YEARS,
)
from src.ingestion.p2_framework.connectors.base import BaseConnector
from src.ingestion.p2_framework.error_handling.exceptions import (
    FatalIngestionError,
    StructuralIngestionError,
    TransientIngestionError,
)
from src.ingestion.p2_framework.error_handling.retry import transient_retry
from src.ingestion.p2_framework.schema import SourceType

logger = logging.getLogger("p2.connectors.worldbank")

# Country code → full name mapping for enrichment
_COUNTRY_NAMES = {
    "IN": "India",
    "CN": "China",
    "PK": "Pakistan",
    "NP": "Nepal",
    "BD": "Bangladesh",
    "LK": "Sri Lanka",
    "MM": "Myanmar",
    "AF": "Afghanistan",
    "RU": "Russia",
    "US": "United States",
}

# Additional indicator for current USD military spending
_INDICATOR_USD = "MS.MIL.XPND.CD"


class WorldBankConnector(BaseConnector):
    """
    Fetches military expenditure data from the World Bank Indicators API.

    Retrieves two metrics per country per year:
      - Military expenditure as % of GDP  (MS.MIL.XPND.GD.ZS)
      - Military expenditure in current USD (MS.MIL.XPND.CD)

    Parameters
    ----------
    countries  : Semicolon-separated ISO-2 country codes.
    indicator  : Primary World Bank indicator code (% of GDP).
    years      : Number of most-recent years to retrieve.
    timeout    : Request timeout in seconds.
    """

    def __init__(
        self,
        countries: str = WORLD_BANK_COUNTRIES,
        indicator: str = WORLD_BANK_INDICATOR,
        years: int = WORLD_BANK_YEARS,
        timeout: int = 30,
    ) -> None:
        self._countries = countries
        self._indicator = indicator
        self._years     = years
        self._timeout   = timeout
        self._session: requests.Session | None = None

        super().__init__(
            source_name="api.worldbank.org",
            entity_type="military_expenditure",
            entity_id_field="id",
        )

    # ── BaseConnector interface ───────────────────────────────────────────────

    def connect(self) -> None:
        self._session = requests.Session()
        self._connected = True
        logger.info(
            "WorldBank connector connected",
            extra={"countries": self._countries, "indicator": self._indicator},
        )

    def extract(self) -> Generator[dict[str, Any], None, None]:
        if not self._connected or self._session is None:
            raise FatalIngestionError(
                message="WorldBankConnector not connected. Call connect() first.",
                source=self.source_name,
            )
        # Fetch % of GDP data
        pct_gdp_data = self._fetch_indicator(self._indicator)
        # Fetch current USD data
        usd_data = self._fetch_indicator(_INDICATOR_USD)

        # Build lookup: (country_code, year) -> usd_value
        usd_lookup: dict[tuple[str, str], float | None] = {}
        for entry in usd_data:
            key = (entry.get("countryiso3code", ""), str(entry.get("date", "")))
            usd_lookup[key] = entry.get("value")

        for entry in pct_gdp_data:
            record = self._entry_to_dict(entry, usd_lookup)
            if record:
                yield record

    def disconnect(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None
        self._connected = False
        logger.info("WorldBank connector disconnected")

    def get_source_type(self) -> SourceType:
        return SourceType.REST

    # ── Private helpers ───────────────────────────────────────────────────────

    @transient_retry
    def _fetch_indicator(self, indicator: str) -> list[dict[str, Any]]:
        """
        Fetch all pages of a World Bank indicator for configured countries.
        World Bank paginates with page=1,2,... until records are exhausted.
        """
        url = (
            f"{WORLD_BANK_BASE_URL}/country/{self._countries}"
            f"/indicator/{indicator}"
        )
        params = {
            "format":   "json",
            "per_page": 500,
            "mrv":      self._years,   # Most Recent Values
        }
        all_data: list[dict[str, Any]] = []
        page = 1

        while True:
            params["page"] = page
            try:
                resp = self._session.get(url, params=params, timeout=self._timeout)
            except requests.exceptions.Timeout as exc:
                raise TransientIngestionError(
                    message=f"World Bank request timed out (indicator={indicator})",
                    source=self.source_name,
                ) from exc
            except requests.exceptions.ConnectionError as exc:
                raise TransientIngestionError(
                    message=f"World Bank connection error: {exc}",
                    source=self.source_name,
                ) from exc

            if resp.status_code != 200:
                raise FatalIngestionError(
                    message=f"World Bank HTTP {resp.status_code} for indicator={indicator}",
                    source=self.source_name,
                )

            try:
                payload = resp.json()
            except Exception as exc:
                raise StructuralIngestionError(
                    message=f"World Bank response is not valid JSON: {exc}",
                    source=self.source_name,
                ) from exc

            # World Bank returns [metadata_dict, data_list]
            if not isinstance(payload, list) or len(payload) < 2:
                raise StructuralIngestionError(
                    message=f"Unexpected World Bank response structure: {type(payload)}",
                    source=self.source_name,
                )

            meta, data = payload[0], payload[1]
            if not isinstance(data, list):
                break
            all_data.extend(data)

            total_pages = meta.get("pages", 1)
            if page >= total_pages:
                break
            page += 1

        logger.info(
            "World Bank indicator fetched",
            extra={"indicator": indicator, "records": len(all_data)},
        )
        return all_data

    def _entry_to_dict(
        self,
        entry: dict[str, Any],
        usd_lookup: dict[tuple[str, str], float | None],
    ) -> dict[str, Any] | None:
        """
        Convert a World Bank API entry into a flat intelligence record.
        Skips entries where the value is None (no data for that year).
        """
        value = entry.get("value")
        if value is None:
            return None   # Skip years with no reported data

        country_info = entry.get("country", {})
        country_id   = entry.get("countryiso3code", "")
        country_code = country_info.get("id", "")     # ISO-2 code
        year         = str(entry.get("date", ""))
        usd_value    = usd_lookup.get((country_id, year))

        # Threat context enrichment
        threat_level = _threat_level(country_code)

        return {
            "id":                    f"{country_code}-{year}",
            "country_name":          _COUNTRY_NAMES.get(country_code, country_info.get("value", "")),
            "country_code":          country_code,
            "country_iso3":          country_id,
            "year":                  year,
            "military_pct_gdp":      round(float(value), 4),
            "military_usd_current":  round(float(usd_value), 2) if usd_value else None,
            "indicator_code":        self._indicator,
            "indicator_name":        "Military expenditure (% of GDP)",
            "threat_context":        threat_level,
            "data_source":           "World Bank / SIPRI",
        }


def _threat_level(country_code: str) -> str:
    """Simple threat classification for Indian Army context."""
    high     = {"CN", "PK"}
    moderate = {"AF", "MM"}
    monitor  = {"NP", "BD", "LK"}
    if country_code in high:
        return "HIGH"
    if country_code in moderate:
        return "MODERATE"
    if country_code in monitor:
        return "MONITOR"
    if country_code == "IN":
        return "SELF"
    return "REFERENCE"
