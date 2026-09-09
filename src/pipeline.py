"""
AI-Powered Defence & Geopolitical Intelligence Platform
========================================================

Main pipeline orchestrator — 11-stage merged pipeline.

    Stage 0 — D-P2-21 Multi-Source Ingestion (GDELT + WorldBank + SQL + RSS)
        ↓
    Stage 1 — RSS Feed Ingestion (feeds.yaml)
        ↓
    Stage 2 — Article Extraction (full text)
        ↓
    Stage 3 — Text Cleaning
        ↓
    Stage 4 — Semantic Deduplication
        ↓
    Stage 5 — Multi-label Classification (BART)
        ↓
    Stage 6 — NER + Location Extraction (spaCy + geography)
        ↓
    Stage 7 — AI Summarization (Gemini)
        ↓
    Stage 8 — Threat & Strategic Analysis (Gemini)
        ↓
    Stage 9 — Sentiment Analysis (BART)
        ↓
    Stage 10 — Database Storage + Index Update

D-P2-21 Sources (Stage 0):
    GDELT       — Geopolitical events CSV (gdeltproject.org)
    RSSConnector— 6 defence-specific news outlets (JSON/feedparser)
    WorldBank   — Military expenditure data for 10 countries (REST)
    SQL         — Strategic Intelligence Reference DB (local SQLite)

Usage:
    python -m src.pipeline
    python -m src.pipeline --skip-ai     (skip Gemini stages)
    python -m src.pipeline --skip-p2     (skip D-P2-21 multi-source stage)
    python -m src.pipeline --p2-only     (run only P2 ingestion, no NLP)
    python -m src.pipeline --p2-source gdelt  (run only GDELT connector)
    python -m src.pipeline --nlp-only    (only NLP stages)
"""

import argparse
import json
import logging
from pathlib import Path
import time


# ============================================================================
# PIPELINE MODULES
# ============================================================================

from src.ingestion.feed_reader import run_ingestion, run_combined_ingestion
from src.ingestion.article_fetcher import run_article_extraction
from src.processing.cleaner import run_cleaning
from src.processing.deduplicator import run_deduplication

# New NLP modules
from src.nlp.classifier import run_classification
from src.nlp.ner_extractor import run_ner_extraction
from src.nlp.location_extractor import run_location_extraction
from src.nlp.summarizer import run_summarization
from src.nlp.threat_analyzer import run_threat_analysis
from src.nlp.sentiment_analyzer import run_sentiment_analysis

from src.storage.database import (
    run_storage,
    initialize_database,
)

from src.digest.generator import run_digest_generation


# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================================
# PIPELINE STAGE RUNNER
# ============================================================================

def run_stage(
    stage_number: int,
    total_stages: int,
    name: str,
    function,
    articles=None,
):
    """
    Execute one pipeline stage and measure execution time.

    Supports both:
    - Stateless stages: function() → None
    - Article-transforming stages: function(articles) → articles
    """

    logger.info("")
    logger.info("=" * 70)
    logger.info(
        "STAGE %d/%d — %s",
        stage_number,
        total_stages,
        name,
    )
    logger.info("=" * 70)

    start_time = time.perf_counter()

    try:

        if articles is not None:
            result = function(articles)
        else:
            result = function()

    except Exception:

        logger.exception(
            "Stage failed: %s",
            name,
        )
        raise

    elapsed = time.perf_counter() - start_time

    logger.info(
        "✓ Completed '%s' in %.2f seconds.",
        name,
        elapsed,
    )

    return result


# ============================================================================
# NLP ARTICLE PROCESSOR (applies all NLP stages to each article)
# ============================================================================

def run_nlp_pipeline(articles: list[dict]) -> list[dict]:
    """
    Run NER + location extraction on each article.
    These are applied per-article, not batch.
    """

    logger.info("Running NLP intelligence extraction on %d articles...", len(articles))

    for i, article in enumerate(articles):

        # NER
        article = run_ner_extraction(article)

        # Location
        article = run_location_extraction(article)

        # Mark NLP as processed
        article["nlp_processed"] = 1

        if (i + 1) % 20 == 0:
            logger.info("NLP processed: %d/%d", i + 1, len(articles))

    logger.info("NLP extraction complete.")

    return articles


# ============================================================================
# COMPLETE PIPELINE
# ============================================================================

