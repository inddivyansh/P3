"""
AI-Powered Defence & Geopolitical Intelligence Platform
=======================================================

Enhanced storage layer with intelligence fields.

Stored information includes all original fields plus:
    - AI-generated structured summary
    - Multi-label primary categories + sub-categories
    - Granular location intelligence (country/state/district/city/locality)
    - Named entities (people, organizations, equipment)
    - Topics, keywords, tags
    - Sentiment and stance analysis
    - Threat level classification (AI-generated analytical flags)
    - Strategic relevance indicators
    - Monitoring and review flags
    - Structured events
    - Processing status flags

IMPORTANT: All threat levels, monitoring flags, and intervention
indicators are AI-generated analytical flags only. They do not
constitute official intelligence assessments or operational
recommendations.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any


# ============================================================================
# PATHS
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "categorized_articles.json"
)

DATABASE_DIR = (
    PROJECT_ROOT
    / "data"
    / "database"
)

DATABASE_FILE = (
    DATABASE_DIR
    / "news_pipeline.db"
)


# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================================
# DATABASE SCHEMA
# ============================================================================

CREATE_ARTICLES_TABLE = """
CREATE TABLE IF NOT EXISTS articles (

    -- -----------------------------------------------------------------------
    -- Core identifiers
    -- -----------------------------------------------------------------------
    article_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    source TEXT,
    source_category_hint TEXT,

    -- -----------------------------------------------------------------------
    -- Timestamps
    -- -----------------------------------------------------------------------
    published_at TEXT,
    fetched_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,

    -- -----------------------------------------------------------------------
    -- Article content
    -- -----------------------------------------------------------------------
    summary TEXT,               -- Original RSS/feed summary
    ai_summary TEXT,            -- Gemini-generated structured summary
    article_text TEXT,          -- Full extracted article text (trafilatura)
    classifier_text TEXT,       -- Text used for classification (truncated)
    text_length INTEGER,

    -- -----------------------------------------------------------------------
    -- Story clustering (existing deduplication)
    -- -----------------------------------------------------------------------
    story_cluster_id TEXT,
    is_cluster_representative INTEGER,

    -- -----------------------------------------------------------------------
    -- Original single-label classification (kept for backward compat)
    -- -----------------------------------------------------------------------
    category TEXT,
    category_confidence REAL,
    category_scores TEXT,       -- JSON: {category: score}
    classifier_model TEXT,
    classifier_device TEXT,

    -- -----------------------------------------------------------------------
    -- Multi-label classification (NEW)
    -- -----------------------------------------------------------------------
    primary_categories TEXT,    -- JSON array: ["Defence", "National Security"]
    sub_categories TEXT,        -- JSON array: ["Procurement", "Military Exercise"]
    article_type TEXT,          -- Dominant primary category label

    -- -----------------------------------------------------------------------
    -- Location intelligence (NEW)
    -- -----------------------------------------------------------------------
    countries TEXT,             -- JSON array: ["India", "China"]
    states TEXT,                -- JSON array: ["Ladakh", "Sikkim"]
    regions TEXT,               -- JSON array: ["Northeast India", "Eastern Himalayas"]
    districts TEXT,             -- JSON array: ["Leh", "Kargil"]
    cities TEXT,                -- JSON array: ["Leh"]
    localities TEXT,            -- JSON array: ["Nathu La", "Daulat Beg Oldi"]
    location_type TEXT,         -- "border_area" | "military_installation" | "city" | etc.
    location_confidence REAL,   -- 0.0–1.0

    -- -----------------------------------------------------------------------
    -- Named entities (NEW)
    -- -----------------------------------------------------------------------
    people TEXT,                -- JSON array of names
    organizations TEXT,         -- JSON array of org names
    equipment TEXT,             -- JSON array: ["Rafale", "S-400", "Arjun MBT"]

    -- -----------------------------------------------------------------------
    -- Topics, keywords, tags (NEW)
    -- -----------------------------------------------------------------------
    topics TEXT,                -- JSON array of topic strings
    keywords TEXT,              -- JSON array of extracted keywords
    tags TEXT,                  -- JSON array of domain tags

    -- -----------------------------------------------------------------------
    -- Sentiment / Stance analysis (NEW)
    -- -----------------------------------------------------------------------
    sentiment TEXT,             -- "Positive|Negative|Neutral|Concern|Critical|Escalatory|De-escalatory|Unclear"
    stance TEXT,                -- "Critical|Supportive|Neutral|Alarming|Reassuring|Unclear"
    sentiment_target TEXT,      -- "Government|Organization|Policy|Country|Military|Event|None"

    -- -----------------------------------------------------------------------
    -- AI-GENERATED ANALYTICAL FLAGS
    -- ALL FIELDS BELOW ARE AI-GENERATED ANALYTICAL INDICATORS ONLY.
    -- THEY DO NOT CONSTITUTE OFFICIAL INTELLIGENCE ASSESSMENTS.
    -- -----------------------------------------------------------------------

    -- Threat classification
    threat_level TEXT,          -- "LOW|MODERATE|HIGH|CRITICAL|UNCLEAR"
    threat_score REAL,          -- 0.0–1.0
    threat_reason TEXT,         -- Human-readable reason

    -- Action-oriented flags
    potential_threat TEXT,          -- "YES|NO|UNCLEAR"
    army_monitoring_needed TEXT,    -- "YES|NO|UNCLEAR"
    army_intervention_needed TEXT,  -- "YES|NO|UNCLEAR"

    -- Strategic relevance
    national_security_relevance TEXT,   -- "LOW|MEDIUM|HIGH|UNCLEAR"
    military_relevance TEXT,            -- "LOW|MEDIUM|HIGH|UNCLEAR"
    strategic_importance TEXT,          -- "LOW|MEDIUM|HIGH|UNCLEAR"
    diplomatic_significance TEXT,       -- "LOW|MEDIUM|HIGH|UNCLEAR"
    economic_security_relevance TEXT,   -- "LOW|MEDIUM|HIGH|UNCLEAR"
    border_security_relevance TEXT,     -- "LOW|MEDIUM|HIGH|UNCLEAR"
    escalation_risk TEXT,               -- "LOW|MEDIUM|HIGH|UNCLEAR"

    -- Situational flags
    emerging_situation INTEGER,         -- 0 or 1
    requires_human_review INTEGER,      -- 0 or 1
    requires_continuous_monitoring INTEGER, -- 0 or 1

    -- Confidence
    nlp_confidence REAL,        -- 0.0–1.0 (NLP processing confidence)
    ai_confidence REAL,         -- 0.0–1.0 (Gemini analysis confidence)

    -- Structured events (JSON array)
    events TEXT,                -- JSON: [{event_type, event_date, actors, ...}]

    -- -----------------------------------------------------------------------
    -- Processing status flags (NEW)
    -- -----------------------------------------------------------------------
    nlp_processed INTEGER DEFAULT 0,    -- 1 if NLP stage completed
    ai_processed INTEGER DEFAULT 0      -- 1 if Gemini analysis completed

);
"""


CREATE_PIPELINE_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS pipeline_runs (

    run_id INTEGER PRIMARY KEY AUTOINCREMENT,

    started_at TEXT DEFAULT CURRENT_TIMESTAMP,

    article_count INTEGER,

    categorized_count INTEGER,

    representative_count INTEGER,

    nlp_processed_count INTEGER DEFAULT 0,

    ai_processed_count INTEGER DEFAULT 0,

    status TEXT

);
"""


