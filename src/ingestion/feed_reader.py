"""RSS/Atom ingestion using feedparser."""
"""
D-P1-22 — News Feed to Digest Pipeline

RSS / Atom feed ingestion module.

Responsibilities:
    1. Load feed configuration from config/feeds.yaml
    2. Fetch enabled RSS/Atom feeds
    3. Parse feed entries using feedparser
    4. Normalize entries into a common article structure
    5. Remove duplicate URLs
    6. Save the normalized articles as JSON

This module does NOT:
    - extract full article text
    - classify articles
    - perform semantic deduplication
    - generate the digest

Those responsibilities belong to later pipeline stages.
"""
import json
import logging
import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
import feedparser
import requests
import urllib3
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_FILE = PROJECT_ROOT / "config" / "feeds.yaml"
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

OUTPUT_FILE = RAW_DATA_DIR / "articles.json"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------

@dataclass
class Article:
    """
    Normalized representation of an article collected from a feed.
    """

    article_id: str
    title: str
    url: str
    source: str
    source_category_hint: str | None
    published_at: str | None
    summary: str | None
    fetched_at: str


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def load_feed_config(config_path: Path = CONFIG_FILE) -> list[dict[str, Any]]:
    """
    Load enabled feeds from config/feeds.yaml.
    """

    if not config_path.exists():
        raise FileNotFoundError(
            f"Feed configuration not found: {config_path}"
        )

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not config or "feeds" not in config:
        raise ValueError(
            f"Invalid feed configuration: {config_path}"
        )

    feeds = config["feeds"]

    if not isinstance(feeds, list):
        raise ValueError(
            "'feeds' must be a list in feeds.yaml"
        )

    enabled_feeds = [
        feed
        for feed in feeds
        if feed.get("enabled", True)
    ]

    logger.info(
        "Loaded %d enabled feed(s)",
        len(enabled_feeds),
    )

    return enabled_feeds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_text(value: Any) -> str | None:
    """
    Convert feed values to clean strings.

    Feed metadata can occasionally contain HTML or unexpected values.
    Full HTML cleaning will happen later in the processing layer.
    """

    if value is None:
        return None

    text = str(value).strip()

    return text if text else None


def generate_article_id(url: str) -> str:
    """
    Generate a deterministic ID from the article URL.

    The same URL will therefore always produce the same ID.
    """

    return hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()[:16]


def extract_published_date(entry: Any) -> str | None:
    """
    Extract the best available publication timestamp.

    feedparser exposes parsed timestamps through:
        published_parsed
        updated_parsed

    UTC is used for normalized storage.
    """

    parsed_time = (
        getattr(entry, "published_parsed", None)
        or getattr(entry, "updated_parsed", None)
    )

    if parsed_time is None:
        return None

    try:
        dt = datetime(
            parsed_time.tm_year,
            parsed_time.tm_mon,
            parsed_time.tm_mday,
            parsed_time.tm_hour,
            parsed_time.tm_min,
            parsed_time.tm_sec,
            tzinfo=timezone.utc,
        )

        return dt.isoformat()

    except (AttributeError, TypeError, ValueError):
        return None


def extract_summary(entry: Any) -> str | None:
    """
    Extract the feed-provided summary/description.

    This is NOT treated as the final article text.
    """

    summary = getattr(entry, "summary", None)

    if not summary:
        summary = getattr(entry, "description", None)

    return clean_text(summary)


# ---------------------------------------------------------------------------
# Feed parsing
# ---------------------------------------------------------------------------

def _parse_with_bs4(content: bytes, source_name: str, category_hint: str | None, fetched_at: str) -> list[Article]:
    """Fallback XML parser for non-standard or malformed RSS feeds (e.g. PIB ASP.NET XML)."""
    articles = []
    try:
        soup = BeautifulSoup(content, "xml")
        items = soup.find_all("item")
        if not items:
            soup = BeautifulSoup(content, "html.parser")
            items = soup.find_all("item")

        for item in items:
            title_tag = item.find("title")
            link_tag = item.find("link")
            title = clean_text(title_tag.get_text(strip=True)) if title_tag else None
            url = clean_text(link_tag.get_text(strip=True)) if link_tag else None
            if not url and link_tag and link_tag.next_sibling:
                url = clean_text(str(link_tag.next_sibling).strip())
            desc_tag = item.find("description")
            summary = clean_text(desc_tag.get_text(strip=True)) if desc_tag else None
            pub_tag = item.find("pubdate") or item.find("pubDate")
            pub_date = clean_text(pub_tag.get_text(strip=True)) if pub_tag else None

            if title and url:
                articles.append(
                    Article(
                        article_id=generate_article_id(url),
                        title=title,
                        url=url,
                        source=source_name,
                        source_category_hint=category_hint,
                        published_at=pub_date,
                        summary=summary,
                        fetched_at=fetched_at,
                    )
                )
    except Exception as exc:
        logger.debug("BS4 fallback parse failed for %s: %s", source_name, exc)

    return articles