def run_pipeline(
    skip_ai: bool = False,
    nlp_only: bool = False,
    start_stage: int = 1,
    skip_p2: bool = False,
    p2_only: bool = False,
    p2_source: str | None = None,
    sources_config: str | Path | None = None,
) -> None:
    """
    Run the full 11-stage intelligence pipeline.

    Args:
        skip_ai:        Skip Gemini API stages (summarization + threat analysis).
        nlp_only:       Run only stages 1–6 (no Gemini, no sentiment).
        start_stage:    Resume or start pipeline from stage N (1–10).
        skip_p2:        Skip D-P2-21 multi-source Stage 0 (use RSS-only ingestion).
        p2_only:        Run only Stage 0 (P2 ingestion) and exit — no NLP.
        p2_source:      Limit P2 engine to one connector: gdelt/rss/worldbank/sql.
        sources_config: Custom path to sources YAML configuration file.
    """

    pipeline_start = time.perf_counter()

    logger.info("")
    logger.info("#" * 70)
    logger.info("#")
    logger.info("#  AI-POWERED DEFENCE & GEOPOLITICAL INTELLIGENCE PLATFORM")
    logger.info("#  Pipeline Execution %s", f"(Resuming from Stage {start_stage})" if start_stage > 1 else "")
    logger.info("#")
    logger.info("#" * 70)
    logger.info("")

    # Initialize database first
    initialize_database()

    total_stages = 10 if not (skip_ai or nlp_only) else 7
    project_root = Path(__file__).resolve().parent.parent

    # -------------------------------------------------------------------------
    # Stage 0 — D-P2-21 Multi-Source Ingestion (GDELT + WorldBank + SQL + RSS)
    # -------------------------------------------------------------------------

    if start_stage <= 1 and not skip_p2:
        logger.info("")
        logger.info("=" * 70)
        logger.info("STAGE 0 — D-P2-21 MULTI-SOURCE INGESTION (GDELT + WorldBank + SQL + RSS)")
        logger.info("=" * 70)
        import time as _time
        _p2_start = _time.perf_counter()
        try:
            from src.ingestion.feed_reader import run_p2_ingestion
            run_p2_ingestion(source_filter=p2_source, skip_rss=False, config_path=sources_config)
            logger.info("✓ Stage 0 completed in %.2f seconds.", _time.perf_counter() - _p2_start)
        except Exception:
            logger.warning("Stage 0 (P2 ingestion) failed — continuing with RSS-only data.", exc_info=True)

        if p2_only:
            logger.info("#" * 70)
            logger.info("#  P2-ONLY MODE — Pipeline complete after Stage 0.")
            logger.info("#" * 70)
            return

    # -------------------------------------------------------------------------
    # Stages 1 to 4 — Ingestion, Extraction, Cleaning, Deduplication
    # -------------------------------------------------------------------------

    if start_stage <= 1:
        if skip_p2:
            run_stage(1, total_stages, "Feed Ingestion (RSS-only)", run_ingestion)
        else:
            run_stage(1, total_stages, "Feed Ingestion (Combined RSS + P2)",
                      lambda: run_combined_ingestion(skip_p2=True))  # P2 already ran in Stage 0

    if start_stage <= 2:
        run_stage(2, total_stages, "Article Extraction", run_article_extraction)

    if start_stage <= 3:
        run_stage(3, total_stages, "Text Cleaning", run_cleaning)

    if start_stage <= 4:
        run_stage(4, total_stages, "Semantic Deduplication", run_deduplication)

    # -------------------------------------------------------------------------
    # Stage 5 — Multi-label Classification
    # -------------------------------------------------------------------------

    articles = None
    import json

    if start_stage <= 5:
        dedup_file = project_root / "data" / "processed" / "deduplicated_articles.json"

        if not dedup_file.exists():
            logger.error("Deduplicated articles file not found at %s. Aborting.", dedup_file)
            return

        with open(dedup_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        articles = data.get("articles", data) if isinstance(data, dict) else data
        logger.info("Loaded %d articles for classification.", len(articles))

        articles = run_stage(
            5, total_stages,
            "Multi-label Classification",
            run_classification,
            articles,
        )
    else:
        # Resuming from stage >= 6: load previously categorized articles if available
        cat_file = project_root / "data" / "processed" / "categorized_articles.json"
        dedup_file = project_root / "data" / "processed" / "deduplicated_articles.json"

        source_file = cat_file if cat_file.exists() else dedup_file
        if not source_file.exists():
            logger.error("No processed article file found at %s or %s. Aborting.", cat_file, dedup_file)
            return

        with open(source_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        articles = data.get("articles", data) if isinstance(data, dict) else data
        logger.info("Loaded %d articles from %s to resume at Stage %d.", len(articles), source_file.name, start_stage)

    # -------------------------------------------------------------------------
    # Stage 6 — NER + Location Extraction
    # -------------------------------------------------------------------------

    if start_stage <= 6:
        articles = run_stage(
            6, total_stages,
            "NER + Location Intelligence",
            run_nlp_pipeline,
            articles,
        )

    if nlp_only:
        # Save and store, then finish
        _save_and_store(articles, project_root)
        _print_completion(pipeline_start, "NLP-only mode")
        return

    # -------------------------------------------------------------------------
    # Stage 7 — AI Summarization (Gemini)
    # -------------------------------------------------------------------------

    if start_stage <= 7:
        if not skip_ai:
            articles = run_stage(
                7, total_stages,
                "AI Summarization (Gemini)",
                run_summarization,
                articles,
            )
        else:
            logger.info("Skipping AI Summarization (--skip-ai flag).")

    # -------------------------------------------------------------------------
    # Stage 8 — Threat & Strategic Analysis (Gemini)
    # -------------------------------------------------------------------------

    if start_stage <= 8:
        if not skip_ai:
            articles = run_stage(
                8, total_stages,
                "Threat & Strategic Analysis (Gemini) [AI-generated flags only]",
                run_threat_analysis,
                articles,
            )

            # Mark AI as processed
            for article in articles:
                article["ai_processed"] = 1
        else:
            logger.info("Skipping Threat Analysis (--skip-ai flag).")

    # -------------------------------------------------------------------------
    # Stage 9 — Sentiment Analysis
    # -------------------------------------------------------------------------

    if start_stage <= 9:
        articles = run_stage(
            9, total_stages,
            "Sentiment Analysis",
            run_sentiment_analysis,
            articles,
        )

    # -------------------------------------------------------------------------
    # Stage 10 — Database Storage
    # -------------------------------------------------------------------------

    if start_stage <= 10:
        _save_and_store(articles, project_root)

    # -------------------------------------------------------------------------
    # Stage 10b — Digest Generation (legacy)
    # -------------------------------------------------------------------------

    try:
        run_stage(total_stages, total_stages, "Digest Generation", run_digest_generation)
    except Exception:
        logger.warning("Digest generation failed (non-critical). Continuing.")

    _print_completion(pipeline_start)


def _save_and_store(articles: list[dict], project_root: Path) -> None:
    """Save articles to JSON and store in database."""

    import json

    # Save enriched articles to JSON
    output_file = project_root / "data" / "processed" / "categorized_articles.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"articles": articles}, f, ensure_ascii=False, indent=2)

    logger.info("Saved %d enriched articles to %s", len(articles), output_file)

    # Store in database
    from src.storage.database import store_articles, record_pipeline_run
    store_articles(articles)
    record_pipeline_run(articles)


def _print_completion(pipeline_start: float, mode: str = "") -> None:
    """Print pipeline completion summary."""

    total_elapsed = time.perf_counter() - pipeline_start

    logger.info("")
    logger.info("#" * 70)
    logger.info("#  PIPELINE COMPLETED %s", f"({mode})" if mode else "")
    logger.info("#  Total time: %.2f seconds", total_elapsed)
    logger.info("#")
    logger.info("#  Database:  data/database/news_pipeline.db")
    logger.info("#  Articles:  data/processed/categorized_articles.json")
    logger.info("#  API:       http://localhost:8000")
    logger.info("#  Dashboard: http://localhost:5173")
    logger.info("#" * 70)
    logger.info("")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="AI-Powered Defence & Geopolitical Intelligence Platform — Pipeline"
    )

    parser.add_argument(
        "--from-stage",
        "--start-stage",
        type=int,
        default=1,
        dest="start_stage",
        help="Resume or start pipeline from a specific stage (1–10). Example: --from-stage 6",
    )

    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Skip Gemini API stages (summarization + threat analysis)",
    )

    parser.add_argument(
        "--nlp-only",
        action="store_true",
        help="Run only ingestion + NLP stages (no Gemini, no sentiment)",
    )

    parser.add_argument(
        "--skip-p2",
        action="store_true",
        help="Skip D-P2-21 multi-source Stage 0. Use RSS-only ingestion (backward compat).",
    )

    parser.add_argument(
        "--p2-only",
        action="store_true",
        help="Run only the D-P2-21 multi-source ingestion (Stage 0). No NLP processing.",
    )

    parser.add_argument(
        "--p2-source",
        choices=["gdelt", "rss", "worldbank", "sql"],
        default=None,
        dest="p2_source",
        help="Limit P2 Stage 0 to a single connector. Default: all sources.",
    )

    parser.add_argument(
        "--sources-config",
        type=str,
        default=None,
        dest="sources_config",
        help="Path to custom sources YAML configuration file (e.g. config/sources.yaml).",
    )

    args = parser.parse_args()

    run_pipeline(
        skip_ai=args.skip_ai,
        nlp_only=args.nlp_only,
        start_stage=args.start_stage,
        skip_p2=args.skip_p2,
        p2_only=args.p2_only,
        p2_source=args.p2_source,
        sources_config=args.sources_config,
    )