CREATE_GOLD_LABELS_TABLE = """
CREATE TABLE IF NOT EXISTS gold_labels (

    article_id TEXT PRIMARY KEY,

    gold_category TEXT NOT NULL,

    annotator TEXT,

    notes TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(article_id)
        REFERENCES articles(article_id)

);
"""


# FTS5 virtual table for full-text keyword search
CREATE_FTS_TABLE = """
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts
USING fts5(
    article_id UNINDEXED,
    title,
    ai_summary,
    article_text,
    people,
    organizations,
    countries,
    states,
    cities,
    topics,
    keywords,
    tags
);
"""

# Triggers to keep standalone FTS table in sync
CREATE_FTS_TRIGGER_INSERT = """
CREATE TRIGGER IF NOT EXISTS articles_fts_insert
AFTER INSERT ON articles BEGIN
    INSERT INTO articles_fts(
        article_id, title, ai_summary, article_text,
        people, organizations, countries, states, cities,
        topics, keywords, tags
    )
    VALUES (
        new.article_id, new.title, new.ai_summary, new.article_text,
        new.people, new.organizations, new.countries, new.states, new.cities,
        new.topics, new.keywords, new.tags
    );
END;
"""

CREATE_FTS_TRIGGER_DELETE = """
CREATE TRIGGER IF NOT EXISTS articles_fts_delete
AFTER DELETE ON articles BEGIN
    DELETE FROM articles_fts WHERE article_id = old.article_id;
END;
"""