def parse_feed(feed_config: dict[str, Any]) -> list[Article]:
    """
    Fetch and parse one RSS/Atom feed.
    """

    source_name = feed_config["name"]
    feed_url = feed_config["url"]
    category_hint = feed_config.get("category")

    logger.info(
        "Fetching feed: %s",
        source_name,
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/rss+xml, application/xml, application/atom+xml, text/xml, */*",
    }

    parsed = None
    response_content = None

    try:
        response = requests.get(
            feed_url,
            headers=headers,
            timeout=12,
            verify=False,
        )
        if response.status_code == 200:
            response_content = response.content
            parsed = feedparser.parse(response.content)
        else:
            logger.warning(
                "HTTP %d when fetching feed %s (%s)",
                response.status_code,
                source_name,
                feed_url,
            )
    except Exception as exc:
        logger.debug("Requests fetch failed for %s (%s), falling back to feedparser direct fetch", source_name, exc)

    if parsed is None or not getattr(parsed, "entries", None):
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as exc:
            logger.error(
                "Failed to fetch %s: %s",
                source_name,
                exc,
            )
            return []

    articles: list[Article] = []
    fetched_at = datetime.now(timezone.utc).isoformat()

    # Fallback to BeautifulSoup if feedparser failed on non-standard/ASP.NET XML
    if not getattr(parsed, "entries", None) and response_content:
        bs4_articles = _parse_with_bs4(response_content, source_name, category_hint, fetched_at)
        if bs4_articles:
            logger.info("Fetched %d article(s) from %s", len(bs4_articles), source_name)
            return bs4_articles

    # Only log bozo warning if no valid entries could be parsed at all
    if getattr(parsed, "bozo", False) and not getattr(parsed, "entries", None):
        logger.warning(
            "Feed parser error for %s: %s",
            source_name,
            getattr(parsed, "bozo_exception", "syntax or encoding error"),
        )

    if not getattr(parsed, "entries", None):
        logger.warning(
            "No entries found in feed: %s",
            source_name,
        )
        return []

    for entry in parsed.entries:

        title = clean_text(
            getattr(entry, "title", None)
        )

        url = clean_text(
            getattr(entry, "link", None)
        )

        if not title or not url:
            logger.warning(
                "Skipping incomplete entry from %s",
                source_name,
            )
            continue

        article = Article(
            article_id=generate_article_id(url),
            title=title,
            url=url,
            source=source_name,
            source_category_hint=category_hint,
            published_at=extract_published_date(entry),
            summary=extract_summary(entry),
            fetched_at=fetched_at,
        )

        articles.append(article)

    logger.info(
        "Fetched %d article(s) from %s",
        len(articles),
        source_name,
    )

    return articles


# ---------------------------------------------------------------------------
# URL-level deduplication
# ---------------------------------------------------------------------------

def deduplicate_urls(
    articles: list[Article],
) -> list[Article]:
    """
    Remove exact duplicate URLs.

    This is only basic URL deduplication.

    Semantic/near-duplicate detection will be implemented later using
    sentence-transformers.
    """

    seen_urls: set[str] = set()
    unique_articles: list[Article] = []

    for article in articles:

        normalized_url = article.url.rstrip("/")

        if normalized_url in seen_urls:
            continue

        seen_urls.add(normalized_url)
        unique_articles.append(article)

    removed = len(articles) - len(unique_articles)

    logger.info(
        "URL deduplication removed %d duplicate(s)",
        removed,
    )

    return unique_articles


# ---------------------------------------------------------------------------
# Save data
# ---------------------------------------------------------------------------

def save_articles(
    articles: list[Article],
    output_path: Path = OUTPUT_FILE,
) -> None:
    """
    Save normalized articles to JSON.
    """

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "article_count": len(articles),
        "articles": [
            asdict(article)
            for article in articles
        ],
    }

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            payload,
            file,
            indent=2,
            ensure_ascii=False,
        )

    logger.info(
        "Saved %d article(s) to %s",
        len(articles),
        output_path,
    )


# ---------------------------------------------------------------------------
# Main ingestion function
# ---------------------------------------------------------------------------

def run_ingestion() -> list[Article]:
    """
    Execute the complete feed-ingestion stage.
    """

    feeds = load_feed_config()

    all_articles: list[Article] = []

    for feed in feeds:

        required_fields = {
            "name",
            "url",
        }

        missing_fields = required_fields - feed.keys()

        if missing_fields:
            logger.error(
                "Skipping invalid feed configuration %s. "
                "Missing: %s",
                feed,
                ", ".join(sorted(missing_fields)),
            )
            continue

        articles = parse_feed(feed)

        all_articles.extend(articles)

    unique_articles = deduplicate_urls(
        all_articles
    )

    save_articles(unique_articles)

    logger.info(
        "Ingestion complete: %d unique article(s)",
        len(unique_articles),
    )

    return unique_articles


# ---------------------------------------------------------------------------
# D-P2-21 Multi-Source Ingestion Integration
# ---------------------------------------------------------------------------

def _unified_record_to_article(record: dict, source_hint: str = "") -> dict | None:
    """
    Convert a UnifiedRecord storage dict (from P2 SQLiteStore.query_records())
    into a P3-compatible article dict for downstream pipeline stages.

    Handles all four P2 source types:
      - JSON  (RSSConnector):       has title/link/summary — standard article
      - CSV   (GDELTConnector):     has title/url/domain   — article-like
      - REST  (WorldBankConnector): structured data        — synthetic body
      - SQL   (SQLConnector):       reference data         — synthetic body

    Articles that have a real URL will enter Stage 2 (article extraction).
    Structured records (WorldBank, SQL) get a pre-built body and skip Stage 2.
    """
    import json as _json

    payload = record.get("payload", {})
    if isinstance(payload, str):
        try:
            payload = _json.loads(payload)
        except Exception:
            payload = {}

    source_type = record.get("source_type", "").upper()
    entity_type = record.get("entity_type", "")

    # ── RSS / JSON source — standard news article ─────────────────────────
    if source_type == "JSON" or entity_type == "defence_news":
        url = payload.get("link") or payload.get("url") or ""
        if not url:
            return None
        return {
            "article_id":           generate_article_id(url),
            "title":                payload.get("title", ""),
            "url":                  url,
            "source":               payload.get("source_feed") or source_hint or "p2_rss",
            "source_category_hint": "Defence",
            "published_at":         payload.get("published"),
            "summary":              payload.get("summary", ""),
            "fetched_at":           record.get("ingested_at", ""),
            "p2_source_type":       source_type,
            "p2_entity_type":       entity_type,
            "full_text":            None,   # Stage 2 will fetch this
            "needs_extraction":     True,
        }

    # ── GDELT / CSV source — geopolitical event article ───────────────────
    if source_type == "CSV" or entity_type == "geopolitical_event":
        url = payload.get("url") or payload.get("URL") or ""
        title = payload.get("title") or payload.get("Title") or payload.get("domain", "GDELT Event")
        if not url:
            return None
        return {
            "article_id":           generate_article_id(url),
            "title":                title,
            "url":                  url,
            "source":               payload.get("domain") or "gdelt",
            "source_category_hint": "Geopolitics",
            "published_at":         payload.get("seendate") or payload.get("published"),
            "summary":              f"[GDELT] {title}. Source country: {payload.get('sourcecountry', 'Unknown')}",
            "fetched_at":           record.get("ingested_at", ""),
            "p2_source_type":       source_type,
            "p2_entity_type":       entity_type,
            "full_text":            None,   # Stage 2 will fetch this
            "needs_extraction":     True,
            "gdelt_topics":         payload.get("matched_topics", []),
        }

    # ── WorldBank / REST source — military expenditure data ───────────────
    if source_type == "REST" or entity_type == "military_expenditure":
        country = payload.get("country_name", payload.get("country_code", "Unknown"))
        year    = payload.get("year", "")
        pct_gdp = payload.get("military_pct_gdp", "N/A")
        usd     = payload.get("military_usd_current")
        usd_str = f" | ${usd:,.0f}M current USD" if usd else ""
        synthetic_body = (
            f"Military Expenditure Intelligence Report\n\n"
            f"Country: {country}\n"
            f"Year: {year}\n"
            f"Military Expenditure (% of GDP): {pct_gdp}%{usd_str}\n"
            f"Threat Context (Indian Army): {payload.get('threat_context', 'N/A')}\n"
            f"Data Source: {payload.get('data_source', 'World Bank')}\n"
            f"Indicator: {payload.get('indicator_name', 'Military expenditure (% of GDP)')}"
        )
        record_id = record.get("entity_id") or f"worldbank-{country}-{year}"
        return {
            "article_id":           hashlib.sha256(record_id.encode()).hexdigest()[:16],
            "title":                f"Military Expenditure: {country} ({year}) — {pct_gdp}% of GDP",
            "url":                  f"https://data.worldbank.org/indicator/MS.MIL.XPND.GD.ZS?locations={payload.get('country_code', '')}",
            "source":               "World Bank / SIPRI",
            "source_category_hint": "Defence Economics",
            "published_at":         f"{year}-01-01",
            "summary":              synthetic_body[:400],
            "fetched_at":           record.get("ingested_at", ""),
            "full_text":            synthetic_body,  # Pre-built — skip Stage 2
            "p2_source_type":       source_type,
            "p2_entity_type":       entity_type,
            "needs_extraction":     False,  # Already has full_text
            "worldbank_data":       {
                "country":          country,
                "year":             year,
                "military_pct_gdp": pct_gdp,
                "threat_context":   payload.get("threat_context", ""),
            },
        }

    # ── SQL / Strategic reference DB — intelligence reference record ───────
    if source_type == "SQL" or entity_type == "strategic_reference":
        name   = payload.get("name") or payload.get("country_name") or payload.get("id", "Unknown")
        region = payload.get("region", "")
        threat = payload.get("threat_level") or payload.get("threat_context", "")
        fields = {k: v for k, v in payload.items() if v is not None and k not in ("id",)}
        synthetic_body = (
            f"Strategic Intelligence Reference: {name}\n\n"
            + "\n".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in fields.items())
        )
        record_id = record.get("entity_id") or name
        return {
            "article_id":           hashlib.sha256(record_id.encode()).hexdigest()[:16],
            "title":                f"Strategic Intel Reference: {name}" + (f" ({region})" if region else ""),
            "url":                  "",
            "source":               "Strategic Intelligence DB",
            "source_category_hint": "Strategic Affairs",
            "published_at":         None,
            "summary":              synthetic_body[:400],
            "fetched_at":           record.get("ingested_at", ""),
            "full_text":            synthetic_body,  # Pre-built — skip Stage 2
            "p2_source_type":       source_type,
            "p2_entity_type":       entity_type,
            "needs_extraction":     False,  # Already has full_text
            "threat_level":         threat,
        }

    return None


def run_p2_ingestion(
    source_filter: str | None = None,
    skip_rss: bool = False,
    config_path: Path | str | None = None,
) -> list[dict]:
    """
    Run the D-P2-21 Multi-Source Data Ingestion Engine.

    Orchestrates the IngestionEngine with all configured connectors built
    dynamically from config/sources.yaml via ConnectorFactory, reads back
    the stored UnifiedRecords, converts them to intelligence article dicts,
    and saves them to data/raw/p2_articles.json.

    Parameters
    ----------
    source_filter : Limit to one source: 'gdelt', 'rss', 'worldbank', 'sql'.
                    None = run all configured sources.
    skip_rss      : Skip the RSSConnector (to avoid duplicates when running
                    alongside the main RSS feed reader).
    config_path   : Custom path to sources YAML configuration file.

    Returns
    -------
    List of article dicts compatible with downstream pipeline stages 2–10.
    """
    from src.ingestion.p2_framework import (
        IngestionEngine,
        SQLiteStore,
        load_sources_config,
    )
    from src.ingestion.p2_framework.p2_config import SOURCES_CONFIG_FILE, OUTPUT_DB_PATH

    logger.info("=" * 60)
    logger.info("D-P2-21 Multi-Source Ingestion Engine — Starting (Config-Driven)")
    logger.info("=" * 60)

    cfg = load_sources_config(config_path or SOURCES_CONFIG_FILE)

    # ── Run the engine via factory ──────────────────────────────────────
    store = SQLiteStore(db_path=OUTPUT_DB_PATH)
    engine = IngestionEngine.from_config(
        config=cfg,
        source_filter=source_filter,
        skip_rss=skip_rss,
        storage=store,
    )

    logger.info("[P2] Executing ingestion across registered connectors...")
    engine.run()
    engine.report()

    # ── Convert UnifiedRecords → article dicts ──────────────────────────
    raw_records = store.query_records(limit=10_000)
    store.close()

    articles = []
    for rec in raw_records:
        article = _unified_record_to_article(rec)
        if article:
            articles.append(article)

    logger.info("[P2] Converted %d raw records → %d article dicts", len(raw_records), len(articles))

    # ── Save to p2_articles.json ────────────────────────────────────────
    p2_output = RAW_DATA_DIR / "p2_articles.json"
    p2_output.parent.mkdir(parents=True, exist_ok=True)
    import json as _json
    with open(p2_output, "w", encoding="utf-8") as f:
        _json.dump({"articles": articles, "total": len(articles)}, f, ensure_ascii=False, indent=2)

    logger.info("[P2] Saved %d P2 article dicts → %s", len(articles), p2_output)
    return articles


def run_combined_ingestion(
    skip_p2: bool = False,
    p2_source_filter: str | None = None,
    sources_config: Path | str | None = None,
) -> list[dict]:
    """
    Run the full combined ingestion: RSS feeds (feeds.yaml) PLUS P2 multi-source.

    This replaces Stage 1 when P2 integration is active.

    Parameters
    ----------
    skip_p2          : If True and p2_articles.json does not exist, run only legacy RSS ingestion.
    p2_source_filter : Limit P2 engine to one source type.
    sources_config   : Optional custom path to sources YAML configuration file.

    Returns
    -------
    List of merged unique article dicts.
    """
    import json as _json

    # Legacy RSS ingestion (feeds.yaml based)
    rss_articles_raw = run_ingestion()

    # Convert all Article dataclass objects to standard dictionaries
    rss_articles: list[dict[str, Any]] = [
        asdict(a) if hasattr(a, "__dataclass_fields__") else (dict(a) if isinstance(a, dict) else a.__dict__)
        for a in rss_articles_raw
    ]

    existing_urls = {
        a["url"]
        for a in rss_articles
        if isinstance(a, dict) and a.get("url")
    }

    # Load or fetch P2 multi-source articles
    p2_articles: list[dict[str, Any]] = []
    p2_file = RAW_DATA_DIR / "p2_articles.json"

    # 1. Check if Stage 0 already generated p2_articles.json
    if p2_file.exists():
        try:
            with open(p2_file, "r", encoding="utf-8") as f:
                p2_data = _json.load(f)
            p2_articles = p2_data.get("articles", p2_data) if isinstance(p2_data, dict) else p2_data
            logger.info("[Combined] Loaded %d pre-ingested P2 articles from %s", len(p2_articles), p2_file.name)
        except Exception as e:
            logger.warning("[Combined] Could not read %s: %s", p2_file, e)

    # 2. If not loaded from file and not skip_p2, run P2 ingestion now
    if not p2_articles and not skip_p2:
        try:
            p2_articles = run_p2_ingestion(
                source_filter=p2_source_filter,
                skip_rss=True,   # Main RSS already covered by feeds.yaml above
                config_path=sources_config,
            )
        except Exception as e:
            logger.warning("[Combined] P2 ingestion failed (%s) — continuing with RSS-only.", e)

    # Deduplicate by URL — prefer the richer RSS article if URL already seen
    new_p2 = []
    for art in p2_articles:
        if not isinstance(art, dict):
            continue
        url = art.get("url", "")
        if url and url in existing_urls:
            continue  # Duplicate URL from RSS
        if url:
            existing_urls.add(url)
        new_p2.append(art)

    merged = rss_articles + new_p2

    # Save merged output in standard pipeline format
    merged_output = RAW_DATA_DIR / "articles.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "article_count": len(merged),
        "articles": merged,
    }
    with open(merged_output, "w", encoding="utf-8") as f:
        _json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.info(
        "[Combined] Merged ingestion: %d RSS + %d P2-new = %d total articles",
        len(rss_articles), len(new_p2), len(merged),
    )
    return merged


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_ingestion()