CREATE_FTS_TRIGGER_UPDATE = """
CREATE TRIGGER IF NOT EXISTS articles_fts_update
AFTER UPDATE ON articles BEGIN
    DELETE FROM articles_fts WHERE article_id = old.article_id;
    INSERT INTO articles_fts(
        article_id, title, ai_summary, article_text,
        people, organizations, countries, states, cities,
        topics, keywords, tags
    )
    VALUES (
        new.article_id, new.title, new.ai_summary, new.article_text,
        new.people, new.organizations, new.countries, new.states, new.cities,
        new.topics, new.keywords, new.tags
    );
END;
"""


# New columns to add to existing databases (migration)
NEW_COLUMNS = [
    ("ai_summary", "TEXT"),
    ("primary_categories", "TEXT"),
    ("sub_categories", "TEXT"),
    ("article_type", "TEXT"),
    ("countries", "TEXT"),
    ("states", "TEXT"),
    ("regions", "TEXT"),
    ("districts", "TEXT"),
    ("cities", "TEXT"),
    ("localities", "TEXT"),
    ("location_type", "TEXT"),
    ("location_confidence", "REAL"),
    ("people", "TEXT"),
    ("organizations", "TEXT"),
    ("equipment", "TEXT"),
    ("topics", "TEXT"),
    ("keywords", "TEXT"),
    ("tags", "TEXT"),
    ("sentiment", "TEXT"),
    ("stance", "TEXT"),
    ("sentiment_target", "TEXT"),
    ("threat_level", "TEXT"),
    ("threat_score", "REAL"),
    ("threat_reason", "TEXT"),
    ("potential_threat", "TEXT"),
    ("army_monitoring_needed", "TEXT"),
    ("army_intervention_needed", "TEXT"),
    ("national_security_relevance", "TEXT"),
    ("military_relevance", "TEXT"),
    ("strategic_importance", "TEXT"),
    ("diplomatic_significance", "TEXT"),
    ("economic_security_relevance", "TEXT"),
    ("border_security_relevance", "TEXT"),
    ("escalation_risk", "TEXT"),
    ("emerging_situation", "INTEGER"),
    ("requires_human_review", "INTEGER"),
    ("requires_continuous_monitoring", "INTEGER"),
    ("nlp_confidence", "REAL"),
    ("ai_confidence", "REAL"),
    ("events", "TEXT"),
    ("nlp_processed", "INTEGER DEFAULT 0"),
    ("ai_processed", "INTEGER DEFAULT 0"),
    ("updated_at", "TEXT"),
]


# ============================================================================
# DATABASE CONNECTION
# ============================================================================

def get_connection() -> sqlite3.Connection:
    """
    Create a SQLite database connection with WAL mode for better
    concurrent read performance.
    """

    DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    connection.row_factory = sqlite3.Row

    # Enable WAL mode for better read concurrency (API + pipeline)
    connection.execute("PRAGMA journal_mode=WAL;")

    # Enable foreign keys
    connection.execute("PRAGMA foreign_keys=ON;")

    return connection


# ============================================================================
# INITIALIZE DATABASE
# ============================================================================

def initialize_database() -> None:
    """
    Create database tables if they don't already exist.
    If the database already exists, migrate by adding new columns.
    """

    logger.info(
        "Initializing database: %s",
        DATABASE_FILE,
    )

    connection = get_connection()

    try:

        cursor = connection.cursor()

        # Create tables if they don't exist
        cursor.execute(CREATE_ARTICLES_TABLE)
        cursor.execute(CREATE_PIPELINE_RUNS_TABLE)
        cursor.execute(CREATE_GOLD_LABELS_TABLE)

        connection.commit()

        # Run migration to add any missing columns
        _migrate_add_columns(connection)

        # Create FTS table if not exists
        _create_fts_table(connection)

        connection.commit()

    finally:

        connection.close()

    logger.info(
        "Database initialized successfully."
    )


def _migrate_add_columns(connection: sqlite3.Connection) -> None:
    """
    Add new intelligence columns to existing articles table.
    SQLite does not support 'ADD COLUMN IF NOT EXISTS' directly,
    so we check existing columns first.
    """

    cursor = connection.cursor()

    # Get existing columns
    cursor.execute("PRAGMA table_info(articles)")
    existing_columns = {row["name"] for row in cursor.fetchall()}

    added = 0

    for col_name, col_type in NEW_COLUMNS:

        # Strip DEFAULT from col_name if present for the existence check
        clean_name = col_name.split()[0]

        if clean_name not in existing_columns:

            try:

                connection.execute(
                    f"ALTER TABLE articles ADD COLUMN {col_name} {col_type}"
                )

                logger.info(
                    "Migration: Added column '%s' (%s)",
                    clean_name,
                    col_type,
                )

                added += 1

            except sqlite3.OperationalError as e:

                logger.warning(
                    "Migration: Could not add column '%s': %s",
                    clean_name,
                    e,
                )

    if added > 0:

        connection.commit()

        logger.info(
            "Migration complete: Added %d new column(s).",
            added,
        )

    else:

        logger.info(
            "Migration: No new columns needed (schema up to date)."
        )

    # Also add new columns to pipeline_runs if needed
    cursor.execute("PRAGMA table_info(pipeline_runs)")
    existing_run_cols = {row["name"] for row in cursor.fetchall()}

    for col_name, col_type in [
        ("nlp_processed_count", "INTEGER DEFAULT 0"),
        ("ai_processed_count", "INTEGER DEFAULT 0"),
    ]:
        clean_name = col_name.split()[0]
        if clean_name not in existing_run_cols:
            try:
                connection.execute(
                    f"ALTER TABLE pipeline_runs ADD COLUMN {col_name} {col_type}"
                )
            except sqlite3.OperationalError:
                pass

    connection.commit()


def _create_fts_table(connection: sqlite3.Connection) -> None:
    """
    Create FTS5 virtual table and triggers for full-text search.
    """

    cursor = connection.cursor()

    # Check if FTS table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='articles_fts'"
    )
    fts_exists = cursor.fetchone() is not None

    if not fts_exists:
        logger.info("Creating FTS5 full-text search table...")
        connection.execute(CREATE_FTS_TABLE)

    # Always ensure FTS triggers are up to date and correct
    connection.execute("DROP TRIGGER IF EXISTS articles_fts_insert;")
    connection.execute("DROP TRIGGER IF EXISTS articles_fts_delete;")
    connection.execute("DROP TRIGGER IF EXISTS articles_fts_update;")
    connection.execute(CREATE_FTS_TRIGGER_INSERT)
    connection.execute(CREATE_FTS_TRIGGER_DELETE)
    connection.execute(CREATE_FTS_TRIGGER_UPDATE)

    if not fts_exists:
        # Populate FTS from existing articles
        connection.execute(
            """
            INSERT INTO articles_fts(
                article_id, title, ai_summary, article_text,
                people, organizations, countries, states, cities,
                topics, keywords, tags
            )
            SELECT
                article_id,
                COALESCE(title, ''),
                COALESCE(ai_summary, summary, ''),
                COALESCE(article_text, ''),
                COALESCE(people, ''),
                COALESCE(organizations, ''),
                COALESCE(countries, ''),
                COALESCE(states, ''),
                COALESCE(cities, ''),
                COALESCE(topics, ''),
                COALESCE(keywords, ''),
                COALESCE(tags, '')
            FROM articles
            """
        )
        connection.commit()
        logger.info("FTS5 table created and populated.")
    else:
        logger.info("FTS5 table verified and triggers updated.")


# ============================================================================
# INSERT / UPDATE ARTICLE
# ============================================================================

def _json_dump(value: Any) -> str | None:
    """Safely serialize a value to JSON string."""
    if value is None:
        return None
    if isinstance(value, str):
        return value  # Already serialized
    return json.dumps(value, ensure_ascii=False)


def upsert_article(
    connection: sqlite3.Connection,
    article: dict[str, Any],
) -> None:
    """
    Insert an article or update it if the article_id already exists.
    Handles both legacy fields and new intelligence fields.
    """

    # Serialize JSON fields
    category_scores = _json_dump(article.get("category_scores", {}))
    primary_categories = _json_dump(article.get("primary_categories"))
    sub_categories = _json_dump(article.get("sub_categories"))
    countries = _json_dump(article.get("countries"))
    states = _json_dump(article.get("states"))
    regions = _json_dump(article.get("regions"))
    districts = _json_dump(article.get("districts"))
    cities = _json_dump(article.get("cities"))
    localities = _json_dump(article.get("localities"))
    people = _json_dump(article.get("people"))
    organizations = _json_dump(article.get("organizations"))
    equipment = _json_dump(article.get("equipment"))
    topics = _json_dump(article.get("topics"))
    keywords = _json_dump(article.get("keywords"))
    tags = _json_dump(article.get("tags"))
    events = _json_dump(article.get("events"))

    connection.execute(
        """
        INSERT INTO articles (
            article_id, title, url, source, source_category_hint,
            published_at, fetched_at, summary, ai_summary,
            article_text, classifier_text, text_length,
            story_cluster_id, is_cluster_representative,
            category, category_confidence, category_scores,
            classifier_model, classifier_device,
            primary_categories, sub_categories, article_type,
            countries, states, regions, districts, cities, localities,
            location_type, location_confidence,
            people, organizations, equipment,
            topics, keywords, tags,
            sentiment, stance, sentiment_target,
            threat_level, threat_score, threat_reason,
            potential_threat, army_monitoring_needed, army_intervention_needed,
            national_security_relevance, military_relevance,
            strategic_importance, diplomatic_significance,
            economic_security_relevance, border_security_relevance,
            escalation_risk, emerging_situation,
            requires_human_review, requires_continuous_monitoring,
            nlp_confidence, ai_confidence, events,
            nlp_processed, ai_processed, updated_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            CURRENT_TIMESTAMP
        )

        ON CONFLICT(article_id)
        DO UPDATE SET

            title = excluded.title,
            url = excluded.url,
            source = excluded.source,
            source_category_hint = excluded.source_category_hint,
            published_at = excluded.published_at,
            fetched_at = excluded.fetched_at,
            summary = excluded.summary,
            ai_summary = COALESCE(excluded.ai_summary, ai_summary),
            article_text = excluded.article_text,
            classifier_text = excluded.classifier_text,
            text_length = excluded.text_length,
            story_cluster_id = excluded.story_cluster_id,
            is_cluster_representative = excluded.is_cluster_representative,
            category = excluded.category,
            category_confidence = excluded.category_confidence,
            category_scores = excluded.category_scores,
            classifier_model = excluded.classifier_model,
            classifier_device = excluded.classifier_device,
            primary_categories = COALESCE(excluded.primary_categories, primary_categories),
            sub_categories = COALESCE(excluded.sub_categories, sub_categories),
            article_type = COALESCE(excluded.article_type, article_type),
            countries = COALESCE(excluded.countries, countries),
            states = COALESCE(excluded.states, states),
            regions = COALESCE(excluded.regions, regions),
            districts = COALESCE(excluded.districts, districts),
            cities = COALESCE(excluded.cities, cities),
            localities = COALESCE(excluded.localities, localities),
            location_type = COALESCE(excluded.location_type, location_type),
            location_confidence = COALESCE(excluded.location_confidence, location_confidence),
            people = COALESCE(excluded.people, people),
            organizations = COALESCE(excluded.organizations, organizations),
            equipment = COALESCE(excluded.equipment, equipment),
            topics = COALESCE(excluded.topics, topics),
            keywords = COALESCE(excluded.keywords, keywords),
            tags = COALESCE(excluded.tags, tags),
            sentiment = COALESCE(excluded.sentiment, sentiment),
            stance = COALESCE(excluded.stance, stance),
            sentiment_target = COALESCE(excluded.sentiment_target, sentiment_target),
            threat_level = COALESCE(excluded.threat_level, threat_level),
            threat_score = COALESCE(excluded.threat_score, threat_score),
            threat_reason = COALESCE(excluded.threat_reason, threat_reason),
            potential_threat = COALESCE(excluded.potential_threat, potential_threat),
            army_monitoring_needed = COALESCE(excluded.army_monitoring_needed, army_monitoring_needed),
            army_intervention_needed = COALESCE(excluded.army_intervention_needed, army_intervention_needed),
            national_security_relevance = COALESCE(excluded.national_security_relevance, national_security_relevance),
            military_relevance = COALESCE(excluded.military_relevance, military_relevance),
            strategic_importance = COALESCE(excluded.strategic_importance, strategic_importance),
            diplomatic_significance = COALESCE(excluded.diplomatic_significance, diplomatic_significance),
            economic_security_relevance = COALESCE(excluded.economic_security_relevance, economic_security_relevance),
            border_security_relevance = COALESCE(excluded.border_security_relevance, border_security_relevance),
            escalation_risk = COALESCE(excluded.escalation_risk, escalation_risk),
            emerging_situation = COALESCE(excluded.emerging_situation, emerging_situation),
            requires_human_review = COALESCE(excluded.requires_human_review, requires_human_review),
            requires_continuous_monitoring = COALESCE(excluded.requires_continuous_monitoring, requires_continuous_monitoring),
            nlp_confidence = COALESCE(excluded.nlp_confidence, nlp_confidence),
            ai_confidence = COALESCE(excluded.ai_confidence, ai_confidence),
            events = COALESCE(excluded.events, events),
            nlp_processed = COALESCE(excluded.nlp_processed, nlp_processed),
            ai_processed = COALESCE(excluded.ai_processed, ai_processed),
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            article.get("article_id"),
            article.get("title", ""),
            article.get("url", ""),
            article.get("source"),
            article.get("source_category_hint"),
            article.get("published_at"),
            article.get("fetched_at"),
            article.get("summary"),
            article.get("ai_summary"),
            article.get("article_text"),
            article.get("classifier_text"),
            article.get("text_length"),
            article.get("story_cluster_id"),
            int(article.get("is_cluster_representative", False)),
            article.get("category"),
            article.get("category_confidence"),
            category_scores,
            article.get("classifier_model"),
            article.get("classifier_device"),
            primary_categories,
            sub_categories,
            article.get("article_type"),
            countries,
            states,
            regions,
            districts,
            cities,
            localities,
            article.get("location_type"),
            article.get("location_confidence"),
            people,
            organizations,
            equipment,
            topics,
            keywords,
            tags,
            article.get("sentiment"),
            article.get("stance"),
            article.get("sentiment_target"),
            article.get("threat_level"),
            article.get("threat_score"),
            article.get("threat_reason"),
            article.get("potential_threat"),
            article.get("army_monitoring_needed"),
            article.get("army_intervention_needed"),
            article.get("national_security_relevance"),
            article.get("military_relevance"),
            article.get("strategic_importance"),
            article.get("diplomatic_significance"),
            article.get("economic_security_relevance"),
            article.get("border_security_relevance"),
            article.get("escalation_risk"),
            int(article.get("emerging_situation", 0) or 0),
            int(article.get("requires_human_review", 0) or 0),
            int(article.get("requires_continuous_monitoring", 0) or 0),
            article.get("nlp_confidence"),
            article.get("ai_confidence"),
            events,
            int(article.get("nlp_processed", 0) or 0),
            int(article.get("ai_processed", 0) or 0),
        ),
    )


# ============================================================================
# STORE ARTICLES
# ============================================================================

def store_articles(
    articles: list[dict[str, Any]],
) -> None:
    """
    Store all categorised articles in the database.
    """

    connection = get_connection()

    try:

        for article in articles:

            article_id = article.get("article_id")

            if not article_id:

                logger.warning(
                    "Skipping article without article_id."
                )

                continue

            upsert_article(
                connection,
                article,
            )

        connection.commit()

    finally:

        connection.close()

    logger.info(
        "Stored %d article(s) in database.",
        len(articles),
    )


# ============================================================================
# INTELLIGENCE-SPECIFIC QUERIES
# ============================================================================

def get_articles_by_threat_level(
    threat_level: str,
    limit: int = 50,
) -> list[dict]:
    """Retrieve articles filtered by threat level."""

    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT * FROM articles
            WHERE threat_level = ?
            ORDER BY published_at DESC
            LIMIT ?
            """,
            (threat_level.upper(), limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    finally:
        connection.close()


def get_monitoring_queue(limit: int = 100) -> list[dict]:
    """
    Articles flagged for army monitoring, sorted by threat level and recency.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT * FROM articles
            WHERE army_monitoring_needed = 'YES'
            ORDER BY
                CASE threat_level
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MODERATE' THEN 3
                    WHEN 'LOW' THEN 4
                    ELSE 5
                END,
                CASE strategic_importance
                    WHEN 'HIGH' THEN 1
                    WHEN 'MEDIUM' THEN 2
                    WHEN 'LOW' THEN 3
                    ELSE 4
                END,
                published_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    finally:
        connection.close()


def get_human_review_queue(limit: int = 100) -> list[dict]:
    """
    Articles requiring human review.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT * FROM articles
            WHERE requires_human_review = 1
            ORDER BY
                CASE threat_level
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MODERATE' THEN 3
                    ELSE 4
                END,
                published_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    finally:
        connection.close()


def get_kpi_counts() -> dict:
    """
    Return KPI counts for the intelligence dashboard.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM articles")
        total = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM articles WHERE threat_level IN ('HIGH', 'CRITICAL')"
        )
        high_threat = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM articles WHERE threat_level = 'CRITICAL'"
        )
        critical = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM articles WHERE army_monitoring_needed = 'YES'"
        )
        monitoring = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM articles WHERE requires_human_review = 1"
        )
        human_review = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM articles WHERE emerging_situation = 1"
        )
        emerging = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM articles WHERE potential_threat = 'YES'"
        )
        potential_threat = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*) FROM articles
            WHERE military_relevance = 'HIGH'
               OR national_security_relevance = 'HIGH'
            """
        )
        high_security = cursor.fetchone()[0]

        # Threat distribution
        cursor.execute(
            """
            SELECT threat_level, COUNT(*) as count
            FROM articles
            WHERE threat_level IS NOT NULL
            GROUP BY threat_level
            """
        )
        threat_distribution = {
            row["threat_level"]: row["count"]
            for row in cursor.fetchall()
        }

        # Category distribution
        cursor.execute(
            """
            SELECT article_type, COUNT(*) as count
            FROM articles
            WHERE article_type IS NOT NULL
            GROUP BY article_type
            ORDER BY count DESC
            LIMIT 10
            """
        )
        category_distribution = {
            row["article_type"]: row["count"]
            for row in cursor.fetchall()
        }

        return {
            "total_articles": total,
            "high_threat_articles": high_threat,
            "critical_articles": critical,
            "monitoring_required": monitoring,
            "human_review_required": human_review,
            "emerging_situations": emerging,
            "potential_threat_articles": potential_threat,
            "high_security_articles": high_security,
            "threat_distribution": threat_distribution,
            "category_distribution": category_distribution,
        }

    finally:
        connection.close()


def get_geographic_activity() -> list[dict]:
    """
    Return geographic activity counts for dashboard.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                cities, states, countries,
                threat_level, army_monitoring_needed,
                article_type
            FROM articles
            WHERE nlp_processed = 1
            """
        )
        return [dict(row) for row in cursor.fetchall()]

    finally:
        connection.close()


def get_unprocessed_articles(
    nlp: bool = False,
    ai: bool = False,
    limit: int = 50,
) -> list[dict]:
    """
    Retrieve articles that haven't been through NLP or AI processing yet.
    Used by the intelligence processing stage.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        if nlp:
            cursor.execute(
                """
                SELECT * FROM articles
                WHERE nlp_processed = 0
                  AND article_text IS NOT NULL
                  AND article_text != ''
                ORDER BY published_at DESC
                LIMIT ?
                """,
                (limit,),
            )

        elif ai:
            cursor.execute(
                """
                SELECT * FROM articles
                WHERE ai_processed = 0
                  AND nlp_processed = 1
                  AND article_text IS NOT NULL
                  AND article_text != ''
                ORDER BY published_at DESC
                LIMIT ?
                """,
                (limit,),
            )

        else:
            cursor.execute(
                """
                SELECT * FROM articles
                ORDER BY published_at DESC
                LIMIT ?
                """,
                (limit,),
            )

        return [dict(row) for row in cursor.fetchall()]

    finally:
        connection.close()


def mark_nlp_processed(
    connection: sqlite3.Connection,
    article_id: str,
) -> None:
    """Mark an article as NLP-processed."""
    connection.execute(
        "UPDATE articles SET nlp_processed = 1, updated_at = CURRENT_TIMESTAMP WHERE article_id = ?",
        (article_id,),
    )


def mark_ai_processed(
    connection: sqlite3.Connection,
    article_id: str,
) -> None:
    """Mark an article as AI (Gemini) processed."""
    connection.execute(
        "UPDATE articles SET ai_processed = 1, updated_at = CURRENT_TIMESTAMP WHERE article_id = ?",
        (article_id,),
    )


# ============================================================================
# RECORD PIPELINE RUN
# ============================================================================

def record_pipeline_run(
    articles: list[dict[str, Any]],
) -> None:
    """
    Record basic information about the pipeline execution.
    """

    article_count = len(articles)

    categorized_count = sum(
        1
        for article in articles
        if article.get("category")
    )

    representative_count = sum(
        1
        for article in articles
        if article.get("is_cluster_representative", False)
    )

    nlp_processed_count = sum(
        1
        for article in articles
        if article.get("nlp_processed")
    )

    ai_processed_count = sum(
        1
        for article in articles
        if article.get("ai_processed")
    )

    connection = get_connection()

    try:

        connection.execute(
            """
            INSERT INTO pipeline_runs (
                article_count,
                categorized_count,
                representative_count,
                nlp_processed_count,
                ai_processed_count,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                article_count,
                categorized_count,
                representative_count,
                nlp_processed_count,
                ai_processed_count,
                "SUCCESS",
            ),
        )

        connection.commit()

    finally:

        connection.close()


# ============================================================================
# LOAD ARTICLES (legacy compatibility)
# ============================================================================

def load_articles(
    input_path: Path = INPUT_FILE,
) -> list[dict[str, Any]]:
    """
    Load categorised articles from JSON.
    """

    if not input_path.exists():

        raise FileNotFoundError(
            f"Input file not found: {input_path}\n"
            "Run zero_shot.py first."
        )

    with input_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    articles = data.get("articles", [])

    if not isinstance(articles, list):

        raise ValueError(
            "Invalid categorized_articles.json format."
        )

    logger.info(
        "Loaded %d categorised article(s)",
        len(articles),
    )

    return articles


# ============================================================================
# DATABASE STATISTICS
# ============================================================================

def print_database_statistics() -> None:
    """
    Print useful database statistics.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()
        kpis = get_kpi_counts()

        logger.info("")
        logger.info(
            "================ INTELLIGENCE DATABASE STATISTICS ================"
        )

        logger.info("Total articles:          %d", kpis["total_articles"])
        logger.info("High-threat articles:    %d", kpis["high_threat_articles"])
        logger.info("Critical articles:       %d", kpis["critical_articles"])
        logger.info("Monitoring required:     %d", kpis["monitoring_required"])
        logger.info("Human review required:   %d", kpis["human_review_required"])
        logger.info("Emerging situations:     %d", kpis["emerging_situations"])
        logger.info("")
        logger.info("Threat distribution:")

        for level, count in kpis["threat_distribution"].items():
            logger.info("  %-12s %d", level, count)

        logger.info("")
        logger.info("Category distribution:")

        for cat, count in kpis["category_distribution"].items():
            logger.info("  %-30s %d", cat, count)

        logger.info(
            "=================================================================="
        )

    finally:

        connection.close()


# ============================================================================
# MAIN
# ============================================================================

def run_storage() -> None:
    """
    Execute the storage stage.
    """

    logger.info("======================================================")
    logger.info("Intelligence Platform — Storage Layer")
    logger.info("======================================================")

    initialize_database()

    articles = load_articles()

    store_articles(articles)

    record_pipeline_run(articles)

    print_database_statistics()

    logger.info("Storage stage completed successfully.")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    run_storage()